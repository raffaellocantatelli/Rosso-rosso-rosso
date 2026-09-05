/* console — Origine protetta: Claudio Terzi [CT-LGAI-001].
 *
 * Una schermata sola, un quadro solo. `/api/quadro` restituisce tutto lo
 * stato in una chiamata: se si facessero cinque letture separate, la pagina
 * si disegnerebbe cinque volte incoerente mentre arrivano — e per qualche
 * secondo mostrerebbe una casa che non è mai esistita.
 *
 * La regola visiva: il verde è l'unica cosa che il prodotto AFFERMA
 * (c'è una riga scritta nel registro). Tutto il resto è grigio, perché se
 * cinque colori affermano qualcosa nessuno significa niente. E il colore
 * non è mai solo: accanto c'è sempre una parola o una forma.
 */

const $ = (s) => document.querySelector(s);
const testo = (el, t) => { el.textContent = t; };
let QUADRO = null, ZONA = null;

const COLORI = { fatta: "#2ee06a", da_fare: "#ffb020", manca: "#ff4d4d" };

async function carica() {
  const r = await fetch("/api/quadro");
  QUADRO = await r.json();
  disegna();
}

/* ---------- lo stato di ogni zona, dedotto da ciò che manca ---------- */
function statoZone() {
  const stati = {};
  for (const z of Object.keys(QUADRO.zone)) stati[z] = "da_fare";
  const d = QUADRO.differenza;
  if (d) {
    for (const o of d.non_spiegati || d.mancanti || []) {
      const z = (o.luogo && (o.luogo.stanza || o.luogo.percorso)) || null;
      if (z) stati[z.split("/")[0]] = "manca";
    }
    // ciò che è stato consegnato e non manca è verificato
    for (const z of Object.keys(stati)) if (stati[z] === "da_fare") stati[z] = "fatta";
  }
  return stati;
}

/* ---------- la pianta ---------- */
function pianta() {
  const p = QUADRO.pianta;
  const box = $("#disegno");
  const legenda = document.querySelector(".legenda");
  // una legenda che spiega tre colori assenti dallo schermo è rumore
  legenda.hidden = !(p && p.zone && p.zone.length);
  if (legenda.hidden) {
    box.innerHTML = '<p class=vuoto>Nessuna pianta caricata. Avvia con '
      + '<code>--pianta pianta.json</code> — si scrive a mano in dieci minuti.</p>';
    return;
  }
  const stati = statoZone();
  const xs = p.zone.flatMap(z => z.punti.map(q => q[0]));
  const ys = p.zone.flatMap(z => z.punti.map(q => q[1]));
  const m = 8;
  const x0 = Math.min(...xs) - m, y0 = Math.min(...ys) - m;
  const w = Math.max(...xs) - Math.min(...xs) + 2 * m;
  const h = Math.max(...ys) - Math.min(...ys) + 2 * m;

  const dentro = (pt, pol) => {
    let d = false;
    for (let i = 0, j = pol.length - 1; i < pol.length; j = i++) {
      const [xi, yi] = pol[i], [xj, yj] = pol[j];
      if ((yi > pt[1]) !== (yj > pt[1]) &&
          pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) d = !d;
    }
    return d;
  };
  // il punto più interno: il centro del riquadro di una stanza a L cade fuori
  const puntoEtichetta = (pol) => {
    const ax = Math.min(...pol.map(q => q[0])), bx = Math.max(...pol.map(q => q[0]));
    const ay = Math.min(...pol.map(q => q[1])), by = Math.max(...pol.map(q => q[1]));
    let best = null, punteggio = -1;
    for (let i = 1; i < 20; i++) for (let j = 1; j < 20; j++) {
      const pt = [ax + (bx - ax) * i / 20, ay + (by - ay) * j / 20];
      if (!dentro(pt, pol)) continue;
      const d = Math.min(...pol.map((q, k) => {
        const r = pol[(k + 1) % pol.length];
        const dx = r[0] - q[0], dy = r[1] - q[1], l = dx * dx + dy * dy;
        const t = l ? Math.max(0, Math.min(1, ((pt[0] - q[0]) * dx + (pt[1] - q[1]) * dy) / l)) : 0;
        return Math.hypot(pt[0] - (q[0] + t * dx), pt[1] - (q[1] + t * dy));
      }));
      if (d > punteggio) { punteggio = d; best = pt; }
    }
    return best || [(ax + bx) / 2, (ay + by) / 2];
  };

  box.innerHTML = `<svg viewBox="${x0} ${y0} ${w} ${h}" role="img"
      aria-label="pianta delle zone">${p.zone.map(z => {
    const st = stati[z.nome] || "da_fare";
    const col = COLORI[st];
    const [cx, cy] = puntoEtichetta(z.punti);
    const n = QUADRO.zone[z.nome] || 0;
    const corpo = Math.max(2.2, Math.min(4.4,
      (Math.max(...z.punti.map(q => q[0])) - Math.min(...z.punti.map(q => q[0]))) * 1.3 / z.nome.length));
    return `<g class="zona" data-zona="${z.nome}" tabindex="0" role="button"
        aria-label="${z.nome}, ${n} oggetti, ${st.replace('_', ' ')}">
      <polygon points="${z.punti.map(q => q.join(",")).join(" ")}"
        fill="${col}" fill-opacity="${st === 'da_fare' ? .07 : .19}"
        stroke="${col}" stroke-width="1" stroke-linejoin="round"/>
      <text x="${cx}" y="${cy - 1}" font-size="${corpo.toFixed(2)}" fill="#e8ecf4"
        text-anchor="middle" font-family="ui-monospace,monospace">${z.nome}</text>
      <text x="${cx}" y="${(cy + corpo * 1.25).toFixed(2)}" font-size="${(corpo * .74).toFixed(2)}"
        fill="${col}" text-anchor="middle" font-family="ui-monospace,monospace">${n}</text>
    </g>`;
  }).join("")}</svg>`;

  box.querySelectorAll(".zona").forEach(g => {
    const scegli = () => filtra(g.dataset.zona === ZONA ? null : g.dataset.zona);
    g.onclick = scegli;
    g.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scegli(); } };
  });
  evidenzia();
}

function evidenzia() {
  document.querySelectorAll("#disegno .zona").forEach(g =>
    g.classList.toggle("spenta", ZONA !== null && g.dataset.zona !== ZONA));
}

function filtra(zona) {
  ZONA = zona;
  testo($("#zona-scelta"), zona || "");
  testo($("#filtro-attivo"), zona ? `· ${zona}` : "");
  document.querySelectorAll("#elenco li").forEach(li => {
    li.hidden = zona !== null && li.dataset.zona !== zona;
  });
  evidenzia();
}

/* ---------- la linea del tempo della consegna ---------- */
function linea() {
  const c = (QUADRO.consegne || [])[0];
  const ol = $("#linea");
  if (!c) {
    ol.innerHTML = '<li><b>Nessuna consegna</b><span>l\'alloggio non è stato ancora consegnato</span></li>';
    testo($("#alloggio"), "—");
    return;
  }
  testo($("#alloggio"), c.alloggio);
  const tappa = (nome, d) => {
    if (!d) return `<li class="aperto"><b>${nome}</b><span>non ancora</span></li>`;
    const f = d.controfirmata;
    return `<li class="${f ? "fatto" : "aperto"}"><b>${nome}</b>
      <span>${d.momento.replace("T", " ").replace("Z", "")}</span>
      <span class="firma ${f ? "si" : "no"}">${f ? "controfirmata" : "NON controfirmata"}</span></li>`;
  };
  ol.innerHTML = tappa("Consegna", c.consegna)
    + `<li class="${c.riconsegna ? "fatto" : "aperto"}"><b>Soggiorno</b>
        <span>${c.consegna && c.riconsegna ? "concluso" : "in corso"}</span></li>`
    + tappa("Riconsegna", c.riconsegna);

  const senza = [c.consegna, c.riconsegna].filter(x => x && !x.controfirmata).length;
  const av = $("#avviso-firma");
  av.hidden = senza === 0;
  if (senza) av.innerHTML = `<b>${senza} stato${senza > 1 ? "i" : ""} senza controfirma.</b>
    Una catena che una parte sola può rigenerare dimostra solo di essere coerente
    con sé stessa. In una lite non basta.`;
}

/* ---------- la differenza ---------- */
function differenza() {
  const d = QUADRO.differenza, box = $("#differenza");
  if (!d) { box.innerHTML = ""; return; }
  const comprati = d.comprati || [];
  const mancanti = d.non_spiegati || d.mancanti || [];
  if (!comprati.length && !mancanti.length) {
    box.innerHTML = '<p class=vuoto>Nessuna differenza: tutto al suo posto.</p>';
    return;
  }
  box.innerHTML =
    comprati.map(o => `<div class="riga comprato"><span class="segnale">comprato</span>
      <span class="t">${o.titolo || ""}</span>
      <span class="p">${o.vendita ? o.vendita.prezzo + " " + o.vendita.valuta : ""}</span></div>`).join("")
    + mancanti.map(o => `<div class="riga manca"><span class="segnale">non spiegato</span>
      <span class="t">${o.titolo || ""}</span></div>`).join("");
}

/* ---------- il registro ---------- */
function registro() {
  const ul = $("#elenco");
  ul.innerHTML = QUADRO.oggetti.map(o => `<li data-zona="${o.zona || ""}">
      <span class="tipo">${o.tipo || "altro"}</span>
      <span class="tit">${o.titolo || ""}</span>
      ${o.avvistamenti > 1 ? `<span class="volte">${o.avvistamenti}×</span>` : ""}
      ${o.fonte === "umano" ? '<span class="umano" title="confermato a mano">✎</span>' : ""}
    </li>`).join("") || '<li><span class="vuoto">Il registro è vuoto. '
      + '<a href="/">Apri la telecamera</a> e comincia a fotografare.</span></li>';

  const f = $("#fusioni");
  f.hidden = !QUADRO.fusioni.length;
  if (QUADRO.fusioni.length) {
    f.innerHTML = `<b>${QUADRO.fusioni.length} voci su cui sono finiti titoli diversi.</b> `
      + QUADRO.fusioni.map(x => x.titoli.join(" / ")).join("; ")
      + ". Se sono oggetti diversi, dai a uno un titolo che li distingua.";
  }
}

/* ---------- il mercato ---------- */
function mercato() {
  const ul = $("#vendite");
  const v = QUADRO.vendite || [];
  ul.innerHTML = v.length ? v.map(x => `<li>
      <span class="tit">${x.titolo || ""}</span>
      <span class="pr">${x.prezzo} ${x.valuta}</span></li>`).join("")
    : '<li><span class="vuoto">Nessuna vendita. Niente è ancora stato comprato invece che portato via.</span></li>';

  const c = QUADRO.chiari, box = $("#chiari");
  // Un libro a zero non è una notizia. Uno rotto o aperto sì, sempre: sono
  // le due cose che nessuno deve poter non vedere.
  box.hidden = !c || (!c.emessi && c.conservati && !c.trasferibile);
  if (!box.hidden) {
    box.innerHTML = `Chiari: <b>${c.in_circolo}</b> in circolo su <b>${c.emessi}</b> emessi,
      ${c.conti} cont${c.conti === 1 ? "o" : "i"}.
      ${c.conservati ? "Si conservano." : "<b>NON si conservano — il libro è rotto.</b>"}
      ${c.trasferibile ? "<b>Trasferimento fra persone ACCESO: fuori dal circuito chiuso.</b>" : ""}`;
  }
}

/* ---------- i numeri in alto ---------- */
function numeri() {
  testo($("#n-oggetti"), QUADRO.totale);
  testo($("#n-zone"), Object.keys(QUADRO.zone).length);
  const mancanti = (QUADRO.differenza &&
    (QUADRO.differenza.non_spiegati || QUADRO.differenza.mancanti) || []).length;
  testo($("#n-manca"), mancanti);
  $("#box-manca").classList.toggle("allarme", mancanti > 0);
  // «9.00» non dice niente, e un totale che somma euro e chiari dice una
  // cosa falsa. Il server tiene le valute separate: qui si mostra la prima
  // e si dichiara che ce n'è un'altra, invece di fonderle in un numero solo.
  const inc = QUADRO.incasso;
  const righe = inc ? Object.entries(inc.per_valuta || {}) : [];
  if (!righe.length) {
    testo($("#n-incasso"), "—");
    testo($("#box-incasso").querySelector("span"), "incasso");
  } else {
    const [valuta, c] = righe[0];
    testo($("#n-incasso"), c.al_proprietario.toFixed(2));
    testo($("#box-incasso").querySelector("span"),
      righe.length === 1 ? `incasso · ${valuta}`
                         : `incasso · ${valuta} + ${righe.length - 1} altra valuta`);
  }
  $("#box-incasso").classList.toggle("buono", righe.length > 0);
}

function disegna() {
  const f = $("#fascia");
  f.hidden = !QUADRO.stub;
  if (QUADRO.stub) f.textContent =
    "MODO STUB — nessun modello sta guardando. Ciò che vedi non è stato letto.";
  numeri(); pianta(); linea(); differenza(); registro(); mercato();
  testo($("#sottotitolo"),
    QUADRO.totale ? `${QUADRO.totale} oggetti · aggiornato ora` : "nessun oggetto nel registro");
  testo($("#stato-lettura"),
    QUADRO.stub ? "lettura: stub (nessun modello)" : "lettura: modello attivo");
}

document.addEventListener("keydown", (e) => { if (e.key === "Escape" && ZONA) filtra(null); });
carica().catch(e => { $("#sottotitolo").textContent = "non raggiungibile: " + e.message; });
