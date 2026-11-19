from care.facility.models import Facility
from django.core.management.base import BaseCommand, CommandError

from care_scribe.extensions.facility import EXTENSION_NAME, FacilityExtension


class Command(BaseCommand):
    help = "Set the HFR ID the scribe handoff sends for a facility"

    def add_arguments(self, parser):
        parser.add_argument("facility_id", help="the facility's external id")
        parser.add_argument("hfr_id", help="e.g. IN2410013685")

    def handle(self, *args, facility_id, hfr_id, **options):
        facility = Facility.objects.filter(external_id=facility_id).first()
        if facility is None:
            raise CommandError(f"no facility {facility_id}")
        data = {**facility.extensions.get(EXTENSION_NAME, {}), "hfr_id": hfr_id}
        try:
            FacilityExtension().validate(data)
        except ValueError as e:
            raise CommandError(str(e)) from e
        facility.extensions = {**facility.extensions, EXTENSION_NAME: data}
        facility.save(update_fields=["extensions"])
        self.stdout.write(f"set hfr_id on {facility.name}")
