/* La Costellazione — barra di navigazione comune a tutte le pagine.
   Oro su nero, pagina corrente evidenziata. Nascosta in stampa.
   Su schermo largo resta una riga sola; su telefono va a capo
   restringendosi, così tutte le stanze restano raggiungibili. */
(function () {
  var VOCI = [
    ["index.html", "Tarocchi"],
    ["alpha.html", "Alpha"],
    ["parti.html", "Parti"],
    ["viaggi.html", "Viaggi"],
    ["flight_hunter.html", "Flight"],
    ["oracolo.html", "Oracolo"],
    ["parfums.html", "Parfums"],
    ["organo.html", "Organo"],
    ["spesa.html", "Dispensa"],
    ["valigia.html", "Valigia"],
    ["libro.html", "Libro"],
    ["atelier.html", "Atelier"],
    ["opera.html", "Opera"],
    ["creazioni.html", "Creazioni"],
    ["opuscolo.html", "Opuscolo"],
  ];
  var qui = location.pathname.split("/").pop() || "index.html";

  var stile = document.createElement("style");
  stile.textContent =
    /* Flex: le voci vanno a capo da sole, senza dipendere dagli spazi
       nell'HTML (prima erano unite con join("") e la riga non si spezzava). */
    ".nav-costellazione{display:flex;flex-wrap:wrap;justify-content:center;" +
    "align-items:baseline;column-gap:1.22rem;row-gap:0.1rem;" +
    "padding:0.55rem 0.4rem 0.7rem;border-bottom:1px solid #2a2a32;" +
    "margin:-2rem -1rem 2rem;font-family:Georgia,'Times New Roman',serif;" +
    "font-size:0.78rem;letter-spacing:0.14em;text-transform:uppercase;" +
    "line-height:2;max-width:100vw}" +
    ".nav-costellazione a{color:#7a7468;text-decoration:none;white-space:nowrap}" +
    ".nav-costellazione a:hover{color:#c9a84c}" +
    ".nav-costellazione a.qui{color:#c9a84c;border-bottom:1px solid #8a6f2e;" +
    "padding-bottom:2px}" +
    "@media (max-width:720px){.nav-costellazione{font-size:0.68rem;" +
    "letter-spacing:0.08em;column-gap:0.9rem;line-height:1.85;" +
    "margin:-2rem -1rem 1.5rem}}" +
    "@media (max-width:420px){.nav-costellazione{font-size:0.62rem;" +
    "letter-spacing:0.05em;column-gap:0.72rem}}" +
    "@media print{.nav-costellazione{display:none}}";
  document.head.appendChild(stile);

  var nav = document.createElement("nav");
  nav.className = "nav-costellazione";
  nav.setAttribute("aria-label", "La Costellazione");
  nav.innerHTML = VOCI.map(function (v) {
    var corrente = v[0] === qui;
    return '<a href="' + v[0] + '"' +
      (corrente ? ' class="qui" aria-current="page"' : '') + '>' + v[1] + '</a>';
  }).join("");

  function monta() { document.body.insertBefore(nav, document.body.firstChild); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", monta);
  } else {
    monta();
  }
})();
