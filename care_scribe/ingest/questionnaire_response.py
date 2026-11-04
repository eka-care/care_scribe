from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse

from care_scribe.ingest.context import Context
from care_scribe.ingest.questions import QUESTIONNAIRE_SLUG


def create(ctx: Context) -> None:
    if not ctx.notes:
        return
    questionnaire = Questionnaire.objects.get(slug=QUESTIONNAIRE_SLUG)
    question_ids = {q["link_id"]: q["id"] for q in questionnaire.questions}
    response = QuestionnaireResponse.objects.create(
        **ctx.scope,
        **ctx.audit,
        questionnaire=questionnaire,
        subject_id=ctx.encounter.external_id,
        responses=[
            {
                "question_id": question_ids[link_id],
                "values": [{"value": v} for v in values],
            }
            for link_id, values in ctx.notes.items()
        ],
    )
    ctx.add_created("questionnaire_response", response)
