"""Balises d'interface communes : en-têtes de colonnes triables, surlignage de la recherche."""
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.inclusion_tag("includes/entete_tri.html", takes_context=True)
def entete_tri(context, libelle, cle):
    """
    En-tête de colonne cliquable : un clic trie par cette colonne, le suivant inverse l'ordre.
    Garde la recherche et les filtres de l'URL, et revient à la première page.
    """
    actuel = context.get("tri", "")
    query = context["request"].GET.copy()
    query.pop("page", None)
    query["tri"] = f"-{cle}" if actuel == cle else cle
    if actuel == cle:
        sens = "croissant"
    elif actuel == f"-{cle}":
        sens = "decroissant"
    else:
        sens = ""
    return {"libelle": libelle, "url": f"?{query.urlencode()}", "sens": sens}


@register.filter
def surligner(valeur, texte):
    """Met en valeur les passages qui correspondent à la recherche (sans risque d'injection HTML)."""
    valeur = str(valeur)
    if not texte:
        return valeur
    # Avec un groupe capturant, re.split alterne : texte normal, passage trouvé, texte normal…
    morceaux = re.split(f"({re.escape(texte)})", valeur, flags=re.IGNORECASE)
    return mark_safe("".join(
        f'<mark class="at-surligne">{escape(morceau)}</mark>' if i % 2 else escape(morceau)
        for i, morceau in enumerate(morceaux)
    ))
