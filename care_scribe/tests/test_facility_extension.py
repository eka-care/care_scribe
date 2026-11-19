from io import StringIO

from care.utils.tests.base import CareAPITestBase
from django.core.management import CommandError, call_command
from django.urls import reverse

from care_scribe.extensions.facility import EXTENSION_NAME, FacilityExtension


class FacilityExtensionTest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser, facility_type=2)
        self.client.force_authenticate(user=self.superuser)

    def retrieve(self):
        url = reverse(
            "facility-detail", kwargs={"external_id": self.facility.external_id}
        )
        return self.client.get(url)

    def set_hfr_id(self, hfr_id, facility_id=None):
        call_command(
            "set_facility_hfr_id",
            str(facility_id or self.facility.external_id),
            hfr_id,
            stdout=StringIO(),
        )

    def test_validate(self):
        cases = [
            ("accepts an IN id", {"hfr_id": "IN2410013685"}, True),
            ("accepts no id", {}, True),
            ("rejects digits without IN", {"hfr_id": "2410013685"}, False),
            ("rejects a lowercase prefix", {"hfr_id": "in2410013685"}, False),
            ("rejects unknown keys", {"hfr_id": "IN1", "other": "x"}, False),
        ]
        for name, data, valid in cases:
            with self.subTest(name):
                if valid:
                    FacilityExtension().validate(data)
                    continue
                with self.assertRaises(ValueError):
                    FacilityExtension().validate(data)

    def test_retrieve_returns_the_hfr_id_once_set(self):
        self.set_hfr_id("IN2410013685")

        resp = self.retrieve()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.data["extensions"][EXTENSION_NAME], {"hfr_id": "IN2410013685"}
        )

    def test_retrieve_returns_an_empty_extension_when_unset(self):
        resp = self.retrieve()

        self.assertEqual(resp.data["extensions"][EXTENSION_NAME], {})

    def test_command_keeps_other_extensions(self):
        self.facility.extensions = {"core": {"alternate_id": "ALT1"}}
        self.facility.save(update_fields=["extensions"])

        self.set_hfr_id("IN2410013685")

        self.facility.refresh_from_db()
        self.assertEqual(self.facility.extensions["core"], {"alternate_id": "ALT1"})

    def test_command_rejects_an_invalid_hfr_id(self):
        with self.assertRaises(CommandError):
            self.set_hfr_id("2410013685")
        self.facility.refresh_from_db()
        self.assertNotIn(EXTENSION_NAME, self.facility.extensions)

    def test_command_rejects_an_unknown_facility(self):
        with self.assertRaises(CommandError):
            self.set_hfr_id(
                "IN2410013685", facility_id="00000000-0000-0000-0000-000000000000"
            )
