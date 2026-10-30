"""
Module 5 : référentiels (F5.1 à F5.4).

Les quatre référentiels partagent les mêmes vues. Chacun est décrit une fois
dans REFERENTIELS : modèle, formulaire, colonnes et relation qui empêche la
suppression.
"""
from dataclasses import dataclass

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, role_requis

from .forms import CategorieForm, FournisseurForm, TechnicienForm, TypeEquipementForm, TypeInterventionForm
from .models import Categorie, Fournisseur, Technicien, TypeEquipement, TypeIntervention

TOUS_LES_ROLES = (ADMINISTRATEUR, TECHNICIEN)


@dataclass(frozen=True)
class Referentiel:
    titre: str            # « Types d'équipements »
    nature: str           # « le type d'équipement » (pour les messages)
    icone: str
    modele: type
    formulaire: type
    colonnes: tuple       # (libellé, fonction objet -> valeur)
    relation: str         # relation comptée et protégée (equipements / interventions)
    libelle_relation: str


REFERENTIELS = {
    "categories": Referentiel(
        "Catégories", "la catégorie", "layers",
        Categorie, CategorieForm,
        (("Libellé", lambda o: o.libelle), ("Code", lambda o: o.code)),
        "types", "Types",
    ),
    "types-equipement": Referentiel(
        "Types d'équipements", "le type d'équipement", "tags",
        TypeEquipement, TypeEquipementForm,
        (("Libellé", lambda o: o.libelle),
         ("Catégorie", lambda o: o.categorie or "Non classé")),
        "equipements", "Équipements",
    ),
    "types-intervention": Referentiel(
        "Types d'intervention", "le type d'intervention", "list-checks",
        TypeIntervention, TypeInterventionForm,
        (("Libellé", lambda o: o.libelle),
         ("Corrective", lambda o: "Oui" if o.est_corrective else "Non")),
        "interventions", "Interventions",
    ),
    "fournisseurs": Referentiel(
        "Fournisseurs", "le fournisseur", "truck",
        Fournisseur, FournisseurForm,
        (("Nom", lambda o: o.nom), ("Téléphone", lambda o: o.telephone or "—"),
         ("E-mail", lambda o: o.email or "—")),
        "equipements", "Équipements",
    ),
    "techniciens": Referentiel(
        "Techniciens", "le technicien", "hard-hat",
        Technicien, TechnicienForm,
        (("Nom", lambda o: o.nom.upper()), ("Prénom", lambda o: o.prenom), ("Unité", lambda o: o.unite),
         ("Compte", lambda o: o.utilisateur.username if o.utilisateur else "Non relié")),
        "interventions", "Interventions",
    ),
}


def get_referentiel(cle):
    try:
        return REFERENTIELS[cle]
    except KeyError:
        raise Http404 from None


def contexte_commun(cle, ref):
    return {
        "cle": cle,
        "ref": ref,
        "onglets": [(c, r.titre, r.icone) for c, r in REFERENTIELS.items()],
    }


@role_requis(*TOUS_LES_ROLES)
def index(request):
    return redirect("referentiels:liste", cle=next(iter(REFERENTIELS)))


@role_requis(*TOUS_LES_ROLES)
def liste(request, cle):
    ref = get_referentiel(cle)
    # Avec annotate(), Django n'applique pas Meta.ordering : on retrie explicitement.
    objets = ref.modele.objects.annotate(nb_utilisations=Count(ref.relation)).order_by(
        *ref.modele._meta.ordering
    )
    if ref.modele is Technicien:
        objets = objets.select_related("utilisateur")
    elif ref.modele is TypeEquipement:
        objets = objets.select_related("categorie")
    page = Paginator(objets, 30).get_page(request.GET.get("page"))
    # (libellé, valeur) : le libellé sert d'étiquette quand le tableau passe en cartes sur téléphone.
    lignes = [(obj, [(libelle, valeur(obj)) for libelle, valeur in ref.colonnes]) for obj in page]
    return render(request, "referentiels/liste.html", {
        **contexte_commun(cle, ref),
        "page": page,
        "lignes": lignes,
        "entetes": [libelle for libelle, _ in ref.colonnes],
    })


@role_requis(ADMINISTRATEUR)
def ajouter(request, cle):
    ref = get_referentiel(cle)
    form = ref.formulaire(request.POST or None)
    if form.is_valid():
        objet = form.save()
        messages.success(request, f"« {objet} » a été ajouté.")
        return redirect("referentiels:liste", cle=cle)
    return render(request, "referentiels/form.html", {
        **contexte_commun(cle, ref), "form": form, "titre": f"Ajouter : {ref.titre.lower()}",
    })


@role_requis(ADMINISTRATEUR)
def modifier(request, cle, pk):
    ref = get_referentiel(cle)
    objet = get_object_or_404(ref.modele, pk=pk)
    libelle_initial = str(objet)
    form = ref.formulaire(request.POST or None, instance=objet)
    if form.is_valid():
        form.save()
        messages.success(request, f"« {objet} » a été modifié.")
        return redirect("referentiels:liste", cle=cle)
    return render(request, "referentiels/form.html", {
        **contexte_commun(cle, ref), "form": form, "titre": f"Modifier « {libelle_initial} »",
    })


@role_requis(ADMINISTRATEUR)
def supprimer(request, cle, pk):
    ref = get_referentiel(cle)
    objet = get_object_or_404(ref.modele, pk=pk)
    url_liste = reverse("referentiels:liste", args=[cle])
    nb = getattr(objet, ref.relation).count()
    message_blocage = (
        f"Impossible de supprimer « {objet} » : {nb} élément(s) "
        f"({ref.libelle_relation.lower()}) l'utilisent encore."
    ) if nb else ""

    if request.method == "POST":
        try:
            objet.delete()
        except ProtectedError:
            messages.error(request, message_blocage or "Cet élément est encore utilisé.")
        else:
            messages.success(request, f"« {objet} » a été supprimé.")
        return redirect(url_liste)

    return render(request, "confirmer_suppression.html", {
        "objet": objet,
        "nature": ref.nature,
        "message_blocage": message_blocage,
        "url_annuler": url_liste,
    })
