"""Tests du module 6 : tableau de bord (F6.1, F6.2, F6.4)."""
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, definir_role
from equipements.models import Equipement, Statut
from interventions.models import Intervention
from referentiels.models import Technicien, TypeIntervention


class TableauDeBordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("init_demo", stdout=StringIO())  # 12 équipements : 8 OK, 2 en panne, 2 en maintenance
        cls.users = []
        for nom, role in (("admin", ADMINISTRATEUR), ("tech", TECHNICIEN)):
            user = get_user_model().objects.create_user(nom, password="x")
            definir_role(user, role)
            cls.users.append(user)

    def setUp(self):
        self.client.force_login(self.users[1])

    def test_visible_par_les_deux_roles(self):
        for user in self.users:
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(reverse("tableau_bord:accueil")).status_code, 200)

    def test_f6_1_compteurs(self):
        compteurs = self.client.get(reverse("tableau_bord:accueil")).context["compteurs"]
        self.assertEqual(compteurs, {"total": 12, "fonctionnels": 8, "en_panne": 2, "en_maintenance": 2})

    def test_f6_1_compteurs_suivent_les_changements(self):
        Equipement.objects.filter(numero_serie="VHF-0001").update(statut=Statut.EN_PANNE)
        compteurs = self.client.get(reverse("tableau_bord:accueil")).context["compteurs"]
        self.assertEqual((compteurs["fonctionnels"], compteurs["en_panne"]), (7, 3))

    def test_f6_2_repartition_par_categorie(self):
        reponse = self.client.get(reverse("tableau_bord:accueil"))
        repartition = reponse.context["repartition"]
        self.assertEqual([p["libelle"] for p in repartition][:2], ["Communication", "Navigation"])
        self.assertTrue(all(p["nb"] == 2 for p in repartition))
        self.assertEqual(sum(p["nb"] for p in repartition), 12)
        self.assertEqual(reponse.context["graphique"]["valeurs"], [2] * 6)

    def test_f6_2_couleur_fixe_par_categorie(self):
        """La couleur suit la catégorie : retirer une catégorie ne repeint pas les autres."""
        avant = {p["libelle"]: p["couleur"] for p in self.client.get("/").context["repartition"]}
        Equipement.objects.filter(type__categorie__code="NAV").delete()
        apres = {p["libelle"]: p["couleur"] for p in self.client.get("/").context["repartition"]}
        self.assertNotIn("Navigation", apres)
        for libelle, couleur in apres.items():
            self.assertEqual(couleur, avant[libelle])

    def test_f6_4_equipements_en_panne(self):
        en_panne = self.client.get("/").context["en_panne"]
        self.assertEqual(sorted(e.nom for e in en_panne), ["Serveur messagerie", "Transmissomètre RVR piste 12"])

    def test_f6_4_cinq_dernieres_interventions(self):
        technicien = Technicien.objects.create(nom="Ngono", prenom="Paul", unite="IRE")
        preventive = TypeIntervention.objects.get(libelle="Préventive")
        equipement = Equipement.objects.first()
        aujourd_hui = timezone.localdate()
        for jours in range(7):
            Intervention.objects.create(date=aujourd_hui - timedelta(days=jours), equipement=equipement,
                                        technicien=technicien, type=preventive)
        dernieres = list(self.client.get("/").context["dernieres_interventions"])
        self.assertEqual(len(dernieres), 5)
        self.assertEqual(dernieres[0].date, aujourd_hui)

    def test_base_vide(self):
        Intervention.objects.all().delete()
        Equipement.objects.all().delete()
        reponse = self.client.get("/")
        self.assertEqual(reponse.context["compteurs"]["total"], 0)
        self.assertContains(reponse, "Aucun équipement enregistré")
