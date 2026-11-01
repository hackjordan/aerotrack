"""Tests du module 5 : référentiels (F5.1 à F5.4) et commandes de passage à l'hébergeur."""
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, definir_role, role_de
from emplacements.models import Emplacement
from equipements.models import Equipement, HistoriqueStatut, Statut
from interventions.models import Intervention

from .models import Categorie, Fournisseur, Technicien, TypeEquipement, TypeIntervention
from .views import REFERENTIELS


class ReferentielsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("admin", password="x")
        cls.tech = User.objects.create_user("tech", password="x")
        definir_role(cls.admin, ADMINISTRATEUR)
        definir_role(cls.tech, TECHNICIEN)

        cls.radar = TypeEquipement.objects.create(libelle="Radar")
        cls.corrective = TypeIntervention.objects.create(libelle="Corrective", est_corrective=True)
        cls.thales = Fournisseur.objects.create(nom="Thales", telephone="699000000")
        Equipement.objects.create(
            nom="Radar", numero_serie="R1", marque="Thales", type=cls.radar, fournisseur=cls.thales,
            emplacement=Emplacement.objects.create(batiment="Tour", zone="Vigie"),
        )

    def test_les_quatre_listes_sont_consultables_par_tous(self):
        for user in (self.admin, self.tech):
            self.client.force_login(user)
            for cle in REFERENTIELS:
                with self.subTest(user=user.username, cle=cle):
                    self.assertEqual(self.client.get(reverse("referentiels:liste", args=[cle])).status_code, 200)

    def test_referentiel_inconnu(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/referentiels/inconnu/").status_code, 404)

    def test_seul_l_admin_modifie(self):
        self.client.force_login(self.tech)
        self.assertNotContains(self.client.get(reverse("referentiels:liste", args=["fournisseurs"])), "Ajouter")
        for url in (reverse("referentiels:ajouter", args=["fournisseurs"]),
                    reverse("referentiels:modifier", args=["fournisseurs", self.thales.pk]),
                    reverse("referentiels:supprimer", args=["fournisseurs", self.thales.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_f5_1_type_equipement(self):
        self.client.force_login(self.admin)
        energie = Categorie.objects.get(code="ENR")
        self.client.post(reverse("referentiels:ajouter", args=["types-equipement"]),
                         {"libelle": "Onduleur", "categorie": energie.pk})
        self.assertTrue(TypeEquipement.objects.filter(libelle="Onduleur").exists())
        reponse = self.client.post(reverse("referentiels:ajouter", args=["types-equipement"]),
                                   {"libelle": "RADAR", "categorie": energie.pk})
        self.assertContains(reponse, "existe déjà")

    def test_f5_2_type_intervention_corrective(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("referentiels:ajouter", args=["types-intervention"]),
                         {"libelle": "Dépannage", "est_corrective": "on"})
        self.assertTrue(TypeIntervention.objects.get(libelle="Dépannage").est_corrective)

    def test_f5_3_fournisseur(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("referentiels:modifier", args=["fournisseurs", self.thales.pk]),
                         {"nom": "Thales Air Systems", "telephone": "699000000", "email": "contact@thales.test"})
        self.thales.refresh_from_db()
        self.assertEqual(self.thales.email, "contact@thales.test")

    def test_f5_4_technicien_relie_a_un_compte(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("referentiels:ajouter", args=["techniciens"]),
                         {"nom": "Ngono", "prenom": "Paul", "unite": "IRE", "utilisateur": self.tech.pk})
        self.assertEqual(Technicien.objects.get(nom="Ngono").utilisateur, self.tech)

        # Le compte déjà relié n'est plus proposé pour une autre fiche
        reponse = self.client.get(reverse("referentiels:ajouter", args=["techniciens"]))
        self.assertNotIn(self.tech, reponse.context["form"].fields["utilisateur"].queryset)
        # …mais reste proposé sur sa propre fiche
        fiche = Technicien.objects.get(nom="Ngono")
        reponse = self.client.get(reverse("referentiels:modifier", args=["techniciens", fiche.pk]))
        self.assertIn(self.tech, reponse.context["form"].fields["utilisateur"].queryset)

    def test_suppression_bloquee_si_utilise(self):
        self.client.force_login(self.admin)
        for cle, objet in (("types-equipement", self.radar), ("fournisseurs", self.thales)):
            url = reverse("referentiels:supprimer", args=[cle, objet.pk])
            self.assertContains(self.client.get(url), "Impossible de supprimer")
            self.client.post(url)
            self.assertTrue(type(objet).objects.filter(pk=objet.pk).exists())

    # --- Catégories (RG7) ---

    def test_six_categories_creees_par_la_migration(self):
        self.assertEqual(
            list(Categorie.objects.values_list("code", flat=True)),
            ["COM", "NAV", "SURV", "MET", "RSI", "ENR"],
        )

    def test_type_equipement_exige_une_categorie(self):
        self.client.force_login(self.admin)
        url = reverse("referentiels:ajouter", args=["types-equipement"])
        reponse = self.client.post(url, {"libelle": "Radio HF", "categorie": ""})
        self.assertIn("categorie", reponse.context["form"].errors)
        com = Categorie.objects.get(code="COM")
        self.client.post(url, {"libelle": "Radio HF", "categorie": com.pk})
        self.assertEqual(TypeEquipement.objects.get(libelle="Radio HF").categorie, com)

    def test_categorie_utilisee_ne_peut_pas_etre_supprimee(self):
        surv = Categorie.objects.get(code="SURV")
        self.radar.categorie = surv
        self.radar.save()
        self.client.force_login(self.admin)
        self.client.post(reverse("referentiels:supprimer", args=["categories", surv.pk]))
        self.assertTrue(Categorie.objects.filter(pk=surv.pk).exists())

    def test_suppression_d_un_element_libre(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("referentiels:supprimer", args=["types-intervention", self.corrective.pk]))
        self.assertFalse(TypeIntervention.objects.filter(pk=self.corrective.pk).exists())


class ExportChargementTests(TestCase):
    """Commandes exporter_donnees et charger_donnees."""

    MDP = "mot-de-passe-1"

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.saisie = User.objects.create_user("saisie", password="x")
        cls.compte = User.objects.create_user("aline", password=cls.MDP, first_name="Aline", last_name="Eto")
        definir_role(cls.compte, TECHNICIEN)
        technicien = Technicien.objects.create(nom="Eto", prenom="Aline", unite="RSI", utilisateur=cls.compte)
        cls.equipement = Equipement.objects.create(
            nom="Radar", numero_serie="R1", marque="Thales", statut=Statut.EN_PANNE,
            type=TypeEquipement.objects.create(libelle="Radar"),
            emplacement=Emplacement.objects.create(batiment="Tour", zone="Vigie"),
        )
        Intervention.objects.create(
            date=date(2026, 10, 1), equipement=cls.equipement, technicien=technicien,
            type=TypeIntervention.objects.create(libelle="Corrective", est_corrective=True),
            commentaire="Carte remplacée", panne_resolue=True, cree_par=cls.saisie,
        )

    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.fichier = Path(dossier.name) / "donnees.json"
        call_command("exporter_donnees", fichier=self.fichier, stdout=StringIO())

    def charger(self):
        call_command("charger_donnees", fichier=self.fichier, stdout=StringIO())

    def vider_serveur(self):
        """Serveur où existent les équipements et les types, mais pas encore ces données."""
        Intervention.objects.all().delete()
        Technicien.objects.all().delete()
        self.compte.delete()

    def test_fichier_sans_mot_de_passe_en_clair(self):
        contenu = self.fichier.read_text(encoding="utf-8")
        self.assertNotIn(self.MDP, contenu)
        self.assertIn(self.compte.password, contenu)

    def test_chargement_recree_tout(self):
        self.vider_serveur()
        self.charger()
        technicien = Technicien.objects.get(nom="Eto", prenom="Aline")
        self.assertEqual(technicien.unite, "RSI")
        self.assertEqual(authenticate(username="aline", password=self.MDP), technicien.utilisateur)
        self.assertEqual(role_de(technicien.utilisateur), TECHNICIEN)
        intervention = Intervention.objects.get()
        self.assertEqual(intervention.technicien, technicien)
        self.assertEqual(intervention.date, date(2026, 10, 1))
        self.assertTrue(intervention.panne_resolue)
        self.assertEqual(intervention.cree_par, self.saisie)

    def test_relance_sans_doublon(self):
        self.vider_serveur()
        self.charger()
        self.charger()
        self.assertEqual(Technicien.objects.count(), 1)
        self.assertEqual(Intervention.objects.count(), 1)
        self.assertEqual(get_user_model().objects.filter(username="aline").count(), 1)

    def test_statut_des_equipements_inchange(self):
        historique = HistoriqueStatut.objects.count()
        self.vider_serveur()
        self.charger()
        self.equipement.refresh_from_db()
        self.assertEqual(self.equipement.statut, Statut.EN_PANNE)
        self.assertEqual(HistoriqueStatut.objects.count(), historique)

    def test_equipement_absent_rien_n_est_charge(self):
        self.vider_serveur()
        Equipement.objects.update(numero_serie="AUTRE")
        with self.assertRaisesMessage(CommandError, "init_demo"):
            self.charger()
        self.assertFalse(Technicien.objects.exists())
        self.assertFalse(get_user_model().objects.filter(username="aline").exists())

    def test_compte_existant_garde_son_mot_de_passe(self):
        self.compte.set_password("change-sur-le-serveur")
        self.compte.save()
        self.charger()
        self.assertEqual(authenticate(username="aline", password="change-sur-le-serveur"), self.compte)
        self.assertIsNone(authenticate(username="aline", password=self.MDP))

    def test_auteur_absent_du_serveur(self):
        self.vider_serveur()
        self.saisie.delete()
        self.charger()
        self.assertIsNone(Intervention.objects.get().cree_par)

    def test_fichier_absent(self):
        self.fichier.unlink()
        with self.assertRaisesMessage(CommandError, "Fichier introuvable"):
            self.charger()
