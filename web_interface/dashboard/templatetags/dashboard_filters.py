"""
Custom template filters for dashboard.
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key."""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def json_dumps(value):
    """Convert value to JSON string."""
    import json
    return json.dumps(value)


