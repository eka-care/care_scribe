import uuid

from django.db import migrations

SLUG = "scribe-note"
NAMESPACE = uuid.UUID("5b0d1c7e-2f41-4f6a-9a51-6a3a0c3f0e11")

QUESTIONS = [
    ("history_of_present_illness", "History of Present Illness"),
    ("medical_history", "Medical History Notes"),
    ("advices", "Advices"),
    ("follow_up_instructions", "Follow-up Instructions"),
    ("other", "Other Notes"),
]


def create_questionnaire(apps, schema_editor):
    Questionnaire = apps.get_model("emr", "Questionnaire")
    if Questionnaire.objects.filter(slug=SLUG).exists():
        return
    Questionnaire.objects.create(
        slug=SLUG,
        version="1.0",
        title="Scribe Note",
        description="Scribe note sections that have no structured CARE resource",
        subject_type="encounter",
        status="active",
        questions=[
            {
                "id": str(uuid.uuid5(NAMESPACE, link_id)),
                "link_id": link_id,
                "text": text,
                "type": "text",
                "repeats": True,
            }
            for link_id, text in QUESTIONS
        ],
    )


def delete_questionnaire(apps, schema_editor):
    apps.get_model("emr", "Questionnaire").objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("care_scribe", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_questionnaire, delete_questionnaire),
    ]
