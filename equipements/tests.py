"""Tests du module 2 : modèle de données (RG1 à RG6) et pages des équipements."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, definir_role
from emplacements.models import Emplacement
from interventions.models import Intervention
from referentiels.models import Categorie, Fournisseur, Technicien, TypeEquipement, TypeIntervention

from .models import Equipement, HistoriqueStatut, Statut


class ModeleDeDonneesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.radar = TypeEquipement.objects.create(libelle="Radar")
        cls.salle = Emplacement.objects.create(zone="Salle technique", batiment="Tour de contrôle")
        cls.fournisseur = Fournisseur.objects.create(nom="Thales")
        cls.equipement = Equipement.objects.create(
            nom="Radar primaire", numero_serie="RAD-001", marque="Thales",
            type=cls.radar, emplacement=cls.salle, fournisseur=cls.fournisseur,
        )

    def test_statut_par_defaut_fonctionnel(self):
        self.assertEqual(self.equipement.statut, Statut.FONCTIONNEL)

    def test_rg6_numero_serie_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Equipement.objects.create(
                nom="Doublon", numero_serie="RAD-001", marque="X",
                type=self.radar, emplacement=self.salle,
            )

    def test_rg6_numero_serie_unique_sans_tenir_compte_des_majuscules(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Equipement.objects.create(
                nom="Doublon", numero_serie=" rad-001 ", marque="X",
                type=self.radar, emplacement=self.salle,
            )

    def test_rg6_message_clair_dans_les_formulaires(self):
        doublon = Equipement(
            nom="Doublon", numero_serie="rad-001", marque="X",
            type=self.radar, emplacement=self.salle,
        )
        with self.assertRaisesMessage(ValidationError, "possède déjà ce numéro de série"):
            doublon.full_clean()

    def test_rg1_rg2_type_et_emplacement_obligatoires(self):
        incomplet = Equipement(nom="Sans type", numero_serie="X-1", marque="X")
        with self.assertRaises(ValidationError) as ctx:
            incomplet.full_clean()
        self.assertIn("type", ctx.exception.message_dict)
        self.assertIn("emplacement", ctx.exception.message_dict)

    def test_rg3_fournisseur_facultatif(self):
        sans_fournisseur = Equipement(
            nom="Onduleur", numero_serie="OND-1", marque="APC",
            type=self.radar, emplacement=self.salle,
        )
        sans_fournisseur.full_clean()  # ne doit pas lever d'erreur

    def test_type_et_emplacement_utilises_ne_peuvent_pas_etre_supprimes(self):
        with self.assertRaises(ProtectedError):
            self.radar.delete()
        with self.assertRaises(ProtectedError):
            self.salle.delete()
        with self.assertRaises(ProtectedError):
            self.fournisseur.delete()

    def test_rg4_rg5_intervention_et_protection_de_l_equipement(self):
        technicien = Technicien.objects.create(nom="Ngono", prenom="Paul", unite="IRE")
        corrective = TypeIntervention.objects.create(libelle="Corrective", est_corrective=True)
        Intervention.objects.create(equipement=self.equipement, technicien=technicien, type=corrective)

        self.assertEqual(self.equipement.interventions.count(), 1)
        # Un équipement qui a un historique d'interventions ne peut pas être effacé par erreur.
        with self.assertRaises(ProtectedError):
            self.equipement.delete()

    def test_libelles_de_referentiel_uniques(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TypeEquipement.objects.create(libelle="radar")

    def test_emplacement_unique_par_batiment(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Emplacement.objects.create(zone="salle technique", batiment="tour de contrôle")


class PagesEquipementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("admin", password="x")
        cls.tech = User.objects.create_user("tech", password="x")
        cls.sans_role = User.objects.create_user("sansrole", password="x")
        definir_role(cls.admin, ADMINISTRATEUR)
        definir_role(cls.tech, TECHNICIEN)

        cls.radar = TypeEquipement.objects.create(libelle="Radar")
        cls.vhf = TypeEquipement.objects.create(libelle="VHF")
        cls.vigie = Emplacement.objects.create(zone="Vigie", batiment="Tour de contrôle")
        cls.radar1 = Equipement.objects.create(
            nom="Radar primaire", numero_serie="RAD-001", marque="Thales", type=cls.radar, emplacement=cls.vigie,
        )
        cls.vhf1 = Equipement.objects.create(
            nom="Émetteur VHF 118.1", numero_serie="VHF-118", marque="Rohde & Schwarz",
            type=cls.vhf, emplacement=cls.vigie, statut=Statut.EN_PANNE,
        )

    def donnees_formulaire(self, **modifs):
        donnees = {
            "nom": "Onduleur salle technique", "numero_serie": "OND-777", "marque": "APC",
            "type": self.radar.pk, "emplacement": self.vigie.pk, "fournisseur": "",
            "date_installation": "2024-03-15", "statut": Statut.FONCTIONNEL,
        }
        donnees.update(modifs)
        return donnees

    # --- Consultation : les deux rôles (F2.4, F2.5, F2.6) ---

    def test_liste_et_fiche_accessibles_aux_deux_roles(self):
        for user in (self.admin, self.tech):
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertContains(self.client.get(reverse("equipements:liste")), "Radar primaire")
                self.assertContains(self.client.get(reverse("equipements:detail", args=[self.radar1.pk])), "RAD-001")

    def test_fiche_avec_historique_sans_auteur(self):
        # Changements créés par init_demo : aucun auteur, la fiche doit quand même s'afficher.
        HistoriqueStatut.objects.create(
            equipement=self.vhf1, ancien_statut=Statut.FONCTIONNEL, nouveau_statut=Statut.EN_PANNE,
        )
        self.client.force_login(self.tech)
        self.assertContains(self.client.get(reverse("equipements:detail", args=[self.vhf1.pk])), "VHF-118")

    def test_utilisateur_sans_role_refuse(self):
        self.client.force_login(self.sans_role)
        self.assertEqual(self.client.get(reverse("equipements:liste")).status_code, 403)

    def test_recherche_par_numero_de_serie(self):
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("equipements:liste"), {"q": "vhf-118"})
        self.assertContains(reponse, "Émetteur VHF")
        self.assertNotContains(reponse, "Radar primaire")

    def test_tri_par_colonne(self):
        self.client.force_login(self.tech)
        url = reverse("equipements:liste")

        def series(tri):
            return [e.numero_serie for e in self.client.get(url, {"tri": tri}).context["page"]]

        self.assertEqual(series("serie"), ["RAD-001", "VHF-118"])
        self.assertEqual(series("-serie"), ["VHF-118", "RAD-001"])
        self.assertEqual(self.client.get(url, {"tri": "inconnu"}).context["tri"], "")  # colonne non autorisée
        # En-tête actif : sens indiqué, et le clic suivant inverse l'ordre
        reponse = self.client.get(url, {"tri": "serie", "q": "a"})
        self.assertContains(reponse, 'aria-sort="ascending"')
        self.assertContains(reponse, 'href="?tri=-serie&amp;q=a"')  # la recherche est conservée

    def test_fil_d_ariane(self):
        self.client.force_login(self.tech)
        fiche = self.client.get(reverse("equipements:detail", args=[self.radar1.pk]))
        self.assertContains(fiche, 'aria-label="Fil d\'Ariane"')
        self.assertEqual(fiche.context["fil_ariane"]["url"], reverse("equipements:liste"))
        self.assertNotIn("fil_ariane", self.client.get(reverse("equipements:liste")).context)

    def test_liste_vide(self):
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("equipements:liste"), {"q": "introuvable"})
        self.assertContains(reponse, "Aucun équipement ne correspond à ces critères")
        self.assertContains(reponse, "Effacer la recherche et les filtres")
        # Le bouton d'ajout n'est proposé qu'à l'administrateur
        Equipement.objects.all().delete()
        self.assertNotContains(self.client.get(reverse("equipements:liste")), "Ajouter un équipement")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("equipements:liste")), "Ajouter un équipement")

    def test_filtres_type_et_statut(self):
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("equipements:liste"), {"statut": Statut.EN_PANNE})
        self.assertEqual([e.nom for e in reponse.context["page"]], ["Émetteur VHF 118.1"])
        reponse = self.client.get(reverse("equipements:liste"), {"type": self.radar.pk})
        self.assertEqual([e.nom for e in reponse.context["page"]], ["Radar primaire"])

    def test_etiquettes_des_filtres_actifs(self):
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("equipements:liste"), {"q": "vhf", "statut": Statut.EN_PANNE, "type": self.vhf.pk})
        puces = {p["libelle"]: p for p in reponse.context["puces"]}
        self.assertEqual(puces["Statut"]["valeur"], "En panne")
        self.assertEqual(str(puces["Type"]["valeur"]), "VHF")
        # Retirer le statut conserve la recherche et le type
        self.assertNotIn("statut=", puces["Statut"]["url_retrait"])
        self.assertIn("q=vhf", puces["Statut"]["url_retrait"])
        self.assertIn(f"type={self.vhf.pk}", puces["Statut"]["url_retrait"])

    def test_filtre_invalide_ignore(self):
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("equipements:liste"), {"type": "abc", "statut": "INCONNU"})
        self.assertEqual(reponse.context["page"].paginator.count, 2)

    def test_pagination_20_par_page(self):
        for n in range(25):
            Equipement.objects.create(nom=f"Poste {n}", numero_serie=f"PC-{n}", marque="HP", type=self.vhf, emplacement=self.vigie)
        self.client.force_login(self.tech)
        reponse = self.client.get(reverse("equipements:liste"))
        self.assertEqual(len(reponse.context["page"]), 20)
        self.assertEqual(reponse.context["page"].paginator.num_pages, 2)

    # --- Droits ---

    def test_technicien_change_le_statut_mais_ne_gere_pas_le_parc(self):  # F2.7
        self.client.force_login(self.tech)
        fiche = self.client.get(reverse("equipements:detail", args=[self.radar1.pk]))
        self.assertContains(fiche, "Changer le statut")
        self.assertNotContains(fiche, reverse("equipements:modifier", args=[self.radar1.pk]))
        self.assertNotContains(self.client.get(reverse("equipements:liste")), "Nouvel équipement")
        for url in (reverse("equipements:ajouter"), reverse("equipements:modifier", args=[self.radar1.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(reverse("equipements:supprimer", args=[self.radar1.pk])).status_code, 403)

        self.client.post(reverse("equipements:statut", args=[self.radar1.pk]),
                         {"statut": Statut.EN_PANNE, "commentaire": "Perte de signal"})
        self.radar1.refresh_from_db()
        self.assertEqual(self.radar1.statut, Statut.EN_PANNE)
        ligne = HistoriqueStatut.objects.get(equipement=self.radar1)
        self.assertEqual((ligne.ancien_statut, ligne.nouveau_statut), (Statut.FONCTIONNEL, Statut.EN_PANNE))
        self.assertEqual(ligne.auteur, self.tech)
        self.assertEqual(ligne.commentaire, "Perte de signal")

    def test_changement_vers_le_meme_statut_refuse(self):
        self.client.force_login(self.tech)
        self.client.post(reverse("equipements:statut", args=[self.radar1.pk]), {"statut": Statut.FONCTIONNEL})
        self.assertFalse(HistoriqueStatut.objects.exists())

    # --- Gestion par l'administrateur (F2.1, F2.2, F2.3) ---

    def test_admin_ajoute_un_equipement(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("equipements:ajouter"), self.donnees_formulaire())
        equipement = Equipement.objects.get(numero_serie="OND-777")
        self.assertRedirects(reponse, reverse("equipements:detail", args=[equipement.pk]))
        self.assertEqual(equipement.historique_statuts.get().nouveau_statut, Statut.FONCTIONNEL)

    def test_numero_de_serie_en_double_message_clair(self):  # RG6
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("equipements:ajouter"), self.donnees_formulaire(numero_serie="rad-001"))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "déjà utilisé par l&#x27;équipement « Radar primaire »")

    def test_champs_obligatoires_controles(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("equipements:ajouter"), self.donnees_formulaire(nom="", type=""))
        self.assertEqual(set(reponse.context["form"].errors), {"nom", "type"})

    def test_modification_garde_son_propre_numero(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(
            reverse("equipements:modifier", args=[self.radar1.pk]),
            self.donnees_formulaire(nom="Radar primaire PSR", numero_serie="RAD-001", statut=Statut.EN_MAINTENANCE),
        )
        self.assertRedirects(reponse, reverse("equipements:detail", args=[self.radar1.pk]))
        self.radar1.refresh_from_db()
        self.assertEqual(self.radar1.nom, "Radar primaire PSR")
        self.assertEqual(self.radar1.historique_statuts.get().nouveau_statut, Statut.EN_MAINTENANCE)

    def test_suppression_apres_confirmation(self):
        self.client.force_login(self.admin)
        url = reverse("equipements:supprimer", args=[self.vhf1.pk])
        self.assertContains(self.client.get(url), "Oui, supprimer")
        self.assertTrue(Equipement.objects.filter(pk=self.vhf1.pk).exists())
        self.assertRedirects(self.client.post(url), reverse("equipements:liste"))
        self.assertFalse(Equipement.objects.filter(pk=self.vhf1.pk).exists())

    def test_suppression_bloquee_si_interventions(self):
        technicien = Technicien.objects.create(nom="Ngono", prenom="Paul", unite="IRE")
        type_i = TypeIntervention.objects.create(libelle="Préventive")
        Intervention.objects.create(equipement=self.radar1, technicien=technicien, type=type_i)
        self.client.force_login(self.admin)
        url = reverse("equipements:supprimer", args=[self.radar1.pk])
        self.assertContains(self.client.get(url), "ne peut pas être supprimé")
        self.client.post(url)
        self.assertTrue(Equipement.objects.filter(pk=self.radar1.pk).exists())


class CommandeInitDonneesTests(TestCase):
    def test_creation_puis_relance_sans_doublon(self):
        call_command("init_donnees", stdout=StringIO())
        nb = (TypeEquipement.objects.count(), TypeIntervention.objects.count(), Emplacement.objects.count())
        self.assertTrue(TypeIntervention.objects.get(libelle="Corrective").est_corrective)
        call_command("init_donnees", stdout=StringIO())
        self.assertEqual(nb, (TypeEquipement.objects.count(), TypeIntervention.objects.count(), Emplacement.objects.count()))

    def test_six_categories_de_deux_types(self):
        call_command("init_donnees", stdout=StringIO())
        self.assertEqual(Categorie.objects.count(), 6)
        for categorie in Categorie.objects.all():
            with self.subTest(categorie=categorie.code):
                self.assertEqual(categorie.types.count(), 2)

    def test_init_demo_deux_equipements_par_categorie(self):
        call_command("init_demo", stdout=StringIO())
        self.assertEqual(Equipement.objects.count(), 12)
        for categorie in Categorie.objects.all():
            with self.subTest(categorie=categorie.code):
                self.assertEqual(Equipement.objects.filter(type__categorie=categorie).count(), 2)
        # Chaque équipement a sa ligne d'historique de création
        self.assertEqual(HistoriqueStatut.objects.count(), 12)
        # Relance sans doublon
        call_command("init_demo", stdout=StringIO())
        self.assertEqual(Equipement.objects.count(), 12)

    def test_filtre_par_categorie(self):
        call_command("init_demo", stdout=StringIO())
        user = get_user_model().objects.create_user("c", password="x")
        definir_role(user, TECHNICIEN)
        self.client.force_login(user)
        nav = Categorie.objects.get(code="NAV")
        reponse = self.client.get(reverse("equipements:liste"), {"categorie": nav.pk})
        self.assertEqual(
            sorted(e.nom for e in reponse.context["page"]),
            ["ILS Localizer piste 12", "VOR/DME Douala"],
        )
        self.assertEqual(reponse.context["puces"][0]["libelle"], "Catégorie")

    def test_formulaire_types_groupes_par_categorie(self):
        call_command("init_donnees", stdout=StringIO())
        from .forms import EquipementForm

        groupes = [libelle for libelle, _ in EquipementForm().fields["type"].choices][1:]
        self.assertEqual(groupes[:2], ["Communication", "Navigation"])


class AdministrationTests(TestCase):
    """Chaque table est consultable dans l'interface /admin/."""

    def test_pages_admin_accessibles(self):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_superuser("admin", "admin@test.local", "MotDePasse-Test-1")
        self.client.force_login(admin)
        for url in [
            "/admin/",
            "/admin/referentiels/typeequipement/", "/admin/referentiels/typeintervention/",
            "/admin/referentiels/fournisseur/", "/admin/referentiels/technicien/",
            "/admin/emplacements/emplacement/",
            "/admin/equipements/equipement/", "/admin/equipements/equipement/add/",
            "/admin/equipements/historiquestatut/",
            "/admin/interventions/intervention/", "/admin/interventions/intervention/add/",
            "/admin/journal/journalaction/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
