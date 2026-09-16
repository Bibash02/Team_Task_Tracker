from rest_framework.routers import DefaultRouter
from labels.views import LabelViewSet

router = DefaultRouter()
router.register("", LabelViewSet, basename="label")
urlpatterns = router.urls
