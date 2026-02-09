from rest_framework.routers import DefaultRouter
from .views import SalaryIncrementViewSet, SalaryIncrementHistoryViewSet, HolidayViewSet

router = DefaultRouter()
router.register(r'salary-increments', SalaryIncrementViewSet, basename='salary-increment')
router.register(r'salary-increment-history', SalaryIncrementHistoryViewSet, basename='salary-increment-history')
router.register(r'holidays', HolidayViewSet, basename='holiday')

urlpatterns = router.urls
