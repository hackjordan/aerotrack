"""Outils communs aux listes filtrables (équipements, interventions)."""


def url_sans(request, *parametres):
    """URL de la page courante sans les paramètres donnés (ni le numéro de page)."""
    query = request.GET.copy()
    for nom in (*parametres, "page"):
        query.pop(nom, None)
    return f"?{query.urlencode()}" if query else request.path


def puce(request, libelle, valeur, *parametres):
    """Étiquette d'un filtre actif, avec le lien qui le retire."""
    return {"libelle": libelle, "valeur": valeur, "url_retrait": url_sans(request, *parametres)}
