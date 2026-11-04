import copy
import json
from pathlib import Path
from unittest import mock

from care.emr.models import (
    AllergyIntolerance,
    Condition,
    MedicationRequest,
    Observation,
    QuestionnaireResponse,
    ServiceRequest,
)
from care.emr.models.medication_statement import MedicationStatement
from care.security.permissions.encounter import EncounterPermissions
from care.utils.tests.base import CareAPITestBase

from care_scribe.fhir import request as fhir
from care_scribe.fhir.lookups import bundle_lookups
from care_scribe.models import ScribeDocument

BUNDLE = json.loads(
    (Path(__file__).parent / "fixtures" / "fhir_bundle.json").read_text()
)


def fhir_note(bundle=None, session_id="sc-test-session"):
    return {"bundle": copy.deepcopy(bundle or BUNDLE), "session_id": session_id}


def resources(note, resource_type, code_text):
    return [
        e["resource"]
        for e in note["bundle"]["entry"]
        if e["resource"]["resourceType"] == resource_type
        and e["resource"].get("code", {}).get("text") == code_text
    ]


@mock.patch("care_scribe.ingest.coding._search", return_value=[])
class ScribeFhirIngestTests(CareAPITestBase):
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
        self.url = self.fhir_url(self.encounter)
        self.client.force_authenticate(self.user)

    def fhir_url(self, encounter):
        return f"/api/care_scribe/encounters/{encounter.external_id}/scribe/fhir/"

    def test_sample_bundle_creates_one_record_per_resource(self, _search):
        resp = self.client.post(self.url, fhir_note(), format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        cases = [
            ("symptoms", Condition, {"category": "problem_list_item"}, 2),
            ("diagnoses", Condition, {"category": "encounter_diagnosis"}, 6),
            ("medical history", Condition, {"category": "chronic_condition"}, 9),
            ("allergies", AllergyIntolerance, {}, 1),
            ("current medications", MedicationStatement, {}, 5),
            ("prescriptions", MedicationRequest, {}, 7),
            ("vitals", Observation, {"category__code": "vital-signs"}, 9),
            ("exam findings", Observation, {"category__code": "exam"}, 14),
            ("lab results", Observation, {"category__code": "laboratory"}, 13),
            ("lab orders", ServiceRequest, {"category": "laboratory"}, 7),
            (
                "procedures advised",
                ServiceRequest,
                {"category": "surgical_procedure"},
                1,
            ),
            ("notes", QuestionnaireResponse, {}, 1),
        ]
        for name, model, filters, count in cases:
            with self.subTest(name):
                rows = model.objects.filter(encounter=self.encounter, **filters)
                self.assertEqual(rows.count(), count)
        self.assertEqual(resp.data["skipped_resources"], [])

    def test_every_terminology_search_is_prefetched_once(self, _search):
        note = fhir_note()
        expected = bundle_lookups(fhir.Request.model_validate(note).bundle)

        self.client.post(self.url, note, format="json")

        searched = [
            (slug, text) for _, slug, text in (c.args for c in _search.call_args_list)
        ]
        self.assertEqual(set(searched), expected)
        self.assertEqual(len(searched), len(expected))

    def test_scribe_codes_are_kept_and_text_is_the_fallback(self, _search):
        self.client.post(self.url, fhir_note(), format="json")

        request = MedicationRequest.objects.get(medication__display="Tab. Ecosprin 75")
        self.assertEqual(
            request.medication,
            {"code": "Tab. Ecosprin 75", "display": "Tab. Ecosprin 75"},
        )
        self.assertEqual(
            request.dosage_instruction[0]["route"],
            {"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral"},
        )
        self.assertEqual(
            request.dosage_instruction[0]["text"],
            "1 tablet, once daily at night, lifelong",
        )

    def test_vitals_keep_numbers_units_and_blood_pressure_text(self, _search):
        self.client.post(self.url, fhir_note(), format="json")

        cases = [
            (
                "Temperature",
                "decimal",
                {"value": "98.4", "unit": {"code": "°F", "display": "°F"}},
            ),
            ("Blood pressure", "string", {"value": "150/94 mmHg"}),
        ]
        for code_text, value_type, value in cases:
            with self.subTest(code_text):
                observation = Observation.objects.get(main_code__display=code_text)
                self.assertEqual(observation.value_type, value_type)
                self.assertEqual(observation.value, value)

    def test_partial_lab_date_goes_into_the_note(self, _search):
        self.client.post(self.url, fhir_note(), format="json")

        observation = Observation.objects.get(main_code__display="Fasting blood sugar")
        self.assertIn("Date: 2026-07", observation.note)
        self.assertIn("High", observation.note)
        self.assertEqual(
            observation.effective_datetime.isoformat(),
            "2026-11-04T15:19:50.750967+00:00",
        )

    def test_statuses_follow_the_scribe(self, _search):
        self.client.post(self.url, fhir_note(), format="json")

        refuted = Condition.objects.filter(verification_status="refuted")
        self.assertEqual(
            set(refuted.values_list("code__display", flat=True)),
            {"Thyroid disorder", "Asthma", "Tuberculosis"},
        )
        self.assertEqual(AllergyIntolerance.objects.get().clinical_status, "inactive")

    def test_narrative_becomes_scribe_note_answers(self, _search):
        self.client.post(self.url, fhir_note(), format="json")

        response = QuestionnaireResponse.objects.get()
        link_ids = {q["id"]: q["link_id"] for q in response.questionnaire.questions}
        counts = {
            link_ids[r["question_id"]]: len(r["values"]) for r in response.responses
        }
        self.assertEqual(
            counts,
            {
                "history_of_present_illness": 1,
                "medical_history": 11,
                "advices": 7,
                "follow_up_instructions": 3,
                "other": 17,
            },
        )

    def test_repeated_bundle_returns_the_first_result(self, _search):
        first = self.client.post(self.url, fhir_note(), format="json")
        second = self.client.post(self.url, fhir_note(), format="json")
        elsewhere = self.client.post(
            self.fhir_url(self.other_encounter), fhir_note(), format="json"
        )

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data, first.data)
        self.assertEqual(elsewhere.status_code, 409)
        self.assertEqual(MedicationRequest.objects.count(), 7)

    def test_bundle_id_is_the_key_without_an_identifier(self, _search):
        note = fhir_note()
        del note["bundle"]["identifier"]
        note["bundle"]["id"] = "7d1f2c3e-0000-4000-8000-00000000abcd"

        resp = self.client.post(self.url, note, format="json")

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            resp.data["document_id"], "7d1f2c3e-0000-4000-8000-00000000abcd"
        )

    def test_unknown_resources_are_listed_as_skipped(self, _search):
        note = fhir_note()
        note["bundle"]["entry"].append({"resource": {"resourceType": "Goal"}})

        resp = self.client.post(self.url, note, format="json")

        self.assertEqual(resp.data["skipped_resources"], ["Goal"])

    def test_invalid_entry_files_nothing(self, _search):
        note = fhir_note()
        del resources(note, "Observation", "Blood pressure")[0]["code"]

        resp = self.client.post(self.url, note, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["error"]["code"], "invalid_entry")
        self.assertFalse(Condition.objects.exists())
        self.assertFalse(ScribeDocument.objects.exists())

    def test_rejected_requests(self, _search):
        no_key = fhir_note()
        del no_key["bundle"]["identifier"]
        del no_key["bundle"]["id"]
        cases = [
            ("missing bundle", {"session_id": "sc-x"}, self.user, 400),
            ("not a bundle", fhir_note({"resourceType": "Patient"}), self.user, 400),
            ("bundle without a document key", no_key, self.user, 400),
            ("user without encounter access", fhir_note(), self.create_user(), 403),
        ]
        for name, body, user, status in cases:
            with self.subTest(name):
                self.client.force_authenticate(user)
                resp = self.client.post(self.url, body, format="json")
                self.assertEqual(resp.status_code, status)
        self.assertFalse(ScribeDocument.objects.exists())
