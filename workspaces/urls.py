from rest_framework.routers import DefaultRouter

from workspaces.views import WorkspaceViewSet

router = DefaultRouter()
router.register("", WorkspaceViewSet, basename="workspace")

urlpatterns = router.urls