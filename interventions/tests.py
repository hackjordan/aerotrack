"""Tests du module 4 : interventions (F4.1 à F4.5)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, definir_role
from emplacements.models import Emplacement
from equipements.models import Equipement, HistoriqueStatut, Statut
from referentiels.models import Technicien, TypeEquipement, TypeIntervention

from .models import Intervention

AUJOURDHUI = timezone.localdate()


class InterventionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("admin", password="x")
        cls.tech_a = User.objects.create_user("tech_a", password="x")
        cls.tech_b = User.objects.create_user("tech_b", password="x")
        cls.tech_sans_fiche = User.objects.create_user("tech_c", password="x")
        definir_role(cls.admin, ADMINISTRATEUR)
        for u in (cls.tech_a, cls.tech_b, cls.tech_sans_fiche):
            definir_role(u, TECHNICIEN)

        cls.fiche_a = Technicien.objects.create(nom="Ngono", prenom="Paul", unite="IRE", utilisateur=cls.tech_a)
        cls.fiche_b = Technicien.objects.create(nom="Eto", prenom="Marie", unite="RSI", utilisateur=cls.tech_b)

        cls.preventive = TypeIntervention.objects.create(libelle="Préventive")
        cls.corrective = TypeIntervention.objects.create(libelle="Corrective", est_corrective=True)

        type_vhf = TypeEquipement.objects.create(libelle="VHF")
        vigie = Emplacement.objects.create(zone="Vigie", batiment="Tour de contrôle")
        cls.vhf = Equipement.objects.create(
            nom="Émetteur VHF", numero_serie="VHF-1", marque="Park Air",
            type=type_vhf, emplacement=vigie, statut=Statut.EN_PANNE,
        )
        cls.radar = Equipement.objects.create(
            nom="Radar", numero_serie="RAD-1", marque="Thales", type=type_vhf, emplacement=vigie,
        )

    def saisir(self, **modifs):
        donnees = {
            "date": AUJOURDHUI.isoformat(), "equipement": self.vhf.pk, "type": self.corrective.pk,
            "commentaire": "Remplacement du module ampli", "panne_resolue": "",
        }
        donnees.update(modifs)
        return self.client.post(reverse("interventions:ajouter"), donnees)

    # --- F4.1 : saisie ---

    def test_technicien_saisit_en_son_nom(self):
        self.client.force_login(self.tech_a)
        reponse = self.saisir(technicien=self.fiche_b.pk)  # tentative d'usurpation ignorée
        intervention = Intervention.objects.get()
        self.assertRedirects(reponse, reverse("interventions:detail", args=[intervention.pk]))
        self.assertEqual(intervention.technicien, self.fiche_a)
        self.assertEqual(intervention.cree_par, self.tech_a)

    def test_technicien_sans_fiche_ne_peut_pas_saisir(self):
        self.client.force_login(self.tech_sans_fiche)
        reponse = self.client.get(reverse("interventions:ajouter"), follow=True)
        self.assertContains(reponse, "relié à aucune fiche technicien")
        self.assertFalse(Intervention.objects.exists())

    def test_admin_choisit_le_technicien(self):
        self.client.force_login(self.admin)
        self.saisir(technicien=self.fiche_b.pk)
        self.assertEqual(Intervention.objects.get().technicien, self.fiche_b)

    def test_date_future_refusee(self):
        self.client.force_login(self.tech_a)
        reponse = self.saisir(date=(AUJOURDHUI + timedelta(days=1)).isoformat())
        self.assertContains(reponse, "ne peut pas être dans le futur")
        self.assertFalse(Intervention.objects.exists())

    def test_equipement_pre_rempli_depuis_la_fiche(self):
        self.client.force_login(self.tech_a)
        reponse = self.client.get(reverse("interventions:ajouter"), {"equipement": self.radar.pk})
        self.assertEqual(str(reponse.context["form"]["equipement"].value()), str(self.radar.pk))

    # --- F4.5 : mise à jour automatique du statut ---

    def test_corrective_resolue_rend_l_equipement_fonctionnel(self):
        self.client.force_login(self.tech_a)
        self.saisir(panne_resolue="on")
        self.vhf.refresh_from_db()
        self.assertEqual(self.vhf.statut, Statut.FONCTIONNEL)
        ligne = HistoriqueStatut.objects.get(equipement=self.vhf)
        self.assertEqual(ligne.auteur, self.tech_a)
        self.assertIn("Intervention corrective", ligne.commentaire)

    def test_corrective_non_resolue_met_en_maintenance(self):
        self.client.force_login(self.tech_a)
        self.saisir()
        self.vhf.refresh_from_db()
        self.assertEqual(self.vhf.statut, Statut.EN_MAINTENANCE)

    def test_preventive_ne_change_pas_le_statut(self):
        self.client.force_login(self.tech_a)
        self.saisir(type=self.preventive.pk, panne_resolue="on")
        self.vhf.refresh_from_db()
        self.assertEqual(self.vhf.statut, Statut.EN_PANNE)
        self.assertFalse(Intervention.objects.get().panne_resolue)  # case ignorée hors corrective

    def test_modifier_pour_resoudre_la_panne(self):
        self.client.force_login(self.tech_a)
        self.saisir()
        intervention = Intervention.objects.get()
        self.client.post(reverse("interventions:modifier", args=[intervention.pk]), {
            "date": AUJOURDHUI.isoformat(), "equipement": self.vhf.pk, "type": self.corrective.pk,
            "commentaire": "Module remplacé, essais OK", "panne_resolue": "on",
        })
        self.vhf.refresh_from_db()
        self.assertEqual(self.vhf.statut, Statut.FONCTIONNEL)

    def test_ancienne_intervention_ne_change_pas_le_statut_actuel(self):
        ancienne = Intervention.objects.create(
            date=AUJOURDHUI - timedelta(days=10), equipement=self.vhf,
            technicien=self.fiche_a, type=self.corrective,
        )
        Intervention.objects.create(date=AUJOURDHUI, equipement=self.vhf, technicien=self.fiche_a, type=self.preventive)
        self.client.force_login(self.tech_a)
        self.client.post(reverse("interventions:modifier", args=[ancienne.pk]), {
            "date": ancienne.date.isoformat(), "equipement": self.vhf.pk, "type": self.corrective.pk,
            "commentaire": "Correction du commentaire", "panne_resolue": "on",
        })
        self.vhf.refresh_from_db()
        self.assertEqual(self.vhf.statut, Statut.EN_PANNE)

    # --- F4.2 : modification ---

    def test_technicien_ne_modifie_que_ses_interventions(self):
        celle_de_b = Intervention.objects.create(equipement=self.radar, technicien=self.fiche_b, type=self.preventive)
        self.client.force_login(self.tech_a)
        self.assertEqual(self.client.get(reverse("interventions:modifier", args=[celle_de_b.pk])).status_code, 403)
        fiche = self.client.get(reverse("interventions:detail", args=[celle_de_b.pk]))
        self.assertNotContains(fiche, reverse("interventions:modifier", args=[celle_de_b.pk]))

        self.client.force_login(self.tech_b)
        self.assertEqual(self.client.get(reverse("interventions:modifier", args=[celle_de_b.pk])).status_code, 200)

    def test_admin_modifie_toutes_les_interventions(self):
        celle_de_b = Intervention.objects.create(equipement=self.radar, technicien=self.fiche_b, type=self.preventive)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("interventions:modifier", args=[celle_de_b.pk])).status_code, 200)

    # --- F4.3 : liste et filtres ---

    def test_filtres_periode_technicien_type(self):
        Intervention.objects.create(date=AUJOURDHUI - timedelta(days=40), equipement=self.radar, technicien=self.fiche_a, type=self.preventive)
        recente = Intervention.objects.create(date=AUJOURDHUI, equipement=self.vhf, technicien=self.fiche_b, type=self.corrective)
        self.client.force_login(self.tech_a)
        url = reverse("interventions:liste")

        def resultats(**params):
            return list(self.client.get(url, params).context["page"])

        self.assertEqual(resultats(du=(AUJOURDHUI - timedelta(days=7)).isoformat()), [recente])
        self.assertEqual(resultats(technicien=self.fiche_b.pk), [recente])
        self.assertEqual(resultats(type=self.corrective.pk), [recente])
        self.assertEqual(resultats(equipement=self.vhf.pk), [recente])
        self.assertEqual(len(resultats(du="pas-une-date")), 2)

    # --- F4.4 : historique des pannes sur la fiche équipement ---

    def test_fiche_equipement_affiche_historique_des_pannes(self):
        self.client.force_login(self.tech_a)
        self.saisir()
        fiche = self.client.get(reverse("equipements:detail", args=[self.vhf.pk]))
        self.assertEqual(fiche.context["nb_correctives"], 1)
        self.assertContains(fiche, "Panne non résolue")
        self.assertContains(fiche, "Nouvelle intervention")
