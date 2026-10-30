"""Fil d'Ariane de la barre du haut : la rubrique parente de la page affichée."""
from django.urls import reverse

# Rubrique de chaque module : (libellé, page liste)
RUBRIQUES = {
    "equipements": ("Équipements", "equipements:liste"),
    "emplacements": ("Emplacements", "emplacements:liste"),
    "interventions": ("Interventions", "interventions:liste"),
    "referentiels": ("Référentiels", "referentiels:index"),
    "comptes": ("Comptes", "comptes:utilisateurs"),
}
# Pages qui sont elles-mêmes la tête de leur rubrique : pas de fil d'Ariane
PAGES_DE_TETE = {"liste", "index", "utilisateurs", "mot_de_passe", "connexion"}


def fil_ariane(request):
    """« Équipements › VHF Vigie » sur une fiche ou un formulaire ; rien sur les listes."""
    page = getattr(request, "resolver_match", None)
    if page is None or page.url_name in PAGES_DE_TETE or page.app_name not in RUBRIQUES:
        return {}
    libelle, nom_url = RUBRIQUES[page.app_name]
    # Référentiels : retour à l'onglet concerné (catégories, types…)
    if "cle" in page.kwargs:
        url = reverse("referentiels:liste", kwargs={"cle": page.kwargs["cle"]})
    else:
        url = reverse(nom_url)
    return {"fil_ariane": {"libelle": libelle, "url": url}}
