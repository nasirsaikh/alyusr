from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if not mapping:
        return ""
    try:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
        return mapping.get(f"field__{key}", "")
    except AttributeError:
        return ""
