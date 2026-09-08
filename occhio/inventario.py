#!/usr/bin/env python3
"""occhio.inventario — il registro degli oggetti, append-only e deterministico.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Un inventario e' utile solo se sa dire **no**: se ripassando con la telecamera
sullo stesso scaffale il conteggio cresce, il numero non misura gli oggetti,
misura le passate. E' il difetto di CLAUDE.md §4 applicato a un armadio.

Percio' l'identita' di un oggetto qui non e' mai una impressione: e' una
funzione pura di cio' che si e' letto, e si puo' rieseguire su un registro
gia' scritto ottenendo lo stesso risultato.

Tre livelli di identita', in ordine di forza:

1. **chiave testuale** — `tipo:titolo` normalizzato. Vale quando il titolo e'
   stato letto davvero. E' la piu' forte perche' sopravvive a inquadratura,
   luce e distanza: lo stesso DVD ripreso da due metri o da venti centimetri
   da' la stessa chiave.
2. **impronta percettiva (dHash a 64 bit)** del ritaglio. Vale quando il
   titolo non e' leggibile ma l'oggetto e' visibilmente lo stesso. Distanza
   di Hamming <= SOGLIA_IMPRONTA -> stesso oggetto fisico.
3. **niente dei due** -> stato INCERTO. Non entra nel registro da solo.
   Il colore in sovrimpressione sara' ambra, non verde: il verde significa
   «e' scritto nel registro», e deve restare una promessa mantenuta.

Il file e' `output/inventario.jsonl`, una riga JSON per evento. Append-only
per la ragione di §6 regola 3: due passate non possono sovrascriversi.
Lo stato corrente si ricostruisce rileggendo il file, non si conserva a parte.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path

# Distanza di Hamming sotto la quale due impronte a 64 bit sono considerate
# lo stesso oggetto. 10/64 e' prudente: sotto questa soglia due dorsi di DVD
# diversi dello stesso cofanetto restano distinti (verificabile con
# `python -m occhio --prova-impronte`), sopra i 14 iniziano a fondersi.
SOGLIA_IMPRONTA = 10

ARCHIVIO = Path(os.environ.get("OCCHIO_INVENTARIO", "output/inventario.jsonl"))


def _etichetta(luogo) -> str:
    """Nome leggibile di un luogo dichiarato. Import tardivo: `inventario`
    deve restare utilizzabile anche senza il modulo dei luoghi."""
    if not luogo:
        return "(luogo non dichiarato)"
    try:
        from .luogo import etichetta
        return etichetta(luogo)
    except Exception:
        return str(luogo)

TIPI_NOTI = (
    "dvd", "blu-ray", "vhs", "cd", "vinile", "libro", "rivista",
    "scatola", "elettronica", "documento", "quadro", "altro",
)

# Articoli e rumore che l'OCR di un dorso porta con se': "THE MATRIX" e
# "MATRIX, THE" sono lo stesso disco, e devono dare la stessa chiave.
_ARTICOLI = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
             "the", "a", "an", "der", "die", "das", "le", "les", "el"}


# --------------------------------------------------------------------------
# normalizzazione e identita'
# --------------------------------------------------------------------------

def normalizza(testo: str) -> str:
    """Riduce un titolo alla sua forma confrontabile.

    Toglie accenti, punteggiatura, doppi spazi, maiuscole e articoli iniziali
    o finali. Non tocca i numeri: «Rocky 2» e «Rocky 3» devono restare diversi.
    """
    if not testo:
        return ""
    t = unicodedata.normalize("NFKD", str(testo))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    if not t:
        return ""
    parole = t.split()
    # articolo in testa, o in coda dopo virgola all'italiana/inglese
    while parole and parole[0] in _ARTICOLI:
        parole.pop(0)
    while parole and parole[-1] in _ARTICOLI:
        parole.pop()
    return " ".join(parole)


def chiave(tipo: str, titolo: str) -> str | None:
    """Chiave canonica di un oggetto, o None se il titolo non e' utilizzabile.

    Un titolo di una sola lettera o di sole cifre non identifica niente: e'
    meglio dichiarare l'assenza di chiave che fabbricarne una debole, perche'
    una chiave debole fonde due oggetti diversi e il registro perde una voce
    senza dirlo.
    """
    n = normalizza(titolo)
    if len(n.replace(" ", "")) < 3:
        return None
    t = normalizza(tipo) or "altro"
    return f"{t}:{n}"


def distanza_impronta(a: str, b: str) -> int:
    """Distanza di Hamming fra due impronte esadecimali a 64 bit.

    Restituisce 64 (massima distanza) se una delle due manca o e' malformata:
    nessuna impronta non deve mai somigliare a tutto.
    """
    if not a or not b:
        return 64
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


# --------------------------------------------------------------------------
# il registro
# --------------------------------------------------------------------------

class Inventario:
    """Vista in memoria di un file append-only. Si ricostruisce rileggendolo."""

    def __init__(self, percorso: Path | str = ARCHIVIO):
        self.percorso = Path(percorso)
        self.voci: list[dict] = []
        self._per_chiave: dict[str, dict] = {}
        self.foto_lette: set[str] = set()
        self.carica()

    # -- lettura ----------------------------------------------------------

    def carica(self) -> int:
        """Rilegge il file da zero. Righe illeggibili contate, non silenziate."""
        self.voci = []
        self._per_chiave = {}
        self.foto_lette: set[str] = set()
        self.righe_illeggibili = 0
        if not self.percorso.exists():
            return 0
        with open(self.percorso, "r", encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    voce = json.loads(riga)
                except json.JSONDecodeError:
                    self.righe_illeggibili += 1
                    continue
                self._assorbi(voce)
        return len(self.voci)

    def _assorbi(self, voce: dict) -> None:
        """Applica un evento allo stato corrente.

        Un evento `avvistamento` su una voce gia' presente non aggiunge una
        voce: incrementa il contatore. E' qui che il ripasso smette di gonfiare
        il totale.
        """
        k = voce.get("chiave")
        if k and k in self._per_chiave:
            esistente = self._per_chiave[k]
            esistente["avvistamenti"] = esistente.get("avvistamenti", 1) + 1
            esistente["visto_ultimo"] = voce.get("visto_ultimo", esistente.get("visto_ultimo"))
            if voce.get("impronta") and voce["impronta"] not in esistente.setdefault("impronte", []):
                esistente["impronte"].append(voce["impronta"])
            # Un oggetto puo' essere visto in piu' luoghi: e' un fatto, non un
            # conflitto — i libri si spostano. Si conservano tutti, in ordine.
            if voce.get("luogo"):
                luoghi = esistente.setdefault("luoghi", [])
                if voce["luogo"] not in luoghi:
                    luoghi.append(voce["luogo"])
            # Titoli originali distinti che sono finiti sulla stessa chiave.
            # «The Matrix» e «MATRIX, THE» devono fondersi — e' il motivo per
            # cui l'articolo si toglie. Ma allora si fondono anche «Heat»
            # (1995) e «The Heat» (2013), che sono due film. Non si puo'
            # avere l'una cosa senza l'altra con la sola normalizzazione,
            # quindi la fusione non si nasconde: si registra e si mostra.
            titolo = str(voce.get("titolo", "")).strip()
            if titolo:
                visti = esistente.setdefault("titoli_visti", [])
                if titolo not in visti:
                    visti.append(titolo)
            return
        # ANCORA — una persona dichiara qual e' il titolo definitivo di un
        # oggetto e quali descrizioni sono la stessa cosa. Serve agli oggetti
        # SENZA titolo scritto sopra: un quadro, un orologio, un candelabro.
        # Li' il titolo lo inventa chi legge, e due letture lo inventano
        # diverso — un oggetto fantasma che a fine soggiorno risulta mancante.
        # Verificato il 07/09 su una fotografia vera: 18 oggetti diventavano
        # 19 riscrivendo «orologio da mensola» come «orologio da tavolo».
        if voce.get("evento") == "ancora":
            bersaglio = self._per_chiave.get(voce.get("ancora_a"))
            if bersaglio is not None:
                if voce.get("titolo"):
                    bersaglio["titolo"] = voce["titolo"]
                bersaglio["confermato"] = True
                bersaglio["fonte"] = "umano"
                for a in voce.get("alias", []):
                    if a and a not in bersaglio.setdefault("alias", []):
                        bersaglio["alias"].append(a)
                self._indicizza(bersaglio)
            return
        # DECISIONE su un «da decidere»: la stessa cosa (l'alias va
        # sull'ancora e la voce doppia sparisce dalla vista) o due cose
        # diverse (la voce resta, e non lo chiede piu').
        if voce.get("evento") in ("uguale", "diversa"):
            doppia = self._per_chiave.get(voce.get("su"))
            if doppia is None:
                return
            if voce["evento"] == "diversa":
                doppia["deciso"] = True
                return
            ancora = self._per_chiave.get(voce.get("ancora_a")) or \
                self._per_chiave.get(doppia.get("simile_a"))
            if ancora is None or ancora is doppia:
                return
            for t in doppia.get("titoli_visti", []) or [doppia.get("titolo")]:
                if t and t not in ancora.setdefault("alias", []):
                    ancora["alias"].append(t)
            for l in doppia.get("luoghi", []):
                if l not in ancora.setdefault("luoghi", []):
                    ancora["luoghi"].append(l)
            ancora["avvistamenti"] = ancora.get("avvistamenti", 1) + \
                doppia.get("avvistamenti", 1)
            self.voci = [v for v in self.voci if v is not doppia]
            self._per_chiave = {k: v for k, v in self._per_chiave.items()
                                if v is not doppia}
            self._indicizza(ancora)
            return
        if voce.get("foto_sha"):
            self.foto_lette.add(voce["foto_sha"])
        voce.setdefault("avvistamenti", 1)
        voce.setdefault("impronte", [voce["impronta"]] if voce.get("impronta") else [])
        voce.setdefault("luoghi", [voce["luogo"]] if voce.get("luogo") else [])
        voce.setdefault("titoli_visti",
                        [voce["titolo"]] if voce.get("titolo") else [])
        self.voci.append(voce)
        self._indicizza(voce)

    def _indicizza(self, voce: dict) -> None:
        """La voce sotto la sua chiave e sotto quelle dei suoi alias.

        E' cosi' che una descrizione diversa dello stesso oggetto ci
        ricasca sopra invece di diventare una voce nuova.
        """
        if voce.get("chiave"):
            self._per_chiave[voce["chiave"]] = voce
        for a in voce.get("alias", []):
            ka = chiave(voce.get("tipo", ""), a)
            if ka:
                self._per_chiave.setdefault(ka, voce)

    # -- riconoscimento ---------------------------------------------------

    def riconosci(self, tipo: str, titolo: str, impronta: str | None = None,
                  luogo: dict | None = None) -> tuple[str, dict | None]:
        """Dice se un oggetto letto adesso e' gia' nel registro.

        Ritorna `(stato, voce)` dove stato e':
          - `CATALOGATO`  la chiave testuale coincide  -> verde
          - `RIVISTO`     l'impronta coincide, il titolo no -> verde chiaro
          - `NUOVO`       ha una chiave e non e' nel registro -> da scrivere
          - `INCERTO`     nessuna chiave utilizzabile, **oppure** un oggetto
                          ancorato dello stesso tipo sta gia' in quella zona
                          -> ambra, mai automatico

        Nessuno di questi stati dipende da cosa e' successo nella sessione
        corrente: dipende solo dal contenuto del file. Riavviando il server
        gli stessi oggetti danno gli stessi stati — questa e' la differenza
        fra un registro e una impressione.
        """
        k = chiave(tipo, titolo)
        if k and k in self._per_chiave:
            return "CATALOGATO", self._per_chiave[k]
        if impronta:
            for voce in self.voci:
                for imp in voce.get("impronte", []):
                    if distanza_impronta(impronta, imp) <= SOGLIA_IMPRONTA:
                        return ("CATALOGATO" if k and voce.get("chiave") == k else "RIVISTO"), voce
        # RETE DI SICUREZZA (05-08/09). Un oggetto ancorato da una persona
        # dello stesso tipo, nella stessa zona, e' quasi sempre lo stesso
        # oggetto descritto in un altro modo. «Quasi» non basta per fondere
        # da solo: si dichiara INCERTO e decide qualcuno. Non fondere in
        # silenzio e non separare in silenzio sono la stessa regola.
        vicino = self._ancorato_nella_zona(tipo, luogo)
        if vicino is not None:
            return "INCERTO", vicino
        if k:
            return "NUOVO", None
        return "INCERTO", None

    @staticmethod
    def _zona(luogo) -> str | None:
        if not luogo:
            return None
        return (_etichetta(luogo).split(" › ") or [None])[0] or None

    def _ancorato_nella_zona(self, tipo: str, luogo) -> dict | None:
        zona = self._zona(luogo)
        if not zona:
            return None
        t = normalizza(tipo) or "altro"
        for voce in self.voci:
            if not voce.get("confermato") or (voce.get("tipo") or "altro") != t:
                continue
            if any(self._zona(l) == zona for l in (voce.get("luoghi") or [])):
                return voce
        return None

    # -- scrittura --------------------------------------------------------

    def registra(self, tipo: str, titolo: str, impronta: str | None = None,
                 testo_letto: str = "", confidenza: float | None = None,
                 fonte: str = "telecamera", note: str = "",
                 luogo: dict | None = None, foto_sha: str | None = None) -> dict:
        """Scrive un evento in coda al file e aggiorna la vista.

        Un oggetto senza chiave utilizzabile non viene scritto: solleva
        ValueError. Serve perche' il chiamante sia costretto a decidere —
        chiedere all'umano o lasciar perdere — invece di depositare una voce
        che nessuno potra' piu' ritrovare.
        """
        k = chiave(tipo, titolo)
        if not k:
            raise ValueError(
                f"titolo non identificante: {titolo!r}. "
                "Serve una conferma umana (--conferma) o una lettura migliore."
            )
        stato, esistente = self.riconosci(tipo, titolo, impronta, luogo)
        ora = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        voce = {
            "chiave": k,
            "tipo": normalizza(tipo) or "altro",
            "titolo": str(titolo).strip(),
            "testo_letto": str(testo_letto or "").strip()[:500],
            "impronta": impronta,
            "confidenza": confidenza,
            "fonte": fonte,
            "note": note,
            "visto_primo": ora if stato == "NUOVO" else (esistente or {}).get("visto_primo", ora),
            "visto_ultimo": ora,
            "evento": "nuovo" if stato == "NUOVO" else "avvistamento",
            # Somiglia a un oggetto che una persona ha gia' ancorato qui:
            # si scrive lo stesso — non si perde mai un dato — ma resta
            # marchiato finche' qualcuno non dice se sono la stessa cosa.
            "simile_a": (esistente or {}).get("chiave") if stato == "INCERTO" else None,
            # Il luogo e' DICHIARATO, mai dedotto da una coordinata: dentro
            # casa il GPS ha un errore piu' grande della casa (H7). Vedi
            # occhio/luogo.py e falsificatori/h7_gps_stanze.py.
            "luogo": luogo or None,
            # L'impronta della fotografia da cui viene: ripassare la stessa
            # cartella non ripaga la stessa lettura al fornitore.
            "foto_sha": foto_sha,
        }
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(voce, ensure_ascii=False) + "\n")
        self._assorbi(dict(voce))
        voce["stato"] = stato
        return voce

    # -- resoconto --------------------------------------------------------

    def per_luogo(self) -> dict[str, list]:
        """L'inventario riorganizzato per dove stanno le cose. E' la mappa."""
        mappa: dict[str, list] = {}
        for v in self.voci:
            for l in (v.get("luoghi") or [None]):
                mappa.setdefault(_etichetta(l), []).append(v)
        return dict(sorted(mappa.items()))

    def fusioni(self) -> list[dict]:
        """Voci su cui sono finiti titoli originali diversi.

        E' il posto in cui guardare quando un conteggio sembra basso: se
        «Heat» e «The Heat» sono diventati una voce sola, qui si vede, e
        `--conferma` permette di separarli dando a uno un titolo distinto.
        Una fusione visibile e' un problema; una fusione silenziosa e' un
        registro che mente.
        """
        return [v for v in self.voci if len(v.get("titoli_visti", [])) > 1]

    #: Le debolezze che una voce puo' avere. Ognuna dice cosa manca e cosa
    #: si fa per toglierla: un difetto senza rimedio e' un rimprovero.
    DEBOLEZZE = (
        ("senza_luogo", "non si sa dove sta",
         "fotografa per cartelle: una cartella per stanza o per mobile"),
        ("vista_una_volta", "letta una volta sola, mai riconfermata",
         "ripassa: la seconda lettura conferma o smentisce la prima"),
        ("confidenza_bassa", "il modello stesso non era sicuro",
         "riavvicinati e rifotografa, o conferma a mano con --conferma"),
        ("titolo_debole", "il titolo e' troppo corto per ritrovarla",
         "correggila a mano: un titolo che non distingue non serve a niente"),
        ("fusa", "titoli diversi finiti sulla stessa voce",
         "dai a uno un titolo che lo distingua"),
        ("senza_foto", "nessuna fotografia la sostiene",
         "rifotografala: senza impronta non c'e' niente da mostrare a nessuno"),
        ("da_decidere", "somiglia a un oggetto gia' ancorato nella stessa zona",
         "python -m occhio --uguale CHIAVE ALTRA-CHIAVE, oppure --diversa CHIAVE"),
    )

    def debolezze(self, voce: dict, soglia_confidenza: float = 0.7) -> list[str]:
        """Le debolezze di UNA voce. Sono fatti sul dato, non giudizi."""
        d = []
        if not (voce.get("luoghi") or voce.get("luogo")):
            d.append("senza_luogo")
        if voce.get("avvistamenti", 1) < 2:
            d.append("vista_una_volta")
        c = voce.get("confidenza")
        if isinstance(c, (int, float)) and c < soglia_confidenza:
            d.append("confidenza_bassa")
        if len(normalizza(voce.get("titolo", "")).replace(" ", "")) < 6:
            d.append("titolo_debole")
        if len(voce.get("titoli_visti", [])) > 1:
            d.append("fusa")
        if not voce.get("foto_sha"):
            d.append("senza_foto")
        if voce.get("simile_a") and not voce.get("deciso"):
            d.append("da_decidere")
        return d

    def qualita(self, soglia_confidenza: float = 0.7) -> dict:
        """Quanto e' affidabile CIO' CHE E' SCRITTO qui dentro.

        **Non** quanto somiglia alla casa: quello lo dice solo qualcuno che
        conta a mano, ed e' il numero che manca a tutto il progetto. Questa
        misura guarda il registro e basta, quindi puo' migliorare senza che
        nulla sia entrato dall'esterno — e' il difetto di CLAUDE.md §4, qui
        dichiarato invece che nascosto. Serve a sapere di quali righe ci si
        puo' fidare, non a dire che il sistema va bene.
        """
        conteggio = {nome: 0 for nome, _, _ in self.DEBOLEZZE}
        esempi: dict[str, list[str]] = {nome: [] for nome, _, _ in self.DEBOLEZZE}
        solide = 0
        for v in self.voci:
            d = self.debolezze(v, soglia_confidenza)
            if not d:
                solide += 1
            for nome in d:
                conteggio[nome] += 1
                if len(esempi[nome]) < 3:
                    esempi[nome].append(v.get("titolo", ""))
        totale = len(self.voci)
        return {
            "totale": totale,
            "solide": solide,
            "righe_illeggibili": self.righe_illeggibili,
            "confermate_a_mano": sum(1 for v in self.voci if v.get("fonte") == "umano"),
            "debolezze": [
                {"nome": nome, "cosa": cosa, "azione": azione,
                 "voci": conteggio[nome],
                 "quota": round(conteggio[nome] / totale, 3) if totale else 0.0,
                 "esempi": esempi[nome]}
                for nome, cosa, azione in self.DEBOLEZZE
            ],
        }

    # -- le decisioni di una persona --------------------------------------

    def _evento(self, voce: dict) -> dict:
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(voce, ensure_ascii=False) + "\n")
        self._assorbi(dict(voce))
        return voce

    def ancora(self, chiave_voce: str, titolo: str = "") -> dict:
        """Una persona dichiara il titolo definitivo di un oggetto.

        Da qui in poi quella voce e' un'ancora: le descrizioni che le
        finiscono sopra diventano alias invece di oggetti nuovi.
        """
        voce = self._per_chiave.get(chiave_voce)
        if voce is None:
            raise KeyError(f"nessuna voce con chiave {chiave_voce!r}")
        alias = [t for t in voce.get("titoli_visti", []) if t != titolo]
        if voce.get("titolo") and voce["titolo"] != titolo:
            alias.append(voce["titolo"])
        return self._evento({
            "evento": "ancora", "ancora_a": chiave_voce,
            "titolo": (titolo or voce.get("titolo", "")).strip(),
            "alias": sorted(set(a for a in alias if a)),
            "fonte": "umano",
            "visto_ultimo": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def uguale(self, chiave_doppia: str, chiave_ancora: str = "") -> dict:
        """«Sono la stessa cosa»: la doppia diventa un alias dell'ancora."""
        doppia = self._per_chiave.get(chiave_doppia)
        if doppia is None:
            raise KeyError(f"nessuna voce con chiave {chiave_doppia!r}")
        bersaglio = chiave_ancora or doppia.get("simile_a")
        if not bersaglio:
            raise ValueError("non so a quale oggetto unirla: indica la chiave")
        return self._evento({
            "evento": "uguale", "su": chiave_doppia, "ancora_a": bersaglio,
            "fonte": "umano",
            "visto_ultimo": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def diversa(self, chiave_voce: str) -> dict:
        """«Sono due cose diverse»: la voce resta e non lo chiede piu'."""
        if chiave_voce not in self._per_chiave:
            raise KeyError(f"nessuna voce con chiave {chiave_voce!r}")
        return self._evento({
            "evento": "diversa", "su": chiave_voce, "fonte": "umano",
            "visto_ultimo": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def da_ancorare(self) -> list[dict]:
        """Le voci che meritano un titolo deciso da una persona.

        Non tutte: quelle senza un titolo stabile per natura — nessuna
        scritta sopra da leggere — riconosciute dal fatto che il modello non
        era sicuro o che la voce non e' ancora ancorata e ha gia' preso piu'
        di un titolo.
        """
        fuori = []
        for v in self.voci:
            if v.get("confermato"):
                continue
            c = v.get("confidenza")
            incerta = isinstance(c, (int, float)) and c < 0.7
            if incerta or len(v.get("titoli_visti", [])) > 1 or v.get("simile_a"):
                fuori.append(v)
        return fuori

    def per_tipo(self) -> dict[str, int]:
        conteggio: dict[str, int] = {}
        for v in self.voci:
            conteggio[v.get("tipo", "altro")] = conteggio.get(v.get("tipo", "altro"), 0) + 1
        return dict(sorted(conteggio.items(), key=lambda kv: -kv[1]))

    def csv(self) -> str:
        import csv as _csv
        import io
        buf = io.StringIO()
        w = _csv.writer(buf)
        w.writerow(["tipo", "titolo", "luogo", "avvistamenti", "visto_primo",
                    "visto_ultimo", "confidenza", "testo_letto"])
        for v in sorted(self.voci, key=lambda x: (x.get("tipo", ""), x.get("titolo", ""))):
            luoghi = v.get("luoghi") or []
            w.writerow([v.get("tipo", ""), v.get("titolo", ""),
                        " | ".join(_etichetta(x) for x in luoghi),
                        v.get("avvistamenti", 1),
                        v.get("visto_primo", ""), v.get("visto_ultimo", ""),
                        v.get("confidenza", ""), v.get("testo_letto", "")])
        return buf.getvalue()
