"""
Les deux rôles d'AéroTrack : Administrateur et Technicien.

Chaque rôle est un groupe Django. Un utilisateur appartient à un seul de ces
groupes. Un superutilisateur est toujours considéré comme Administrateur.
"""
from functools import wraps

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

ADMINISTRATEUR = "Administrateur"
TECHNICIEN = "Technicien"

ROLES = [ADMINISTRATEUR, TECHNICIEN]
ROLE_CHOICES = [(role, role) for role in ROLES]


def role_de(user):
    """Renvoie le rôle de l'utilisateur, ou None s'il n'en a pas."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ADMINISTRATEUR
    # .all() profite d'un éventuel prefetch_related("groups")
    noms = {groupe.name for groupe in user.groups.all()}
    for role in ROLES:
        if role in noms:
            return role
    return None


def definir_role(user, role):
    """Remplace le rôle de l'utilisateur par celui donné."""
    user.groups.remove(*Group.objects.filter(name__in=ROLES))
    user.groups.add(Group.objects.get(name=role))


def a_un_role(user, *roles):
    return role_de(user) in roles


def role_requis(*roles):
    """
    Décorateur de vue : refuse l'accès (erreur 403) aux utilisateurs
    qui n'ont pas l'un des rôles indiqués.

    La connexion est déjà exigée partout par LoginRequiredMiddleware.
    """

    def decorateur(vue):
        @wraps(vue)
        def vue_protegee(request, *args, **kwargs):
            if not a_un_role(request.user, *roles):
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return vue_protegee

    return decorateur
