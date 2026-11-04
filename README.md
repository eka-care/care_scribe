# care_scribe

A CARE backend plug that files an AI scribe note against an encounter as CARE clinical records.

## Endpoint

`POST /api/care_scribe/encounters/<encounter_external_id>/scribe/`

Authenticated with the user's CARE token. The user needs permission to submit questionnaires on the encounter.

| Status | Meaning |
|---|---|
| 201 | Records created; the body lists their ids per resource |
| 200 | This `document_id` was already filed on this encounter; the first result is returned |
| 400 | The body does not match the scribe note shape |
| 409 | This `document_id` is already filed under another encounter |

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

Each item is coded with the top match from the CARE valueset; text with no match is stored as a text-only coding.

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
