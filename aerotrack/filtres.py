"""Outils communs aux listes filtrables et triables (équipements, interventions, emplacements)."""


def url_sans(request, *parametres):
    """URL de la page courante sans les paramètres donnés (ni le numéro de page)."""
    query = request.GET.copy()
    for nom in (*parametres, "page"):
        query.pop(nom, None)
    return f"?{query.urlencode()}" if query else request.path


def puce(request, libelle, valeur, *parametres):
    """Étiquette d'un filtre actif, avec le lien qui le retire."""
    return {"libelle": libelle, "valeur": valeur, "url_retrait": url_sans(request, *parametres)}


def trier(request, queryset, colonnes):
    """
    Tri par colonne demandé dans l'URL : ?tri=nom (croissant) ou ?tri=-nom (décroissant).

    « colonnes » associe chaque clé autorisée aux champs du tri. Une clé inconnue est
    ignorée. Renvoie le queryset trié et le tri appliqué ("" si aucun).
    """
    tri = request.GET.get("tri", "")
    champs = colonnes.get(tri.removeprefix("-"))
    if not champs:
        return queryset, ""
    if tri.startswith("-"):
        champs = [f"-{champ}" for champ in champs]
    # « pk » en dernier : ordre stable d'une page à l'autre quand des valeurs sont égales
    return queryset.order_by(*champs, "pk"), tri
