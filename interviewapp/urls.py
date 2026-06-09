from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import InterviewCandidateViewSet, candidate_checkin, dashboard


router = DefaultRouter()
router.register(r"candidates", InterviewCandidateViewSet, basename="interview-candidate")

app_name = "interviewapp"

urlpatterns = [
    path("checkin/", candidate_checkin, name="candidate-checkin"),
    path("dashboard/", dashboard, name="interview-dashboard"),
]

urlpatterns += router.urls
