from .roles import ADMINISTRATEUR, TECHNICIEN, role_de


def role(request):
    """Rend le rôle de l'utilisateur connecté disponible dans tous les templates."""
    role_actuel = role_de(request.user)
    return {
        "role": role_actuel,
        "est_admin": role_actuel == ADMINISTRATEUR,
        "est_technicien": role_actuel == TECHNICIEN,
    }
