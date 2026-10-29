"""Tests du module 1 : authentification, rôles et gestion des comptes."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .roles import ADMINISTRATEUR, ROLE_CHOICES, TECHNICIEN, definir_role, role_de

User = get_user_model()
MDP = "Tour-Douala-2026"


def creer_utilisateur(username, role=None, **extra):
    user = User.objects.create_user(username, password=MDP, **extra)
    if role:
        definir_role(user, role)
    return user


class ConnexionTests(TestCase):
    def setUp(self):
        self.tech = creer_utilisateur("tech", TECHNICIEN)

    def test_page_protegee_redirige_vers_connexion(self):
        reponse = self.client.get(reverse("tableau_bord:accueil"))
        self.assertRedirects(reponse, f"{reverse('comptes:connexion')}?next=/")

    def test_connexion_reussie(self):  # F1.1
        reponse = self.client.post(reverse("comptes:connexion"), {"username": "tech", "password": MDP})
        self.assertRedirects(reponse, reverse("tableau_bord:accueil"))

    def test_connexion_refusee_mauvais_mot_de_passe(self):
        reponse = self.client.post(reverse("comptes:connexion"), {"username": "tech", "password": "faux"})
        self.assertContains(reponse, "Identifiant ou mot de passe incorrect.")

    def test_compte_desactive_ne_peut_pas_se_connecter(self):
        self.tech.is_active = False
        self.tech.save()
        reponse = self.client.post(reverse("comptes:connexion"), {"username": "tech", "password": MDP})
        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deconnexion(self):  # F1.2
        self.client.force_login(self.tech)
        self.client.post(reverse("comptes:deconnexion"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deconnexion_refuse_get(self):
        self.client.force_login(self.tech)
        self.assertEqual(self.client.get(reverse("comptes:deconnexion")).status_code, 405)

    def test_changement_mot_de_passe(self):  # F1.3
        self.client.force_login(self.tech)
        reponse = self.client.post(reverse("comptes:mot_de_passe"), {
            "old_password": MDP, "new_password1": "Nouveau-Mdp-2026", "new_password2": "Nouveau-Mdp-2026",
        })
        self.assertRedirects(reponse, reverse("tableau_bord:accueil"))
        self.tech.refresh_from_db()
        self.assertTrue(self.tech.check_password("Nouveau-Mdp-2026"))

    def test_menu_affiche_nom_et_role(self):
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("tableau_bord:accueil"))
        self.assertContains(reponse, "Technicien")
        self.assertContains(reponse, "Se déconnecter")


class RolesTests(TestCase):
    def test_superutilisateur_est_administrateur(self):
        admin = User.objects.create_superuser("root", password=MDP)
        self.assertEqual(role_de(admin), ADMINISTRATEUR)

    def test_un_seul_role_a_la_fois(self):
        user = creer_utilisateur("u", TECHNICIEN)
        definir_role(user, ADMINISTRATEUR)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), [ADMINISTRATEUR])

    def test_deux_roles_seulement(self):
        self.assertEqual([valeur for valeur, _ in ROLE_CHOICES], [ADMINISTRATEUR, TECHNICIEN])
        self.assertFalse(Group.objects.filter(name="Consultant").exists())


class GestionComptesTests(TestCase):
    """Critère de recette n° 2 : seuls les administrateurs gèrent les comptes."""

    def setUp(self):
        self.admin = creer_utilisateur("admin", ADMINISTRATEUR)
        self.tech = creer_utilisateur("tech", TECHNICIEN)

    def test_technicien_refuse(self):
        urls = [
            reverse("comptes:utilisateurs"),
            reverse("comptes:ajouter"),
            reverse("comptes:modifier", args=[self.admin.pk]),
            reverse("comptes:reinitialiser", args=[self.admin.pk]),
        ]
        self.client.force_login(self.tech)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        reponse = self.client.post(reverse("comptes:activation", args=[self.admin.pk]))
        self.assertEqual(reponse.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_lien_comptes_visible_uniquement_pour_admin(self):
        lien = reverse("comptes:utilisateurs")
        self.client.force_login(self.tech)
        self.assertNotContains(self.client.get("/"), lien)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get("/"), lien)

    def test_admin_voit_la_liste(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse("comptes:utilisateurs"))
        self.assertContains(reponse, "tech")
        self.assertContains(reponse, "Technicien")

    def test_admin_cree_un_compte_avec_role(self):  # F1.4, F1.5
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("comptes:ajouter"), {
            "username": "nouveau", "last_name": "Mbarga", "first_name": "Alice",
            "email": "", "role": TECHNICIEN, "password1": MDP, "password2": MDP,
        })
        self.assertRedirects(reponse, reverse("comptes:utilisateurs"))
        self.assertEqual(role_de(User.objects.get(username="nouveau")), TECHNICIEN)

    def test_admin_change_le_role(self):  # F1.5
        self.client.force_login(self.admin)
        self.client.post(reverse("comptes:modifier", args=[self.tech.pk]), {
            "last_name": "", "first_name": "", "email": "", "is_active": "on", "role": ADMINISTRATEUR,
        })
        self.assertEqual(role_de(self.tech), ADMINISTRATEUR)

    def test_admin_desactive_puis_reactive(self):  # F1.4
        self.client.force_login(self.admin)
        url = reverse("comptes:activation", args=[self.tech.pk])
        self.client.post(url)
        self.tech.refresh_from_db()
        self.assertFalse(self.tech.is_active)
        self.client.post(url)
        self.tech.refresh_from_db()
        self.assertTrue(self.tech.is_active)

    def test_admin_ne_peut_pas_se_desactiver(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("comptes:activation", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_ne_peut_pas_changer_son_propre_role(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("comptes:modifier", args=[self.admin.pk]), {
            "last_name": "", "first_name": "", "email": "", "role": TECHNICIEN,
        })
        self.admin.refresh_from_db()
        self.assertEqual(role_de(self.admin), ADMINISTRATEUR)
        self.assertTrue(self.admin.is_active)

    def test_admin_reinitialise_un_mot_de_passe(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("comptes:reinitialiser", args=[self.tech.pk]), {
            "new_password1": "Reinit-Mdp-2026", "new_password2": "Reinit-Mdp-2026",
        })
        self.tech.refresh_from_db()
        self.assertTrue(self.tech.check_password("Reinit-Mdp-2026"))
