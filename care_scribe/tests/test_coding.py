from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from care_scribe.ingest import coding

UTI = SimpleNamespace(system="http://snomed.info/sct", code="68566005", display="UTI")


@mock.patch("care_scribe.ingest.coding._search", return_value=[UTI])
@mock.patch("care_scribe.ingest.coding._valueset", return_value=None)
class CodeFromTextTests(SimpleTestCase):
    def test_prefetched_text_skips_the_terminology_server(self, _valueset, search):
        with coding.prefetched_codes({("vs", "uti"), ("vs", "fever")}):
            search.reset_mock()
            code = coding.code_from_text("vs", "uti")

        self.assertEqual(
            code, {"system": UTI.system, "code": UTI.code, "display": "UTI"}
        )
        search.assert_not_called()

    def test_text_not_prefetched_is_looked_up(self, _valueset, search):
        with coding.prefetched_codes({("vs", "uti")}):
            search.reset_mock()
            coding.code_from_text("vs", "cough")

        search.assert_called_once_with(None, "vs", "cough")

    def test_prefetch_ends_with_the_block(self, _valueset, search):
        with coding.prefetched_codes({("vs", "uti")}):
            pass
        search.reset_mock()

        coding.code_from_text("vs", "uti")

        search.assert_called_once_with(None, "vs", "uti")
