from django.db.models import Count
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .filters import InterviewCandidateFilter
from .models import CandidateStatusLog, InterviewCandidate
from .serializers import (
    CandidateCheckInSerializer,
    CandidateStatusLogSerializer,
    ConvertCandidateSerializer,
    FinalStatusUpdateSerializer,
    InterviewCandidateSerializer,
    RemarksUpdateSerializer,
    RoundStatusUpdateSerializer,
    normalize_phone,
)


class IsInterviewAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(user, "role", None) in ["admin", "manager", "hr"])
        )


class IsInterviewAdminNoHRDelete(IsInterviewAdmin):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method == "DELETE" and getattr(request.user, "role", None) == "hr":
            return False
        return True


@api_view(["POST"])
@permission_classes([AllowAny])
def candidate_checkin(request):
    serializer = CandidateCheckInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = normalize_phone(serializer.validated_data["phone"])
    interview_date = serializer.validated_data.get("interview_date") or timezone.localdate()
    existing = InterviewCandidate.objects.filter(
        phone=phone,
        interview_date=interview_date,
    ).first()

    if existing:
        return Response(
            {
                "success": True,
                "duplicate": True,
                "message": "Candidate is already checked in for this date.",
                "token_number": existing.token_number,
                "candidate_id": existing.id,
                "status": existing.status,
                "interview_date": existing.interview_date,
                "checkin_time": existing.checkin_time,
            },
            status=status.HTTP_200_OK,
        )

    candidate = serializer.save()
    return Response(
        {
            "success": True,
            "duplicate": False,
            "message": "Candidate checked in successfully.",
            "token_number": candidate.token_number,
            "candidate_id": candidate.id,
            "status": candidate.status,
            "interview_date": candidate.interview_date,
            "checkin_time": candidate.checkin_time,
        },
        status=status.HTTP_201_CREATED,
    )


class InterviewCandidateViewSet(viewsets.ModelViewSet):
    queryset = InterviewCandidate.objects.select_related(
        "hr_round_by",
        "manager_round_by",
        "converted_employee",
        "converted_by",
        "created_by",
        "updated_by",
    ).prefetch_related("status_logs")
    serializer_class = InterviewCandidateSerializer
    permission_classes = [IsAuthenticated, IsInterviewAdminNoHRDelete]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InterviewCandidateFilter
    search_fields = [
        "full_name",
        "phone",
        "token_number",
        "aadhaar_number",
        "pan_number",
        "email",
    ]
    ordering_fields = ["checkin_time", "interview_date", "created_at", "full_name"]

    def perform_create(self, serializer):
        interview_date = serializer.validated_data.get("interview_date") or timezone.localdate()
        old_status = ""
        candidate = serializer.save(
            token_number=InterviewCandidate.generate_token_number(interview_date),
            checkin_time=timezone.now(),
            interview_date=interview_date,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        CandidateStatusLog.objects.create(
            candidate=candidate,
            action_type=CandidateStatusLog.ACTION_UPDATE,
            old_status=old_status,
            new_status=candidate.status,
            changed_by=self.request.user,
            remarks="Candidate created by HR/admin.",
        )

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        candidate = serializer.save(updated_by=self.request.user)
        if old_status != candidate.status:
            CandidateStatusLog.objects.create(
                candidate=candidate,
                action_type=CandidateStatusLog.ACTION_FINAL_STATUS,
                old_status=old_status,
                new_status=candidate.status,
                changed_by=self.request.user,
                remarks="Candidate status updated.",
            )

    @action(detail=True, methods=["get"], url_path="logs")
    def logs(self, request, pk=None):
        candidate = self.get_object()
        serializer = CandidateStatusLogSerializer(candidate.status_logs.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="hr-round")
    def update_hr_round(self, request, pk=None):
        candidate = self.get_object()
        serializer = RoundStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        round_status = serializer.validated_data["status"]
        remarks = serializer.validated_data.get("remarks", "")
        old_status = candidate.status

        candidate.hr_round_status = round_status
        candidate.hr_round_by = request.user
        candidate.hr_round_at = timezone.now()
        candidate.hr_round_remarks = remarks
        if round_status == InterviewCandidate.ROUND_PASSED:
            candidate.status = InterviewCandidate.STATUS_HR_ROUND_DONE
        elif round_status == InterviewCandidate.ROUND_FAILED:
            candidate.status = InterviewCandidate.STATUS_REJECTED
        elif round_status == InterviewCandidate.ROUND_ON_HOLD:
            candidate.status = InterviewCandidate.STATUS_ON_HOLD
        candidate.updated_by = request.user
        candidate.save()

        CandidateStatusLog.objects.create(
            candidate=candidate,
            action_type=CandidateStatusLog.ACTION_HR_ROUND,
            old_status=old_status,
            new_status=candidate.status,
            changed_by=request.user,
            remarks=remarks,
        )
        return Response(InterviewCandidateSerializer(candidate, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="manager-round")
    def update_manager_round(self, request, pk=None):
        candidate = self.get_object()
        serializer = RoundStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        round_status = serializer.validated_data["status"]
        remarks = serializer.validated_data.get("remarks", "")
        old_status = candidate.status

        candidate.manager_round_status = round_status
        candidate.manager_round_by = request.user
        candidate.manager_round_at = timezone.now()
        candidate.manager_round_remarks = remarks
        if round_status == InterviewCandidate.ROUND_PASSED:
            candidate.status = InterviewCandidate.STATUS_MANAGER_ROUND_DONE
        elif round_status == InterviewCandidate.ROUND_FAILED:
            candidate.status = InterviewCandidate.STATUS_REJECTED
        elif round_status == InterviewCandidate.ROUND_ON_HOLD:
            candidate.status = InterviewCandidate.STATUS_ON_HOLD
        candidate.updated_by = request.user
        candidate.save()

        CandidateStatusLog.objects.create(
            candidate=candidate,
            action_type=CandidateStatusLog.ACTION_MANAGER_ROUND,
            old_status=old_status,
            new_status=candidate.status,
            changed_by=request.user,
            remarks=remarks,
        )
        return Response(InterviewCandidateSerializer(candidate, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="final-status")
    def update_final_status(self, request, pk=None):
        candidate = self.get_object()
        serializer = FinalStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = candidate.status
        candidate.status = serializer.validated_data["status"]
        candidate.remarks = serializer.validated_data.get("remarks", candidate.remarks)
        candidate.updated_by = request.user
        candidate.save(update_fields=["status", "remarks", "updated_by", "updated_at"])

        CandidateStatusLog.objects.create(
            candidate=candidate,
            action_type=CandidateStatusLog.ACTION_FINAL_STATUS,
            old_status=old_status,
            new_status=candidate.status,
            changed_by=request.user,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(InterviewCandidateSerializer(candidate, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="remarks")
    def add_remarks(self, request, pk=None):
        candidate = self.get_object()
        serializer = RemarksUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate.remarks = serializer.validated_data["remarks"]
        candidate.updated_by = request.user
        candidate.save(update_fields=["remarks", "updated_by", "updated_at"])
        CandidateStatusLog.objects.create(
            candidate=candidate,
            action_type=CandidateStatusLog.ACTION_REMARKS,
            old_status=candidate.status,
            new_status=candidate.status,
            changed_by=request.user,
            remarks=candidate.remarks,
        )
        return Response(InterviewCandidateSerializer(candidate, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="convert-to-employee")
    def convert_to_employee(self, request, pk=None):
        candidate = self.get_object()
        serializer = ConvertCandidateSerializer(
            data=request.data,
            context={"candidate": candidate, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        candidate.refresh_from_db()
        return Response(
            {
                "success": True,
                "message": "Candidate converted to employee successfully.",
                "employee_id": employee.id,
                "employee_username": employee.username,
                "candidate": InterviewCandidateSerializer(candidate, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInterviewAdmin])
def dashboard(request):
    today = timezone.localdate()
    candidates = InterviewCandidate.objects.all()
    today_candidates = candidates.filter(interview_date=today)

    def status_count(value):
        return today_candidates.filter(status=value).count()

    source_counts = list(
        candidates.values("source")
        .annotate(count=Count("id"))
        .order_by("-count", "source")
    )
    position_counts = list(
        candidates.values("position_applied")
        .annotate(count=Count("id"))
        .order_by("-count", "position_applied")
    )
    date_counts = [
        {"date": row["interview_date"], "count": row["count"]}
        for row in candidates.values("interview_date")
        .annotate(count=Count("id"))
        .order_by("interview_date")
    ]

    return Response(
        {
            "today_total_candidates": today_candidates.count(),
            "waiting_candidates": status_count(InterviewCandidate.STATUS_WAITING),
            "hr_round_done": status_count(InterviewCandidate.STATUS_HR_ROUND_DONE),
            "manager_round_done": status_count(InterviewCandidate.STATUS_MANAGER_ROUND_DONE),
            "selected": status_count(InterviewCandidate.STATUS_SELECTED),
            "rejected": status_count(InterviewCandidate.STATUS_REJECTED),
            "on_hold": status_count(InterviewCandidate.STATUS_ON_HOLD),
            "no_show": status_count(InterviewCandidate.STATUS_NO_SHOW),
            "converted": status_count(InterviewCandidate.STATUS_CONVERTED),
            "source_wise_count": source_counts,
            "position_wise_count": position_counts,
            "date_wise_count": date_counts,
        }
    )
