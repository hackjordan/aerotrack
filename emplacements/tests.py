"""Tests du module 3 : emplacements (F3.1 à F3.3)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, definir_role
from equipements.models import Equipement, Statut
from referentiels.models import TypeEquipement

from .models import Emplacement


class EmplacementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("admin", password="x")
        cls.tech = User.objects.create_user("tech", password="x")
        definir_role(cls.admin, ADMINISTRATEUR)
        definir_role(cls.tech, TECHNICIEN)

        cls.vigie = Emplacement.objects.create(batiment="Tour de contrôle", zone="Vigie")
        cls.vide = Emplacement.objects.create(batiment="Bloc technique", zone="Magasin")
        radio = TypeEquipement.objects.create(libelle="VHF")
        Equipement.objects.create(nom="VHF 1", numero_serie="V1", marque="X", type=radio, emplacement=cls.vigie)
        Equipement.objects.create(nom="VHF 2", numero_serie="V2", marque="X", type=radio, emplacement=cls.vigie,
                                  statut=Statut.EN_PANNE)

    def test_liste_avec_compteurs(self):  # F3.2
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("emplacements:liste"))
        vigie = next(e for e in reponse.context["page"] if e.pk == self.vigie.pk)
        self.assertEqual((vigie.nb_equipements, vigie.nb_pannes), (2, 1))

    def test_detail_affiche_les_equipements(self):  # F3.3
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("emplacements:detail", args=[self.vigie.pk]))
        self.assertContains(reponse, "VHF 1")
        self.assertContains(reponse, "VHF 2")
        self.assertIn(("EN_PANNE", "En panne", 1), reponse.context["compteurs"])

    def test_seul_l_admin_gere_les_emplacements(self):  # F3.1
        self.client.force_login(self.tech)
        for url in (reverse("emplacements:ajouter"), reverse("emplacements:modifier", args=[self.vide.pk]),
                    reverse("emplacements:supprimer", args=[self.vide.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_ajoute_modifie_supprime(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("emplacements:ajouter"), {"batiment": "Site radar", "zone": "Abri"})
        nouveau = Emplacement.objects.get(batiment="Site radar")
        self.client.post(reverse("emplacements:modifier", args=[nouveau.pk]), {"batiment": "Site radar", "zone": "Abri principal"})
        nouveau.refresh_from_db()
        self.assertEqual(nouveau.zone, "Abri principal")
        self.client.post(reverse("emplacements:supprimer", args=[nouveau.pk]))
        self.assertFalse(Emplacement.objects.filter(pk=nouveau.pk).exists())

    def test_doublon_refuse(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("emplacements:ajouter"), {"batiment": "tour de contrôle", "zone": "VIGIE"})
        self.assertContains(reponse, "existe déjà")
        self.assertEqual(Emplacement.objects.count(), 2)

    def test_suppression_bloquee_si_equipements(self):
        self.client.force_login(self.admin)
        url = reverse("emplacements:supprimer", args=[self.vigie.pk])
        self.assertContains(self.client.get(url), "contient 2 équipement(s)")
        self.client.post(url)
        self.assertTrue(Emplacement.objects.filter(pk=self.vigie.pk).exists())
