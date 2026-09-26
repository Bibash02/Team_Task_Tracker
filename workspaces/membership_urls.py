from rest_framework.routers import DefaultRouter

from workspaces.views import MembershipViewSet

router = DefaultRouter()
router.register("", MembershipViewSet, basename="membership")

urlpatterns = router.urls