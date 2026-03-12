from django import template

register = template.Library()


@register.filter(name="in_list")
def in_list(value, csv_string):
    """
    Usage: {{ donation.status|in_list:"available,expired" }}
    Returns True if value is in the comma-separated string.
    """
    values = [v.strip() for v in csv_string.split(",")]
    return value in values


@register.filter(name="status_badge")
def status_badge(status):
    """Return CSS class string for a given status."""
    return f"badge-{status}"
