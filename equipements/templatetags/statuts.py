from django import template
from django.utils.html import format_html

from equipements.models import Statut

register = template.Library()

CLASSES = {
    Statut.FONCTIONNEL: "at-badge-ok",
    Statut.EN_PANNE: "at-badge-panne",
    Statut.EN_MAINTENANCE: "at-badge-maint",
}


@register.filter
def badge_statut(code):
    """Affiche un statut sous forme de badge coloré : {{ equipement.statut|badge_statut }}"""
    if not code:
        return "—"
    return format_html('<span class="at-badge {}">{}</span>', CLASSES.get(code, ""), Statut(code).label)
