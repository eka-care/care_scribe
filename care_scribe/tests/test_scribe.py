import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from care.emr.models import (
    AllergyIntolerance,
    Condition,
    MedicationRequest,
    Observation,
    QuestionnaireResponse,
    ServiceRequest,
)
from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.models.medication_statement import MedicationStatement
from care.security.permissions.encounter import EncounterPermissions
from care.utils.tests.base import CareAPITestBase

from care_scribe.models import ScribeDocument

SCRIBE_NOTE = json.loads(
    (Path(__file__).parent / "fixtures" / "scribe_note.json").read_text()
)


def scribe_note(**changes):
    note = copy.deepcopy(SCRIBE_NOTE)
    note.update(changes)
    return note


@mock.patch("care_scribe.ingest.coding._search", return_value=[])
class ScribeIngestTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        facility = self.create_facility(user=self.user)
        organization = self.create_facility_organization(facility=facility)
        role = self.create_role_with_permissions(
            [EncounterPermissions.can_submit_encounter_questionnaire.name]
        )
        self.attach_role_facility_organization_user(organization, self.user, role)
        self.other_encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=facility,
            organization=organization,
            encounter_class="amb",
        )
        self.encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=facility,
            organization=organization,
            encounter_class="amb",
        )
        self.url = f"/api/care_scribe/encounters/{self.encounter.external_id}/scribe/"
        self.client.force_authenticate(self.user)

    def test_sample_note_creates_one_record_per_item(self, _search):
        resp = self.client.post(self.url, SCRIBE_NOTE, format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        cases = [
            ("symptoms", Condition, {"category": "problem_list_item"}, 1),
            ("diagnoses", Condition, {"category": "encounter_diagnosis"}, 1),
            ("chronic conditions", Condition, {"category": "chronic_condition"}, 2),
            ("allergies", AllergyIntolerance, {}, 1),
            ("current medications", MedicationStatement, {}, 1),
            ("prescriptions", MedicationRequest, {}, 1),
            ("vitals", Observation, {"category__code": "vital-signs"}, 1),
            ("exam findings", Observation, {"category__code": "exam"}, 3),
            ("investigations", ServiceRequest, {}, 2),
            ("notes", QuestionnaireResponse, {}, 1),
        ]
        for name, model, filters, count in cases:
            with self.subTest(name):
                rows = model.objects.filter(encounter=self.encounter, **filters)
                self.assertEqual(rows.count(), count)

    def test_unmatched_text_is_kept_as_a_text_coding(self, _search):
        self.client.post(self.url, SCRIBE_NOTE, format="json")

        diagnosis = Condition.objects.get(category="encounter_diagnosis")
        self.assertEqual(
            diagnosis.code,
            {"code": "Cystitis", "display": "Cystitis"},
        )
        self.assertEqual(diagnosis.verification_status, "provisional")
        self.assertEqual(diagnosis.onset, {"onset_string": "3 days"})

    def test_terminology_match_is_used_as_the_coding(self, _search):
        _search.return_value = [
            SimpleNamespace(
                system="http://snomed.info/sct", code="68566005", display="UTI"
            )
        ]

        self.client.post(self.url, SCRIBE_NOTE, format="json")

        diagnosis = Condition.objects.get(category="encounter_diagnosis")
        self.assertEqual(
            diagnosis.code,
            {"system": "http://snomed.info/sct", "code": "68566005", "display": "UTI"},
        )

    def test_prescription_carries_dosage_text_and_requester(self, _search):
        self.client.post(self.url, SCRIBE_NOTE, format="json")

        request = MedicationRequest.objects.get()
        self.assertEqual(request.medication["display"], "Nitrofurantoin 100 mg")
        self.assertEqual(request.category, "outpatient")
        self.assertEqual(request.requester, self.user)
        self.assertEqual(
            request.dosage_instruction[0]["text"], "1 capsule, twice daily, 5 days"
        )

    def test_prescribed_medicines_are_grouped_into_one_prescription(self, _search):
        cases = [
            ("note with prescribed medicines", SCRIBE_NOTE, 1),
            (
                "note without prescribed medicines",
                scribe_note(
                    document_id="0b6a3c55-7f0e-4c1d-9a2e-3d5f6b7c8d91",
                    sections=[
                        s
                        for s in SCRIBE_NOTE["sections"]
                        if s["key"] != "treatment_plan_meds"
                    ],
                ),
                0,
            ),
        ]
        for name, note, count in cases:
            with self.subTest(name):
                MedicationRequestPrescription.objects.all().delete()
                self.client.post(self.url, note, format="json")

                prescriptions = MedicationRequestPrescription.objects.filter(
                    encounter=self.encounter
                )
                self.assertEqual(prescriptions.count(), count)
                for prescription in prescriptions:
                    self.assertEqual(
                        prescription.alternate_identifier, note["document_id"]
                    )
                    self.assertEqual(prescription.prescribed_by, self.user)
                    self.assertEqual(prescription.status, "active")
                    self.assertEqual(
                        set(
                            MedicationRequest.objects.values_list(
                                "prescription", flat=True
                            )
                        ),
                        {prescription.id},
                    )

    def test_unstructured_sections_become_questionnaire_answers(self, _search):
        self.client.post(self.url, SCRIBE_NOTE, format="json")

        response = QuestionnaireResponse.objects.get()
        link_ids = {q["id"]: q["link_id"] for q in response.questionnaire.questions}
        answers = {
            link_ids[r["question_id"]]: [v["value"] for v in r["values"]]
            for r in response.responses
        }
        self.assertEqual(
            set(answers),
            {
                "history_of_present_illness",
                "medical_history",
                "advices",
                "follow_up_instructions",
            },
        )
        self.assertEqual(
            answers["follow_up_instructions"], ["Follow-up Date: After 1 week"]
        )
        self.assertEqual(len(answers["medical_history"]), 2)

    def test_repeated_document_returns_the_first_result(self, _search):
        first = self.client.post(self.url, SCRIBE_NOTE, format="json")
        second = self.client.post(self.url, SCRIBE_NOTE, format="json")

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data, first.data)
        self.assertEqual(ScribeDocument.objects.count(), 1)
        self.assertEqual(MedicationRequest.objects.count(), 1)

    def test_document_filed_under_another_encounter_is_a_conflict(self, _search):
        self.client.post(self.url, SCRIBE_NOTE, format="json")
        other_url = (
            f"/api/care_scribe/encounters/{self.other_encounter.external_id}/scribe/"
        )

        resp = self.client.post(other_url, SCRIBE_NOTE, format="json")

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["error"]["code"], "document_in_other_encounter")
        self.assertFalse(
            Condition.objects.filter(encounter=self.other_encounter).exists()
        )

    def test_sections_not_ready_are_skipped(self, _search):
        note = scribe_note()
        note["sections"][0]["status"] = {"state": "failed", "error": "timeout"}

        resp = self.client.post(self.url, note, format="json")

        self.assertEqual(resp.data["skipped_sections"], ["chief_complaint"])
        self.assertFalse(
            Condition.objects.filter(category="problem_list_item").exists()
        )

    def test_rejected_requests(self, _search):
        cases = [
            ("missing document id", scribe_note(document_id=None), self.user, 400),
            ("user without encounter access", SCRIBE_NOTE, self.create_user(), 403),
        ]
        for name, body, user, status in cases:
            with self.subTest(name):
                self.client.force_authenticate(user)
                resp = self.client.post(self.url, body, format="json")
                self.assertEqual(resp.status_code, status)
        self.assertFalse(ScribeDocument.objects.exists())
