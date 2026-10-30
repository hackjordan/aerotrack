"""Tests du module 6 : tableau de bord (F6.1, F6.2, F6.4) et recherche globale."""
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, definir_role
from emplacements.models import Emplacement
from equipements.models import Equipement, Statut
from interventions.models import Intervention
from referentiels.models import Technicien, TypeEquipement, TypeIntervention

from .templatetags.interface import surligner


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

    def test_message_d_accueil(self):
        # Sans prénom renseigné, l'identifiant est repris avec une majuscule
        self.assertContains(self.client.get("/"), '<span class="at-accueil-nom">Tech</span>')
        for heure, attendu in ((9, "Bonjour"), (18, "Bonsoir")):
            with self.subTest(heure=heure), patch("tableau_bord.views.timezone") as horloge:
                horloge.localtime.return_value = datetime(2026, 10, 30, heure, 0)
                self.assertEqual(self.client.get("/").context["salutation"], attendu)


class RechercheGlobaleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.tech = User.objects.create_user("tech", password="x")
        definir_role(cls.tech, TECHNICIEN)
        cls.sans_role = User.objects.create_user("sansrole", password="x")

        type_radar = TypeEquipement.objects.create(libelle="Radar")
        vigie = Emplacement.objects.create(zone="Vigie", batiment="Tour de contrôle")
        cls.radar = Equipement.objects.create(
            nom="Radar primaire", numero_serie="RAD-001", marque="Thales", type=type_radar, emplacement=vigie,
        )
        Intervention.objects.create(
            equipement=cls.radar, technicien=Technicien.objects.create(nom="Ngono", prenom="Paul", unite="IRE"),
            type=TypeIntervention.objects.create(libelle="Préventive"), commentaire="Contrôle de la vigie",
        )

    def setUp(self):
        self.client.force_login(self.tech)

    def rechercher(self, texte):
        return self.client.get(reverse("tableau_bord:recherche"), {"q": texte})

    def test_cherche_dans_les_trois_rubriques(self):
        contexte = self.rechercher("vigie").context  # zone de l'emplacement, commentaire de l'intervention
        self.assertEqual((contexte["nb_equipements"], contexte["nb_emplacements"], contexte["nb_interventions"]), (0, 1, 1))
        contexte = self.rechercher("rad-001").context  # n° de série, sans tenir compte des majuscules
        self.assertEqual(list(contexte["equipements"]), [self.radar])
        self.assertEqual(contexte["nb_total"], 2)  # l'équipement et son intervention

    def test_mot_trouve_surligne(self):
        self.assertContains(self.rechercher("radar"), '<mark class="at-surligne">Radar</mark> primaire')

    def test_surlignage_sans_injection_html(self):
        self.assertEqual(surligner("<i>Radar</i>", "radar"), '&lt;i&gt;<mark class="at-surligne">Radar</mark>&lt;/i&gt;')

    def test_recherche_vide_ou_sans_resultat(self):
        self.assertContains(self.rechercher("  "), "Que cherchez-vous")
        self.assertContains(self.rechercher("introuvable"), "Aucun résultat")

    def test_champ_dans_la_barre_du_haut(self):
        self.assertContains(self.client.get("/"), 'id="at-recherche-globale"')

    def test_utilisateur_sans_role_refuse(self):
        self.client.force_login(self.sans_role)
        self.assertEqual(self.rechercher("radar").status_code, 403)
