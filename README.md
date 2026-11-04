# care_scribe

A CARE backend plug that files an AI scribe note against an encounter as CARE clinical records.

## Endpoints

| Endpoint | Body |
|---|---|
| `POST /api/care_scribe/encounters/<encounter_external_id>/scribe/` | The scribe's sectioned note: `sections`, `session_id`, `document_id`, `published_at` |
| `POST /api/care_scribe/encounters/<encounter_external_id>/scribe/fhir/` | `{"bundle": <FHIR Bundle>, "session_id": "..."}`; the note's id is `Bundle.identifier.value`, else `Bundle.id` |

Both are authenticated with the user's CARE token, and the user needs permission to submit questionnaires on the encounter. A note is filed once, all or nothing.

| Status | Meaning |
|---|---|
| 201 | Records created; the body lists their ids per resource |
| 200 | This note was already filed on this encounter; the first result is returned |
| 400 | The body does not match the shape, or a bundle entry is invalid (`invalid_entry`) |
| 403 | No permission to submit questionnaires on the encounter |
| 409 | This note is already filed under another encounter |

## Section mapping

| Section | CARE resource |
|---|---|
| `chief_complaint` (LIST) | Condition, `problem_list_item` |
| DIAGNOSIS | Condition, `encounter_diagnosis` |
| PATIENT_MEDICAL_HISTORY | Condition `chronic_condition`, AllergyIntolerance, the rest as notes |
| MEDICATION_TABLE `current_medications_treatment` | MedicationStatement |
| MEDICATION_TABLE (other) | MedicationRequest |
| VITAL_TABLE, EXAMINATION_FINDINGS | Observation |
| LAB_INVESTIGATIONS | ServiceRequest |
| Anything else | One QuestionnaireResponse on the "Scribe Note" questionnaire |

## FHIR mapping

| Resource | CARE resource |
|---|---|
| Condition `encounter-diagnosis` / `problem-list-item` | Condition `encounter_diagnosis` / `chronic_condition` |
| Observation `symptom` | Condition `problem_list_item` |
| Observation `vital-signs`, `exam`, `laboratory` | Observation |
| AllergyIntolerance, MedicationStatement, MedicationRequest | The same CARE resource |
| ServiceRequest (SNOMED lab, imaging, surgical, counselling, education category) | ServiceRequest |
| Communication, CarePlan, FamilyMemberHistory, Immunization, Procedure, social-history Observations | Answers on the "Scribe Note" questionnaire |
| Patient, Practitioner, Encounter | Ignored; the encounter comes from the URL |

## Coding

A coding the scribe sent is kept. Otherwise each item is coded with the top match from the CARE valueset, and text with no match is stored as a text-only coding.

## Install

Add to `plug_config.py`:

```python
Plug(
    name="care_scribe",
    package_name="git+https://github.com/<org>/care_scribe.git",
    version="@main",
)
```

Then run `python manage.py migrate`.
