"""
F4.5 : mise à jour automatique du statut de l'équipement après une intervention corrective.

Règle :
  - intervention corrective, panne résolue      → l'équipement passe « Fonctionnel » ;
  - intervention corrective, panne non résolue  → l'équipement passe « En maintenance ».
Les interventions préventives et les installations ne changent pas le statut.
"""
from django.db.models import Q

from equipements.models import Statut
from equipements.services import changer_statut


def statut_attendu(intervention):
    """Statut que doit prendre l'équipement après cette intervention, ou None."""
    if not intervention.type.est_corrective:
        return None
    return Statut.FONCTIONNEL if intervention.panne_resolue else Statut.EN_MAINTENANCE


def est_la_plus_recente(intervention):
    """Vrai si aucune intervention plus récente n'existe pour le même équipement."""
    autres = intervention.equipement.interventions.exclude(pk=intervention.pk)
    return not autres.filter(
        Q(date__gt=intervention.date) | Q(date=intervention.date, cree_le__gt=intervention.cree_le)
    ).exists()


def appliquer_statut(intervention, auteur):
    """
    Met à jour le statut de l'équipement selon l'intervention.

    Seule l'intervention la plus récente de l'équipement peut changer son statut :
    corriger une ancienne intervention ne doit pas écraser l'état actuel.
    Renvoie la ligne d'historique créée, ou None si rien n'a changé.
    """
    nouveau = statut_attendu(intervention)
    if nouveau is None or not est_la_plus_recente(intervention):
        return None
    equipement = intervention.equipement
    if equipement.statut == nouveau:
        return None
    commentaire = f"Intervention corrective du {intervention.date:%d/%m/%Y}"
    return changer_statut(equipement, nouveau, auteur, commentaire)
