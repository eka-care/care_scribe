from rest_framework.routers import SimpleRouter

from care_scribe.api.scribe import ScribeViewSet

router = SimpleRouter()
router.register(
    r"encounters/(?P<encounter_external_id>[^/.]+)/scribe",
    ScribeViewSet,
    basename="care_scribe_scribe",
)

urlpatterns = router.urls
