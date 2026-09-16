from rest_framework.routers import DefaultRouter
from tasks.views import AssignmentRuleViewSet

router = DefaultRouter()
router.register("", AssignmentRuleViewSet, basename="assignment-rule")
urlpatterns = router.urls
