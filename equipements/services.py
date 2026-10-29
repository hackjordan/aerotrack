"""
Règles métier sur les équipements, partagées entre les modules.

Tout changement de statut doit passer par ce module pour être enregistré
dans l'historique (utilisé par F4.4 et F6.3).
"""
from .models import HistoriqueStatut


def enregistrer_changement_statut(equipement, ancien_statut, auteur, commentaire=""):
    """
    Ajoute une ligne à l'historique si le statut de l'équipement a changé.

    `ancien_statut` vaut "" pour un équipement qui vient d'être créé.
    """
    if equipement.statut == ancien_statut:
        return None
    return HistoriqueStatut.objects.create(
        equipement=equipement,
        ancien_statut=ancien_statut,
        nouveau_statut=equipement.statut,
        auteur=auteur if auteur and auteur.is_authenticated else None,
        commentaire=commentaire,
    )


def changer_statut(equipement, nouveau_statut, auteur, commentaire=""):
    """Change le statut d'un équipement et l'inscrit dans l'historique."""
    ancien = equipement.statut
    equipement.statut = nouveau_statut
    equipement.save(update_fields=["statut", "modifie_le"])
    return enregistrer_changement_statut(equipement, ancien, auteur, commentaire)
