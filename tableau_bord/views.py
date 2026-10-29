"""Module 6 : tableau de bord (F6.1, F6.2, F6.4)."""
from django.db.models import Count, F, Max, Q
from django.shortcuts import render

from equipements.models import Equipement, Statut
from interventions.models import Intervention
from referentiels.models import Categorie

# Palette catégorielle validée (ordre fixe : la couleur suit la catégorie, jamais son rang).
COULEURS_CATEGORIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
COULEUR_NON_CLASSE = "#9aa5b1"


def accueil(request):
    # F6.1 : compteurs, en une seule requête
    compteurs = Equipement.objects.aggregate(
        total=Count("pk"),
        fonctionnels=Count("pk", filter=Q(statut=Statut.FONCTIONNEL)),
        en_panne=Count("pk", filter=Q(statut=Statut.EN_PANNE)),
        en_maintenance=Count("pk", filter=Q(statut=Statut.EN_MAINTENANCE)),
    )

    # F6.2 : répartition par catégorie. La couleur dépend de la position de la
    # catégorie dans la liste complète, pas du nombre d'équipements.
    repartition = []
    categories = Categorie.objects.annotate(nb=Count("types__equipements")).order_by("ordre", "libelle")
    for index, categorie in enumerate(categories):
        if categorie.nb:
            repartition.append({
                "libelle": categorie.libelle,
                "nb": categorie.nb,
                "couleur": COULEURS_CATEGORIES[index % len(COULEURS_CATEGORIES)],
                "pk": categorie.pk,
            })
    non_classes = Equipement.objects.filter(type__categorie__isnull=True).count()
    if non_classes:
        repartition.append({"libelle": "Non classé", "nb": non_classes, "couleur": COULEUR_NON_CLASSE, "pk": None})
    for part in repartition:
        part["pourcentage"] = round(100 * part["nb"] / compteurs["total"])

    # F6.4 : 5 dernières interventions et équipements en panne
    dernieres_interventions = Intervention.objects.select_related("equipement", "type", "technicien")[:5]
    # « depuis » = date du dernier passage en panne, lue dans l'historique des statuts
    en_panne = (
        Equipement.objects.filter(statut=Statut.EN_PANNE)
        .select_related("type", "emplacement")
        .annotate(depuis=Max(
            "historique_statuts__date",
            filter=Q(historique_statuts__nouveau_statut=Statut.EN_PANNE),
        ))
        .order_by(F("depuis").desc(nulls_last=True))[:6]
    )

    return render(request, "tableau_bord/accueil.html", {
        "compteurs": compteurs,
        "repartition": repartition,
        "graphique": {
            "libelles": [p["libelle"] for p in repartition],
            "valeurs": [p["nb"] for p in repartition],
            "couleurs": [p["couleur"] for p in repartition],
        },
        "dernieres_interventions": dernieres_interventions,
        "en_panne": en_panne,
    })
