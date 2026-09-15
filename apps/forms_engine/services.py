from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from jsonschema import Draft202012Validator
from .models import DataSource

ALLOWED_FIELD_TYPES = {"text", "textarea", "email", "tel", "number", "date", "datetime", "select", "multiselect", "checkbox", "radio", "file"}
ALLOWED_CONDITION_OPERATORS = {"eq", "neq", "in", "not_in", "truthy", "falsy", "contains"}


def validate_schema_definition(module, schema):
    if not isinstance(schema, dict):
        raise ValidationError("Schema must be a JSON object.")
    steps = schema.get("steps", [])
    if module == "ticket" and len(steps) != 4:
        raise ValidationError("Ticket form schemas must contain exactly four configurable steps.")
    keys = set()
    conditional_refs = []
    for step in steps:
        if not isinstance(step, dict) or not step.get("title"):
            raise ValidationError("Every step needs a title.")
        for field in step.get("fields", []):
            key = field.get("key")
            if not key or key in keys:
                raise ValidationError(f"Duplicate/missing field key: {key!r}")
            keys.add(key)
            if field.get("type", "text") not in ALLOWED_FIELD_TYPES:
                raise ValidationError(f"Unsupported field type: {field.get('type')}")
            if field.get("datasource") and not DataSource.objects.filter(code=field["datasource"], is_active=True).exists():
                raise ValidationError(f"Unknown datasource: {field['datasource']}")
            for condition_name in ("visible_when", "required_when"):
                condition = field.get(condition_name)
                if condition:
                    if not isinstance(condition, dict) or not condition.get("field"):
                        raise ValidationError(f"{condition_name} for {key!r} must be an object containing field/operator/value.")
                    if condition.get("operator", "eq") not in ALLOWED_CONDITION_OPERATORS:
                        raise ValidationError(f"Unsupported condition operator on {key!r}: {condition.get('operator')}")
                    conditional_refs.append((key, condition_name, condition["field"]))
    for key, condition_name, referenced_key in conditional_refs:
        if referenced_key not in keys:
            raise ValidationError(f"{condition_name} for {key!r} references unknown field {referenced_key!r}.")
    return True


def resolve_datasource(code):
    source = DataSource.objects.get(code=code, is_active=True)
    config = source.config or {}
    if source.kind == DataSource.Kind.STATIC:
        return config.get("values", [])
    label = config.get("model", "")
    if label not in settings.ALYUSR_ALLOWED_DATASOURCE_MODELS:
        raise ValidationError("Datasource model is not allowlisted.")
    model = apps.get_model(label)
    value_field = config.get("value_field", "pk")
    label_field = config.get("label_field", "name")
    filters = config.get("filters", {})
    if not isinstance(filters, dict):
        raise ValidationError("Datasource filters must be a JSON object.")
    queryset = model.objects.filter(**filters)
    return [{"value": str(getattr(o, value_field)), "label": str(getattr(o, label_field))} for o in queryset[:500]]


def user_roles(user, organization=None):
    roles = {"super_admin"} if user.is_superuser else set()
    if user.is_authenticated:
        memberships = user.organization_memberships.filter(is_active=True)
        if organization:
            memberships = memberships.filter(organization=organization)
        roles.update(memberships.values_list("role", flat=True))
    return roles


def visible_schema_for_user(form_version, user, organization=None):
    roles = user_roles(user, organization)
    schema = {**(form_version.schema or {})}
    out = []
    for step in schema.get("steps", []):
        fields = []
        for field in step.get("fields", []):
            visible = set(field.get("visible_roles") or [])
            if visible and not roles & visible:
                continue
            copied = dict(field)
            editable = set(copied.get("editable_roles") or [])
            copied["readonly"] = bool(editable and not roles & editable)
            if copied.get("datasource"):
                copied["options"] = resolve_datasource(copied["datasource"])
            fields.append(copied)
        out.append({**step, "fields": fields})
    schema["steps"] = out
    return schema


def condition_matches(condition, data):
    if not condition:
        return True
    actual = data.get(condition.get("field"))
    expected = condition.get("value")
    operator = condition.get("operator", "eq")
    if operator == "eq":
        return actual == expected or str(actual) == str(expected)
    if operator == "neq":
        return not (actual == expected or str(actual) == str(expected))
    if operator == "in":
        values = expected if isinstance(expected, (list, tuple, set)) else [expected]
        return actual in values or str(actual) in {str(v) for v in values}
    if operator == "not_in":
        values = expected if isinstance(expected, (list, tuple, set)) else [expected]
        return actual not in values and str(actual) not in {str(v) for v in values}
    if operator == "truthy":
        return bool(actual)
    if operator == "falsy":
        return not bool(actual)
    if operator == "contains":
        try:
            return expected in actual
        except TypeError:
            return False
    return False


def active_fields(schema, data):
    for step in schema.get("steps", []):
        for field in step.get("fields", []):
            if condition_matches(field.get("visible_when"), data):
                yield field


def validate_submission(schema, data):
    properties = {}
    required = []
    for field in active_fields(schema, data):
        key = field["key"]
        typ = field.get("type", "text")
        properties[key] = {"type": "number" if typ == "number" else "boolean" if typ == "checkbox" else "array" if typ == "multiselect" else "string"}
        required_now = bool(field.get("required"))
        if field.get("required_when"):
            required_now = condition_matches(field["required_when"], data)
        if required_now:
            required.append(key)
    validator = Draft202012Validator({"type": "object", "properties": properties, "required": required, "additionalProperties": True})
    errors = {".".join(map(str, e.path)) or "__all__": e.message for e in validator.iter_errors(data)}
    for key in required:
        if data.get(key) in ("", None, [], False):
            errors.setdefault(key, "This field is required.")
    return not errors, errors
