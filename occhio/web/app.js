/* occhio — interfaccia. Origine protetta: Claudio Terzi [CT-LGAI-001].
 *
 * Tre cose accadono qui, e vale la pena tenerle distinte:
 *
 * 1. CATTURA. Ogni `ritmo` millisecondi un fotogramma viene disegnato su un
 *    canvas fuori schermo, ridotto a 1024 px di lato lungo e mandato al server
 *    come JPEG. Il fotogramma non viene mai salvato, ne' qui ne' li'.
 * 2. IMPRONTA. Quando i riquadri tornano, per ognuno si calcola un dHash a
 *    64 bit sul ritaglio del fotogramma ancora in memoria. Al giro dopo le
 *    impronte partono insieme all'immagine: e' cosi' che un oggetto dal titolo
 *    illeggibile viene riconosciuto come "gia' visto" invece di essere
 *    richiesto in conferma a ogni fotogramma.
 * 3. DISEGNO. Il colore non e' deciso qui. Arriva dal server, che lo ricava dal
 *    file su disco. Verde significa "c'e' una riga scritta": se lo decidesse
 *    il browser, sarebbe l'interfaccia che si conferma da sola.
 */

const $ = (s) => document.querySelector(s);

const video = $("#video");
const tela = $("#sovrimpressione");
const ctx = tela.getContext("2d");

// canvas fuori schermo: quello che viene spedito e quello su cui si misura
const cattura = document.createElement("canvas");
const cctx = cattura.getContext("2d", { willReadFrequently: true });
const mini = document.createElement("canvas");
mini.width = 9; mini.height = 8;
const mctx = mini.getContext("2d", { willReadFrequently: true });

const COLORI = {
  CATALOGATO: "#2ee06a",
  RIVISTO:    "#2ee06a",
  NUOVO:      "#35d6f0",
  INCERTO:    "#ffb020",
};

let flusso = null, timer = null, inFase = false;
let riquadri = [];            // ultimi oggetti disegnati
let impronteRecenti = [];     // [{riquadro, impronta}] per il giro successivo
let nuoviInPassata = 0;
let fotocameraPosteriore = true;
let incertiMostrati = new Set();

/* ------------------------------------------------------------------ *
 * dHash a 64 bit — la stessa idea di analisi_foto.dhash, in JavaScript.
 * Confronta ogni pixel con quello alla sua destra su una griglia 9x8 in
 * scala di grigi: sopravvive a luce, compressione e piccoli spostamenti,
 * cambia se cambia l'oggetto.
 * ------------------------------------------------------------------ */
function impronta(sorgente, x, y, w, h) {
  if (w < 4 || h < 4) return null;
  mctx.drawImage(sorgente, x, y, w, h, 0, 0, 9, 8);
  const px = mctx.getImageData(0, 0, 9, 8).data;
  const g = (i) => 0.299 * px[i * 4] + 0.587 * px[i * 4 + 1] + 0.114 * px[i * 4 + 2];
  let bit = "";
  for (let r = 0; r < 8; r++)
    for (let c = 0; c < 8; c++)
      bit += g(r * 9 + c) > g(r * 9 + c + 1) ? "1" : "0";
  let hex = "";
  for (let i = 0; i < 64; i += 4) hex += parseInt(bit.slice(i, i + 4), 2).toString(16);
  return hex;
}

/* ------------------------------------------------------------------ *
 * telecamera
 * ------------------------------------------------------------------ */
async function accendi() {
  if (!navigator.mediaDevices?.getUserMedia) {
    return messaggio("errore", "Questo browser non espone la telecamera. "
      + "Serve https oppure localhost.");
  }
  try {
    flusso = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: fotocameraPosteriore ? "environment" : "user",
               width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
  } catch (e) {
    $("#spento").hidden = false;
    return messaggio("errore", "Permesso negato o telecamera occupata: " + e.message);
  }
  video.srcObject = flusso;
  await video.play();
  $("#spento").hidden = true;
  $("#spegni").hidden = $("#cambia").hidden = $("#lab-ritmo").hidden = false;
  nuoviInPassata = 0;
  dimensiona();
  ciclo();
  disegna();
}

function spegni() {
  clearTimeout(timer); timer = null;
  flusso?.getTracks().forEach((t) => t.stop());
  flusso = null;
  riquadri = []; impronteRecenti = [];
  $("#spento").hidden = false;
  $("#spegni").hidden = $("#cambia").hidden = $("#lab-ritmo").hidden = true;
  ctx.clearRect(0, 0, tela.width, tela.height);
}

function dimensiona() {
  const r = tela.getBoundingClientRect();
  const d = window.devicePixelRatio || 1;
  tela.width = r.width * d; tela.height = r.height * d;
  ctx.setTransform(d, 0, 0, d, 0, 0);
}
window.addEventListener("resize", dimensiona);

/* ------------------------------------------------------------------ *
 * il ciclo: cattura -> server -> impronte -> disegno
 * ------------------------------------------------------------------ */
function ciclo() {
  const ritmo = +$("#ritmo").value;
  timer = setTimeout(async () => {
    if (flusso) { await passata(); ciclo(); }
  }, ritmo);
}

async function passata() {
  if (inFase || !video.videoWidth) return;
  inFase = true;
  const t0 = performance.now();
  try {
    const lato = 1024;
    const s = Math.min(1, lato / Math.max(video.videoWidth, video.videoHeight));
    cattura.width = Math.round(video.videoWidth * s);
    cattura.height = Math.round(video.videoHeight * s);
    cctx.drawImage(video, 0, 0, cattura.width, cattura.height);
    const dataURL = cattura.toDataURL("image/jpeg", 0.72);

    const r = await fetch("/api/fotogramma", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ immagine: dataURL, impronte: impronteRecenti }),
    });
    const d = await r.json();
    if (!r.ok) { pillola("#p-provider", d.errore ? "errore" : "—"); throw new Error(d.errore || r.status); }

    $("#fascia-stub").hidden = !d.stub;
    pillola("#p-provider", d.provider + (d.stub ? " (finto)" : ""));
    pillola("#p-totale", d.totale_inventario + " oggetti");
    pillola("#p-ritmo", Math.round(performance.now() - t0) + " ms");

    // impronte per il giro successivo, misurate sul fotogramma appena spedito
    impronteRecenti = [];
    for (const o of d.oggetti) {
      const [x, y, w, h] = o.riquadro;
      const imp = impronta(cattura, x * cattura.width, y * cattura.height,
                           w * cattura.width, h * cattura.height);
      if (imp) impronteRecenti.push({ riquadro: o.riquadro, impronta: imp });
      o._impronta = imp;
      if (o.scritto_ora) nuoviInPassata++;
    }
    pillola("#p-nuovi", nuoviInPassata + " nuovi in questa passata");
    riquadri = d.oggetti;
    if (d.oggetti.some((o) => o.scritto_ora)) aggiornaInventario();
    mostraIncerti(d.oggetti);
  } catch (e) {
    console.warn("passata fallita:", e.message);
  } finally {
    inFase = false;
  }
}

/* ------------------------------------------------------------------ *
 * disegno
 * ------------------------------------------------------------------ */
function disegna() {
  if (!flusso) return;
  requestAnimationFrame(disegna);
  const W = tela.clientWidth, H = tela.clientHeight;
  ctx.clearRect(0, 0, W, H);
  if (!video.videoWidth) return;

  // il video e' in object-fit:cover: i riquadri vanno mappati sulla parte
  // realmente visibile, altrimenti scivolano rispetto agli oggetti.
  const sc = Math.max(W / video.videoWidth, H / video.videoHeight);
  const vw = video.videoWidth * sc, vh = video.videoHeight * sc;
  const ox = (W - vw) / 2, oy = (H - vh) / 2;

  const pulsa = 0.55 + 0.45 * Math.sin(performance.now() / 380);

  for (const o of riquadri) {
    const col = COLORI[o.stato] || "#8b96ab";
    const x = ox + o.riquadro[0] * vw, y = oy + o.riquadro[1] * vh;
    const w = o.riquadro[2] * vw, h = o.riquadro[3] * vh;
    if (w < 2 || h < 2) continue;

    ctx.save();
    ctx.strokeStyle = col;
    ctx.lineWidth = o.stato === "INCERTO" ? 2 : 3;
    ctx.globalAlpha = o.stato === "INCERTO" ? pulsa : 1;
    if (o.stato === "INCERTO") ctx.setLineDash([7, 5]);
    arrotondato(x, y, w, h, 8); ctx.stroke();

    // velo verde su cio' che e' gia' scritto nel registro: e' il segnale che
    // permette di ripassare sullo stesso scaffale senza rileggerlo.
    if (o.stato === "CATALOGATO" || o.stato === "RIVISTO") {
      ctx.globalAlpha = 0.16; ctx.fillStyle = col;
      arrotondato(x, y, w, h, 8); ctx.fill(); ctx.globalAlpha = 1;
      spunta(x + w - 13, y + 13, col);
    }
    ctx.restore();

    etichetta(x, y, w, o, col);
  }
}

function arrotondato(x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
}

function spunta(cx, cy, col) {
  ctx.save();
  ctx.fillStyle = col; ctx.beginPath(); ctx.arc(cx, cy, 9, 0, 7); ctx.fill();
  ctx.strokeStyle = "#04150a"; ctx.lineWidth = 2.2; ctx.lineCap = "round";
  ctx.beginPath(); ctx.moveTo(cx - 4, cy); ctx.lineTo(cx - 1, cy + 3.4);
  ctx.lineTo(cx + 4.4, cy - 3.4); ctx.stroke();
  ctx.restore();
}

function etichetta(x, y, w, o, col) {
  const testo = (o.titolo || o.testo_letto || "?").slice(0, 34)
    + (o.stato === "CATALOGATO" && o.avvistamenti > 1 ? `  ·${o.avvistamenti}x` : "");
  ctx.save();
  ctx.font = "600 12.5px -apple-system, Segoe UI, Roboto, sans-serif";
  const lw = ctx.measureText(testo).width + 16;
  const ly = y > 24 ? y - 22 : y + 4;
  ctx.fillStyle = col;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, ly, Math.min(lw, Math.max(w, lw)), 19, 6);
  else ctx.rect(x, ly, lw, 19);
  ctx.fill();
  ctx.fillStyle = "#06090d";
  ctx.fillText(testo, x + 8, ly + 13.6);
  ctx.restore();
}

/* ------------------------------------------------------------------ *
 * pannello
 * ------------------------------------------------------------------ */
const pillola = (sel, testo) => { $(sel).textContent = testo; };

async function aggiornaInventario() {
  const d = await (await fetch("/api/inventario")).json();
  const ul = $("#elenco");
  ul.innerHTML = "";
  $("#vuoto").hidden = d.totale > 0;
  $("#conta").textContent = d.totale;
  for (const v of d.oggetti) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="tipo"></span><span class="titolo"></span><span class="volte"></span>`;
    li.querySelector(".tipo").textContent = v.tipo || "altro";
    li.querySelector(".titolo").textContent = v.titolo || "";
    li.querySelector(".volte").textContent = (v.avvistamenti || 1) > 1 ? v.avvistamenti + "x" : "";
    if (v.fonte === "umano") li.querySelector(".volte").textContent += " ✎";
    ul.appendChild(li);
  }
  if (ul.firstChild) ul.firstChild.classList.add("appena");
}

/* Gli incerti sono il punto in cui il sistema ammette di non sapere e chiede.
 * Averli sotto gli occhi mentre si cammina e' cio' che tiene la soglia alta:
 * senza questo riquadro la tentazione sarebbe abbassarla, e l'inventario si
 * riempirebbe di titoli plausibili che nessuno ha letto. */
function mostraIncerti(oggetti) {
  const box = $("#incerti");
  for (const o of oggetti) {
    if (o.stato !== "INCERTO") continue;
    const id = (o.testo_letto || o.titolo || "").toLowerCase().slice(0, 40);
    if (!id || incertiMostrati.has(id)) continue;
    incertiMostrati.add(id);

    const div = document.createElement("div");
    div.className = "incerto";
    div.innerHTML = `<div class="minuto">non sono sicuro di aver letto</div>
      <div class="letto"></div>
      <input placeholder="titolo esatto">
      <div class="riga"><button class="ok">conferma</button>
        <button class="no">lascia perdere</button></div>`;
    div.querySelector(".letto").textContent = o.testo_letto || o.titolo || "(illeggibile)";
    const campo = div.querySelector("input");
    campo.value = o.titolo || "";
    div.querySelector(".no").onclick = () => div.remove();
    div.querySelector(".ok").onclick = async () => {
      const titolo = campo.value.trim();
      if (!titolo) return campo.focus();
      const r = await fetch("/api/conferma", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo: o.tipo, titolo, testo_letto: o.testo_letto,
                               impronta: o._impronta, confidenza: o.confidenza }),
      });
      const d = await r.json();
      if (!r.ok) { div.querySelector(".letto").textContent = d.errore; return; }
      div.remove(); aggiornaInventario();
    };
    box.appendChild(div);
  }
}

/* ------------------------------------------------------------------ *
 * conversazione
 * ------------------------------------------------------------------ */
function messaggio(classe, testo) {
  const d = document.createElement("div");
  d.className = "msg " + classe; d.textContent = testo;
  $("#messaggi").appendChild(d);
  $("#messaggi").scrollTop = 1e9;
  return d;
}

$("#modulo-chat").addEventListener("submit", async (e) => {
  e.preventDefault();
  const campo = $("#campo-chat");
  const testo = campo.value.trim();
  if (!testo) return;
  campo.value = "";
  messaggio("io", testo);
  const attesa = messaggio("lui", "…");
  try {
    const r = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messaggio: testo }),
    });
    const d = await r.json();
    attesa.textContent = r.ok ? d.risposta : "non ho potuto rispondere: " + d.errore;
    if (!r.ok) attesa.className = "msg errore";
    else if (d.stub) attesa.textContent += "\n\n[risposta dello stub: nessun modello ha pensato]";
  } catch (err) {
    attesa.textContent = "rete non raggiungibile: " + err.message;
    attesa.className = "msg errore";
  }
});

/* ------------------------------------------------------------------ */
$("#accendi").onclick = accendi;
$("#spegni").onclick = spegni;
$("#cambia").onclick = () => { fotocameraPosteriore = !fotocameraPosteriore; spegni(); accendi(); };
$("#ritmo").oninput = (e) => {
  $("#ritmo-val").textContent = (e.target.value / 1000).toFixed(1).replace(".", ",") + " s";
};
document.querySelectorAll(".scheda").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll(".scheda").forEach((x) => x.classList.remove("attiva"));
    document.querySelectorAll(".vista").forEach((x) => x.classList.remove("attiva"));
    b.classList.add("attiva");
    $("#vista-" + b.dataset.vista).classList.add("attiva");
  };
});

// getUserMedia esiste solo in contesto sicuro: dirlo prima, non dopo il rifiuto.
if (!window.isSecureContext) $("#avviso-https").hidden = false;

fetch("/api/stato").then((r) => r.json()).then((d) => {
  $("#fascia-stub").hidden = !d.stub;
  $("#file-inv").textContent = d.inventario.file;
  pillola("#p-totale", d.inventario.oggetti + " oggetti");
  aggiornaInventario();
}).catch(() => {});


/* ------------------------------------------------------------------ *
 * LA VOCE — idea di Claudio Terzi, 3 settembre 2026.
 *
 * Riconoscimento e sintesi stanno nel browser: non costano niente e non
 * mandano audio da nessuna parte. Ciò che parte è solo la frase scritta.
 *
 * La regola che non si tocca: da qui non si scrive MAI nel registro.
 * A una voce non si può chiedere chi sta parlando, e in un alloggio in
 * affitto la stanza è piena di gente che non è il proprietario.
 * ------------------------------------------------------------------ */
const Ascolto = window.SpeechRecognition || window.webkitSpeechRecognition;
let ascoltatore = null;

function parla(testo) {
  if (!window.speechSynthesis) return;
  const v = new SpeechSynthesisUtterance(testo);
  v.lang = "it-IT"; v.rate = 1.03;
  speechSynthesis.cancel();
  speechSynthesis.speak(v);
}

async function chiediAllaCasa(frase, adAltaVoce) {
  messaggio("io", frase);
  const attesa = messaggio("lui voce", "…");
  try {
    const r = await fetch("/api/voce", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frase }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.errore || r.status);
    attesa.textContent = d.risposta;
    if (adAltaVoce) parla(d.risposta);
  } catch (e) {
    attesa.textContent = "non ho potuto rispondere: " + e.message;
    attesa.className = "msg errore";
  }
}

$("#microfono").onclick = () => {
  if (!Ascolto) {
    return messaggio("errore", "Questo browser non ascolta. Scrivi la domanda: "
      + "funziona uguale.");
  }
  if (ascoltatore) { ascoltatore.stop(); return; }
  ascoltatore = new Ascolto();
  ascoltatore.lang = "it-IT";
  ascoltatore.interimResults = false;
  ascoltatore.maxAlternatives = 1;
  $("#microfono").classList.add("ascolta");
  ascoltatore.onresult = (e) => chiediAllaCasa(e.results[0][0].transcript, true);
  ascoltatore.onerror = (e) => messaggio("errore", "microfono: " + e.error);
  ascoltatore.onend = () => {
    $("#microfono").classList.remove("ascolta");
    ascoltatore = null;
  };
  ascoltatore.start();
};

/* Scrivere la domanda invece di dirla non fa perdere niente: il modulo di
 * chat resta attivo e passa da /api/chat, che legge lo stesso inventario.
 * Chi è in una casa con altra gente, o senza microfono, ha la stessa
 * funzione — ed è il motivo per cui la voce non è mai l'unica strada. */
