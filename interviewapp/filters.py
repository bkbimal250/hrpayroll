import django_filters

from .models import InterviewCandidate


class InterviewCandidateFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(field_name="interview_date", lookup_expr="gte")
    to_date = django_filters.DateFilter(field_name="interview_date", lookup_expr="lte")

    class Meta:
        model = InterviewCandidate
        fields = [
            "status",
            "hr_round_status",
            "manager_round_status",
            "position_applied",
            "source",
            "interview_date",
            "from_date",
            "to_date",
        ]
