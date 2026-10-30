/* AéroTrack : bouton menu de la barre du haut.
   - Grand écran : replie / déplie la barre latérale (choix mémorisé).
   - Petit écran : ouvre la barre latérale par-dessus le contenu. */
(function () {
  var layout = document.getElementById("at-layout");
  var bouton = document.getElementById("at-menu-btn");
  var voile = document.getElementById("at-overlay");
  var petitEcran = window.matchMedia("(max-width: 991.98px)");
  var CLE = "aerotrack.sidebarRepliee";

  function lireChoix() {
    try { return localStorage.getItem(CLE) === "1"; } catch (e) { return false; }
  }

  function ecrireChoix(replie) {
    try { localStorage.setItem(CLE, replie ? "1" : "0"); } catch (e) { /* stockage indisponible */ }
  }

  function majAria() {
    var visible = petitEcran.matches
      ? layout.classList.contains("sidebar-ouverte")
      : !layout.classList.contains("sidebar-repliee");
    bouton.setAttribute("aria-expanded", visible ? "true" : "false");
  }

  function fermerMobile() {
    layout.classList.remove("sidebar-ouverte");
    majAria();
  }

  layout.classList.toggle("sidebar-repliee", lireChoix());
  majAria();
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { layout.classList.add("anime"); });
  });

  bouton.addEventListener("click", function () {
    if (petitEcran.matches) {
      layout.classList.toggle("sidebar-ouverte");
    } else {
      var replie = layout.classList.toggle("sidebar-repliee");
      ecrireChoix(replie);
    }
    majAria();
  });

  voile.addEventListener("click", fermerMobile);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fermerMobile();
  });
  petitEcran.addEventListener("change", fermerMobile);
})();

/* Bouton clair / sombre : bascule le thème Bootstrap (data-bs-theme) et mémorise le choix.
   Le thème de départ est posé dans le <head> (includes/theme_head.html). */
(function () {
  var bouton = document.getElementById("at-theme-btn");
  if (!bouton) return;
  var racine = document.documentElement;

  function majBouton() {
    var texte = racine.getAttribute("data-bs-theme") === "dark" ? "Passer en mode clair" : "Passer en mode sombre";
    bouton.setAttribute("aria-label", texte);
    bouton.title = texte;
  }

  majBouton();
  bouton.addEventListener("click", function () {
    var sombre = racine.getAttribute("data-bs-theme") !== "dark";
    racine.classList.add("at-bascule-theme");  // fondu des couleurs
    racine.setAttribute("data-bs-theme", sombre ? "dark" : "light");
    try { localStorage.setItem("aerotrack.theme", sombre ? "sombre" : "clair"); } catch (e) { /* stockage indisponible */ }
    majBouton();
    document.dispatchEvent(new Event("at-theme"));  // le graphique adapte ses couleurs
    setTimeout(function () { racine.classList.remove("at-bascule-theme"); }, 400);
  });
})();

/* Compteurs (data-compteur) : le chiffre défile de 0 à sa valeur au chargement. */
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll("[data-compteur]").forEach(function (el) {
    var cible = parseInt(el.textContent, 10);
    if (!cible) return;
    var debut = null, duree = 900;
    el.textContent = "0";
    function etape(t) {
      if (debut === null) debut = t;
      var p = Math.min((t - debut) / duree, 1);
      el.textContent = Math.round(cible * (1 - Math.pow(1 - p, 3)));  // ralentit en fin de course
      if (p < 1) requestAnimationFrame(etape);
    }
    requestAnimationFrame(etape);
  });
})();

/* Filtres des listes : appliqués dès qu'une valeur est choisie (pas de bouton « Filtrer »). */
document.querySelectorAll("[data-auto-submit]").forEach(function (champ) {
  champ.addEventListener("change", function () {
    if (champ.form) champ.form.requestSubmit();
  });
});
