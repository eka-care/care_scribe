from care.emr.models.encounter import Encounter
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from pydantic import ValidationError
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from care_scribe.ingest import request as scribe
from care_scribe.ingest.filing import DocumentInOtherEncounterError
from care_scribe.ingest.service import ingest_scribe_document


class ScribeViewSet(viewsets.ViewSet):
    def get_authenticate_header(self, request):
        return "Bearer"

    def create(self, request, encounter_external_id=None):
        encounter = get_object_or_404(Encounter, external_id=encounter_external_id)
        if not AuthorizationController.call(
            "can_submit_encounter_questionnaire_obj", request.user, encounter
        ):
            raise PermissionDenied
        try:
            req = scribe.Request.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"errors": e.errors(include_url=False, include_input=False)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result, created = ingest_scribe_document(encounter, request.user, req)
        except DocumentInOtherEncounterError:
            return Response(
                {
                    "error": {
                        "code": "document_in_other_encounter",
                        "message": "This document is already filed under another encounter",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            result, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
