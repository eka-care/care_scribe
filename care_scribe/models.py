from django.conf import settings
from django.db import models


class ScribeDocument(models.Model):
    document_id = models.UUIDField(unique=True)
    session_id = models.CharField(max_length=255)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, related_name="+"
    )
    published_at = models.DateTimeField()
    payload = models.JSONField()
    result = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.document_id)
