"""Module 6 : tableau de bord (F6.1, F6.2, F6.4), et recherche globale de la barre du haut."""
from django.db.models import Count, F, Max, Q
from django.shortcuts import render
from django.utils import timezone

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, role_requis
from emplacements.models import Emplacement
from equipements.models import Equipement, Statut
from interventions.models import Intervention
from referentiels.models import Categorie

# Palette catégorielle validée (ordre fixe : la couleur suit la catégorie, jamais son rang).
COULEURS_CATEGORIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
COULEUR_NON_CLASSE = "#9aa5b1"

# Recherche globale : résultats affichés par rubrique (« Voir tout » ouvre la liste filtrée)
RESULTATS_PAR_RUBRIQUE = 5


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
        # Message d'accueil : « Bonsoir » à partir de 18 h (heure de Douala)
        "salutation": "Bonsoir" if timezone.localtime().hour >= 18 else "Bonjour",
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


@role_requis(ADMINISTRATEUR, TECHNICIEN)
def recherche(request):
    """Recherche globale (barre du haut) : équipements, emplacements et interventions."""
    texte = request.GET.get("q", "").strip()
    if not texte:
        return render(request, "tableau_bord/recherche.html", {"texte": ""})

    equipements = Equipement.objects.recherche(texte).select_related("type", "emplacement")
    emplacements = (
        Emplacement.objects.recherche(texte)
        .annotate(nb_equipements=Count("equipements"))
        .order_by("batiment", "zone")  # annotate() ignore Meta.ordering
    )
    interventions = Intervention.objects.recherche(texte).select_related("equipement", "type")
    nombres = {
        "nb_equipements": equipements.count(),
        "nb_emplacements": emplacements.count(),
        "nb_interventions": interventions.count(),
    }
    return render(request, "tableau_bord/recherche.html", {
        "texte": texte,
        "equipements": equipements[:RESULTATS_PAR_RUBRIQUE],
        "emplacements": emplacements[:RESULTATS_PAR_RUBRIQUE],
        "interventions": interventions[:RESULTATS_PAR_RUBRIQUE],
        "nb_total": sum(nombres.values()),
        **nombres,
    })
