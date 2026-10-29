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

/* Filtres des listes : appliqués dès qu'une valeur est choisie (pas de bouton « Filtrer »). */
document.querySelectorAll("[data-auto-submit]").forEach(function (champ) {
  champ.addEventListener("change", function () {
    if (champ.form) champ.form.requestSubmit();
  });
});
