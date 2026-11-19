from care.emr.extensions.base import ExtensionResource, PlugExtension
from care.emr.registries.extensions.registry import ExtensionRegistry
from jsonschema import ValidationError, validate

EXTENSION_NAME = "care_scribe__facility"

HFR_ID_PROPERTY = {
    "type": "string",
    "title": "HFR ID",
    "description": "The facility's ABDM Health Facility Registry ID, e.g. IN2410013685.",
    "pattern": "^IN[0-9]+$",
}

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Scribe facility details",
    "type": "object",
    "properties": {"hfr_id": HFR_ID_PROPERTY},
    "additionalProperties": False,
}


class FacilityExtension(PlugExtension):
    extension_name = EXTENSION_NAME
    extension_version = "1.0.0"
    resource_type = ExtensionResource.facility
    write_schema = SCHEMA
    retrieve_schema = SCHEMA

    def validate(self, data, resource=None):
        try:
            validate(data, self.write_schema)
        except ValidationError as e:
            raise ValueError(f"invalid {EXTENSION_NAME}: {e.message}") from e
        return data


ExtensionRegistry.register(FacilityExtension())
