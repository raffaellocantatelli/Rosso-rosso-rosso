#!/usr/bin/env python3
"""Genera alpha.html: pagina autosufficiente del Canone Alpha.

Le 74 carte vengono incorporate nella pagina, così il Canone non dipende
più da /api/alpha né da /api/alpha/collasso (entrambi assenti in produzione).
"""
import json
import pathlib

BASE = pathlib.Path(__file__).parent
dati = json.loads((BASE / "alpha_dati.json").read_text(encoding="utf-8"))

carte = dati["carte"]
manifesto = dati["manifesto"]
chiavi = dati.get("interpretazioni_chiave", {})
cicli = dati["stato_costruzione"]["cicli_completati"]
stati = dati["stato_costruzione"]["stati_scritti"]

payload = json.dumps(
    {"carte": carte, "chiavi": chiavi, "cicli": cicli},
    ensure_ascii=False, separators=(",", ":"),
).replace("</", "<\\/")

HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tarocchi Quantici — Canone Alpha</title>
<style>
  *, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
  :root {
    --bg:#0c0c0e; --surface:#141418; --border:#2a2a32;
    --gold:#c9a84c; --gold-dim:#8a6f2e; --text:#e8e4d8; --text-dim:#7a7468;
    --radius:8px; --font:'Georgia','Times New Roman',serif; --mono:'Courier New',monospace;
  }
  body { background:var(--bg); color:var(--text); font-family:var(--font);
         min-height:100vh; padding:2rem 1rem 4rem; overflow-x:hidden; }
  .container { max-width:680px; margin:0 auto; }

  header { text-align:center; margin-bottom:2.5rem; }
  header h1 { font-size:clamp(1.4rem,4vw,2rem); font-weight:normal;
              letter-spacing:0.1em; color:var(--gold); }
  header .conteggio { margin-top:0.5rem; color:var(--text-dim);
                      font-size:0.85rem; letter-spacing:0.06em; }
  .formula { display:inline-block; margin-top:1rem; font-size:0.78rem;
             letter-spacing:0.12em; color:var(--gold-dim); font-family:var(--mono);
             border:1px solid var(--border); padding:0.35rem 0.9rem; border-radius:3px;
             max-width:100%; }
  .principio { margin-top:1rem; color:var(--text-dim); font-size:0.82rem;
               font-style:italic; line-height:1.6; }
  .nav-link { display:inline-block; margin-top:1rem; font-size:0.75rem;
              color:var(--text-dim); letter-spacing:0.08em; text-decoration:none; }
  .nav-link:hover { color:var(--gold-dim); }

  .section-title { font-size:0.7rem; letter-spacing:0.18em; text-transform:uppercase;
                   color:var(--gold-dim); margin-bottom:1rem; }

  .selettore { background:var(--surface); border:1px solid var(--border);
               border-radius:var(--radius); padding:1.5rem; margin-bottom:2rem; }
  .griglia { display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem; margin-bottom:1.25rem; }
  label { display:block; font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase;
          color:var(--text-dim); margin-bottom:0.35rem; }
  select { width:100%; background:var(--bg); border:1px solid var(--border);
           border-radius:4px; color:var(--text); font-family:var(--font);
           font-size:0.9rem; padding:0.45rem 2rem 0.45rem 0.6rem; outline:none;
           -webkit-appearance:none; appearance:none;
           background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath fill='%237a7468' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E");
           background-repeat:no-repeat; background-position:right 0.7rem center; }
  select:focus { border-color:var(--gold-dim); }
  .simbolo-preview { font-size:1.8rem; text-align:center; color:var(--gold);
                     min-height:2.4rem; line-height:1; margin-top:0.2rem; }
  .ciclo-preview { font-size:0.72rem; color:var(--text-dim); text-align:center;
                   letter-spacing:0.1em; margin-top:0.2rem; }

  .azioni { display:flex; gap:0.6rem; flex-wrap:wrap; }
  .btn { border:none; border-radius:var(--radius); cursor:pointer;
         font-family:var(--font); font-size:1rem; letter-spacing:0.1em;
         padding:0.85rem 1rem; transition:background 0.15s,color 0.15s; }
  .btn-oro { flex:1 1 12rem; background:var(--gold-dim); color:var(--bg); }
  .btn-oro:hover { background:var(--gold); }
  .btn-ghost { flex:0 1 auto; background:transparent; color:var(--text-dim);
               border:1px solid var(--border); }
  .btn-ghost:hover { color:var(--gold); border-color:var(--gold-dim); }

  #risultato { display:none; }
  #risultato.visible { display:block; }
  .collasso-box { background:var(--surface); border:1px solid var(--gold-dim);
                  border-radius:var(--radius); padding:2rem 1.25rem; text-align:center;
                  margin-bottom:2rem; }
  .collasso-carta { font-size:1.1rem; letter-spacing:0.08em; }
  .collasso-simbolo { font-size:3rem; color:var(--gold); margin:0.75rem 0; line-height:1; }
  .collasso-formula { font-size:0.7rem; font-family:var(--mono); color:var(--text-dim);
                      letter-spacing:0.08em; margin-bottom:1.5rem; word-break:break-word; }
  .collasso-significato { font-size:clamp(1.15rem,4.2vw,1.5rem); line-height:1.5;
                          color:var(--gold); font-style:italic; }
  .chiave { margin-top:1.25rem; padding-top:1.25rem; border-top:1px solid var(--border);
            font-size:0.85rem; color:var(--text-dim); line-height:1.5; }
  .chiave b { color:var(--text); font-weight:normal; }

  .assi-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-top:1rem; }
  .asse-item { background:var(--bg); border:1px solid var(--border);
               border-radius:4px; padding:0.8rem 1rem; }
  .asse-label { font-size:0.62rem; letter-spacing:0.14em; text-transform:uppercase;
                color:var(--gold-dim); margin-bottom:0.3rem; font-family:var(--mono); }
  .asse-testo { font-size:0.88rem; line-height:1.4; }
  .asse-item.active { border-color:var(--gold-dim); background:var(--surface); }
  .asse-item.active .asse-label, .asse-item.active .asse-testo { color:var(--gold); }

  .divider { border:none; border-top:1px solid var(--border); margin:2.5rem 0; }

  .tag { font-size:0.65rem; letter-spacing:0.14em; text-transform:uppercase;
         color:var(--text-dim); background:var(--surface); border:1px solid var(--border);
         padding:0.3rem 0.65rem; border-radius:3px; cursor:pointer;
         font-family:var(--font); transition:all 0.15s; }
  .tag:hover, .tag.active { border-color:var(--gold-dim); color:var(--gold-dim); }
  .cicli-lista { display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:1.5rem; }
  .carte-lista { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:0.5rem; }
  .carta-mini { background:var(--surface); border:1px solid var(--border); border-radius:4px;
                padding:0.6rem 0.8rem; cursor:pointer; display:flex; align-items:center;
                gap:0.6rem; text-align:left; font-family:var(--font); color:var(--text);
                transition:border-color 0.15s; width:100%; }
  .carta-mini:hover { border-color:var(--gold-dim); }
  .carta-mini .simbolo { font-size:1.1rem; color:var(--gold-dim); flex-shrink:0; }
  .carta-mini .nome { font-size:0.85rem; line-height:1.2; }

  #errore { display:none; background:var(--surface); border:1px solid #8b1c1c;
            border-radius:var(--radius); padding:1.25rem; color:#d08a8a;
            font-size:0.9rem; line-height:1.6; }

  @media (max-width:540px) {
    .griglia, .assi-grid { grid-template-columns:1fr; }
    .carte-lista { grid-template-columns:repeat(auto-fill,minmax(135px,1fr)); }
  }
</style>
</head>
<body>
<script src="soglia.js"></script>
<script src="nav.js"></script>
<div class="container">

  <header>
    <h1>Canone Alpha</h1>
    <div class="conteggio">__CONTEGGIO__</div>
    <div class="formula">__PRINCIPIO__</div>
    <p class="principio">__NONPREDIZIONE__</p>
    <a href="index.html" class="nav-link">← Tarocchi Quantici R³∞</a>
  </header>

  <div id="errore"></div>

  <p class="section-title">Motore di collasso</p>
  <div class="selettore">
    <div class="griglia">
      <div>
        <label for="sel-carta">Carta</label>
        <select id="sel-carta"><option value="">— scegli —</option></select>
        <div class="simbolo-preview" id="prev-simbolo"></div>
        <div class="ciclo-preview" id="prev-ciclo"></div>
      </div>
      <div>
        <label for="sel-asse">Asse</label>
        <select id="sel-asse">
          <option value="nord">Nord — radice · inconscio</option>
          <option value="est">Est — azione · futuro</option>
          <option value="sud" selected>Sud — emozione · presente</option>
          <option value="ovest">Ovest — riflessione · passato</option>
        </select>
      </div>
      <div>
        <label for="sel-polarita">Polarità</label>
        <select id="sel-polarita">
          <option value="luce">Luce — manifestazione costruttiva</option>
          <option value="ombra">Ombra — manifestazione d'ombra</option>
        </select>
      </div>
    </div>
    <div class="azioni">
      <button class="btn btn-oro" id="btn-collassa">Collassa il significato</button>
      <button class="btn btn-ghost" id="btn-caso">Carta a caso</button>
    </div>
  </div>

  <div id="risultato">
    <div class="collasso-box">
      <div class="collasso-carta" id="r-carta"></div>
      <div class="collasso-simbolo" id="r-simbolo"></div>
      <div class="collasso-formula" id="r-formula"></div>
      <div class="collasso-significato" id="r-significato"></div>
      <div class="chiave" id="r-chiave"></div>
    </div>

    <p class="section-title">Tutti gli 8 stati di questa carta</p>
    <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem">
      <button class="tag active" id="tab-luce">Luce</button>
      <button class="tag" id="tab-ombra">Ombra</button>
    </div>
    <div class="assi-grid" id="r-assi"></div>
  </div>

  <hr class="divider">

  <p class="section-title">Sfoglia per ciclo</p>
  <div class="cicli-lista" id="cicli-lista"></div>
  <div class="carte-lista" id="carte-lista"></div>

</div>

<script id="canone-alpha" type="application/json">__PAYLOAD__</script>
<script>
(function () {
  "use strict";

  var ASSI = ["nord", "est", "sud", "ovest"];
  var DATI, CARTE, CHIAVI, CICLI;

  try {
    DATI = JSON.parse(document.getElementById("canone-alpha").textContent);
    CARTE = DATI.carte; CHIAVI = DATI.chiavi || {}; CICLI = DATI.cicli;
    if (!CARTE || !CARTE.length) throw new Error("nessuna carta");
  } catch (e) {
    var box = document.getElementById("errore");
    box.style.display = "block";
    box.textContent = "Il Canone non si è caricato: " + e.message +
      ". I dati sono incorporati in questa pagina, quindi l'errore indica un file danneggiato.";
    return;
  }

  var cartaAttiva = null, cicloAttivo = CICLI[0];

  function $(id) { return document.getElementById(id); }
  function perNome(n) {
    for (var i = 0; i < CARTE.length; i++) if (CARTE[i].nome === n) return CARTE[i];
    return null;
  }
  function maiuscola(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  // ── Selettore ──────────────────────────────────────────────────────────────
  var sel = $("sel-carta");
  CARTE.forEach(function (c) {
    var o = document.createElement("option");
    o.value = c.nome;
    o.textContent = c.simbolo + "  " + c.nome;
    sel.appendChild(o);
  });

  function aggiornaPrev() {
    var c = perNome(sel.value);
    $("prev-simbolo").textContent = c ? c.simbolo : "";
    $("prev-ciclo").textContent = c ? c.ciclo : "";
  }
  sel.addEventListener("change", aggiornaPrev);

  // ── Collasso (calcolato qui, senza backend) ────────────────────────────────
  function collassa() {
    var c = perNome(sel.value);
    if (!c) { sel.focus(); return; }
    var asse = $("sel-asse").value, pol = $("sel-polarita").value;

    cartaAttiva = c;
    $("r-carta").textContent = c.nome;
    $("r-simbolo").textContent = c.simbolo;
    $("r-formula").textContent =
      c.nome.toUpperCase() + " + " + asse.toUpperCase() + " + " + pol.toUpperCase();
    $("r-significato").textContent = c[pol][asse];

    var chiave = CHIAVI[c.nome];
    $("r-chiave").innerHTML = chiave
      ? "<b>" + c.nome + "</b> — " + chiave + "<br>Ciclo: " + c.ciclo
      : "Ciclo: " + c.ciclo;

    disegnaAssi(asse, pol);
    var r = $("risultato");
    r.classList.add("visible");
    r.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function disegnaAssi(asseAttivo, pol) {
    if (!cartaAttiva) return;
    var faccia = cartaAttiva[pol];
    $("r-assi").innerHTML = ASSI.map(function (a) {
      var attivo = a === asseAttivo ? " active" : "";
      return '<div class="asse-item' + attivo + '">' +
             '<div class="asse-label">' + maiuscola(a) + '</div>' +
             '<div class="asse-testo"></div></div>';
    }).join("");
    // testo inserito come nodo, mai come HTML
    var celle = $("r-assi").querySelectorAll(".asse-testo");
    ASSI.forEach(function (a, i) { celle[i].textContent = faccia[a]; });

    $("tab-luce").className = "tag" + (pol === "luce" ? " active" : "");
    $("tab-ombra").className = "tag" + (pol === "ombra" ? " active" : "");
  }

  $("btn-collassa").addEventListener("click", collassa);
  $("tab-luce").addEventListener("click", function () { disegnaAssi($("sel-asse").value, "luce"); });
  $("tab-ombra").addEventListener("click", function () { disegnaAssi($("sel-asse").value, "ombra"); });

  $("btn-caso").addEventListener("click", function () {
    sel.value = CARTE[Math.floor(Math.random() * CARTE.length)].nome;
    $("sel-asse").value = ASSI[Math.floor(Math.random() * 4)];
    $("sel-polarita").value = Math.random() < 0.5 ? "luce" : "ombra";
    aggiornaPrev();
    collassa();
  });

  // ── Sfoglia per ciclo ──────────────────────────────────────────────────────
  var lista = $("cicli-lista");
  CICLI.forEach(function (nome) {
    var b = document.createElement("button");
    b.className = "tag" + (nome === cicloAttivo ? " active" : "");
    b.textContent = nome;
    b.addEventListener("click", function () {
      cicloAttivo = nome;
      lista.querySelectorAll(".tag").forEach(function (t) {
        t.classList.toggle("active", t.textContent === nome);
      });
      disegnaCarte();
    });
    lista.appendChild(b);
  });

  function disegnaCarte() {
    var cont = $("carte-lista");
    cont.innerHTML = "";
    CARTE.filter(function (c) { return c.ciclo === cicloAttivo; }).forEach(function (c) {
      var b = document.createElement("button");
      b.className = "carta-mini";
      var s = document.createElement("span");
      s.className = "simbolo"; s.textContent = c.simbolo;
      var n = document.createElement("span");
      n.className = "nome"; n.textContent = c.nome;
      b.appendChild(s); b.appendChild(n);
      b.addEventListener("click", function () {
        sel.value = c.nome;
        aggiornaPrev();
        collassa();
      });
      cont.appendChild(b);
    });
  }

  disegnaCarte();
})();
</script>
</body>
</html>
"""

conteggio = f"{len(carte)} carte · {len(cicli)} cicli · {stati} stati"
html = (HTML
        .replace("__CONTEGGIO__", conteggio)
        .replace("__PRINCIPIO__", manifesto["principio"])
        .replace("__NONPREDIZIONE__", manifesto["non_predizione"])
        .replace("__PAYLOAD__", payload))

out = BASE / "site" / "alpha.html"
out.write_text(html, encoding="utf-8")
print(f"scritto {out}  ({len(html):,} byte)")
print(f"carte incorporate: {len(carte)} · cicli: {len(cicli)} · stati: {stati}")
