#!/usr/bin/env python3
"""occhio.portavia — quello che ti piace, portalo via. Comprandolo.

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea di PORTAVIA e del Mediatore: Claudio Terzi, 3 settembre 2026.

L'intuizione, che e' sua e va attribuita a lui: **chi porta via un oggetto da
una casa in affitto quasi sempre lo fa perche' gli piace.** La difesa
tradizionale — cauzione, controllo, diffida — combatte il desiderio. PORTAVIA
lo asseconda e lo fa pagare: chi vuole quel film, quella bottiglia, quella
lampada, la compra. Cosi' **cio' che manca non e' stato rubato: e' stato
venduto**, e la differenza di fine soggiorno lo dice con parole diverse.

E' l'inversione che rende sano tutto il resto del prodotto. Fino a ieri
l'inventario era uno strumento di controllo, e un ospite non ha nessun motivo
di controfirmare un controllo. Un catalogo si', perche' gli serve.

---

**La regola che tiene in piedi il Mediatore: il modello parla, le regole
decidono.**

Un modello linguistico lasciato a trattare da solo, prima o poi, vende il
televisore per dieci euro — non perche' sia stupido, ma perche' e' fatto per
essere d'accordo con chi ha davanti, e chi ha davanti vuole pagare meno.
Percio' qui la trattativa e' **deterministica**: il prezzo minimo, lo sconto
massimo e gli oggetti intoccabili sono controllati in codice, prima che il
modello apra bocca. Al modello resta il compito che sa fare — scrivere una
frase gentile — e nessun potere di firmare.

E' la stessa forma dell'anti-eco di §4: cio' che decide non puo' essere la
parte del sistema che parla.

---

**Il confine con le prove, che non va mai attraversato.** Le immagini
generate o ritoccate dall'IA sono escluse dalle prove nei reclami danni
(OCCHIO.md §5-ter). La VETRINA — la presentazione bella di un oggetto — puo'
essere generata; la fotografia che dimostra che quell'oggetto c'era **no, mai**.
Sono due binari, e in questo modulo non si toccano: un'immagine generata non
puo' diventare `foto_sha` di nulla, e c'e' un test che fallisce se qualcuno
prova a farlo passare.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

CATALOGO = Path(os.environ.get("OCCHIO_PORTAVIA", "output/portavia.jsonl"))

# Stato commerciale di un oggetto. Il default e' il piu' protettivo: nulla e'
# in vendita finche' il proprietario non lo dice.
FUORI, IN_VENDITA, TRATTATIVA, VENDUTO = "fuori", "in_vendita", "trattativa", "venduto"

#: Motivi per cui un oggetto non puo' essere venduto, qualunque cosa dicano le
#: regole. Sono qui e non in una configurazione perche' un errore di
#: configurazione non deve poter mettere in vendita la caldaia.
MAI_IN_VENDITA = ("caldaia", "boiler", "condizionatore", "cucina a gas",
                  "porta", "finestra", "estintore", "rilevatore")

# --------------------------------------------------------------------------
# I TRE GENERI — idea di Claudio Terzi, 5 settembre 2026
# --------------------------------------------------------------------------
#
# «Dividerei bene la parte market, la parte ristorazione, la parte
# esperienze.» Non e' una divisione estetica: sono tre cose che si comportano
# in modo diverso davanti alla **differenza di fine soggiorno**, che e' il
# punto in cui questo prodotto o dice la verita' o non serve a niente.
#
#   PORTAVIA  (merce)      esce di casa.      Venderla SPIEGA un'assenza.
#   APRILA    (consumo)    finisce in casa.   Venderla SPIEGA un'assenza.
#   RESTACI   (esperienza) resta dov'e'.      Venderla NON spiega NIENTE.
#
# La terza riga e' l'unica che conta davvero, ed e' il motivo per cui i
# generi stanno nel codice e non in una pagina di marketing: se una serata
# in vasca potesse "spiegare" un phon mancante, il registro avrebbe imparato
# a giustificare le assenze con incassi che non c'entrano — e sarebbe di
# nuovo il sistema che parla a se' stesso di §4, stavolta con i soldi.
MERCE, CONSUMO, ESPERIENZA = "merce", "consumo", "esperienza"
GENERI = (MERCE, CONSUMO, ESPERIENZA)

#: Nomi commerciali dei tre generi. Sono imperativi come PORTAVIA: dicono
#: insieme il permesso e l'atto. Vanno cercati (App Store, EUIPO, dominio)
#: PRIMA di adottarli — la lezione e' costata due rinomine.
NOMI_DEI_GENERI = {MERCE: "PORTAVIA", CONSUMO: "APRILA", ESPERIENZA: "RESTACI"}

#: L'invariante. Un genere spiega un'assenza solo se l'oggetto poteva
#: davvero uscire di casa o finire.
SPIEGA_ASSENZA = {MERCE: True, CONSUMO: True, ESPERIENZA: False}


def genere_valido(genere: str) -> str:
    if genere not in GENERI:
        raise ValueError(f"genere sconosciuto: {genere!r} (attesi: {GENERI})")
    return genere


class Regole:
    """Le regole del proprietario. Il Mediatore non puo' uscire da qui.

    `commissione` e' la quota dell'applicazione. Va dichiarata a **entrambe**
    le parti: un prezzo maggiorato in silenzio su tutti e due i lati e' una
    pratica che si paga cara la prima volta che qualcuno confronta due schermi.
    """

    def __init__(self, prezzo_minimo: dict[str, float] | None = None,
                 sconto_massimo: float = 0.15, commissione: float = 0.12,
                 margine: float = 0.25, mai: tuple = (), valuta: str = "EUR",
                 generi: dict[str, str] | None = None):
        if not 0 <= sconto_massimo < 1:
            raise ValueError("sconto_massimo va fra 0 e 1")
        if not 0 <= commissione < 1:
            raise ValueError("commissione va fra 0 e 1")
        if margine < 0:
            raise ValueError("margine non puo' essere negativo")
        #: **`prezzo_minimo` e' quanto incassa il PROPRIETARIO, netto.** Era
        #: il prezzo esposto, e con lo sconto massimo il proprietario finiva
        #: sotto il minimo che aveva dichiarato — trovato eseguendo, non
        #: rileggendo. Un proprietario che scopre di aver preso meno di
        #: quanto aveva scritto non usa piu' il prodotto, e ha ragione.
        self.prezzo_minimo = prezzo_minimo or {}
        self.sconto_massimo = sconto_massimo
        self.commissione = commissione
        #: Ricarico di listino: e' lo spazio in cui la trattativa puo'
        #: muoversi senza toccare il minimo del proprietario. Senza margine
        #: non c'e' trattativa possibile, solo prendere o lasciare.
        self.margine = margine
        self.mai = tuple(m.lower() for m in mai) + MAI_IN_VENDITA
        self.valuta = valuta
        #: chiave -> genere. Il difetto sta dal lato sicuro: cio' che non e'
        #: dichiarato e' MERCE, cioe' qualcosa che puo' uscire di casa e che
        #: quindi va riconciliato. Dichiarare per sbaglio un'esperienza come
        #: merce fa vedere un'assenza in piu'; il contrario ne nasconde una.
        self.generi = {k: genere_valido(v) for k, v in (generi or {}).items()}

    def genere(self, chiave: str) -> str:
        return self.generi.get(chiave, MERCE)

    def vendibile(self, chiave: str, titolo: str) -> tuple[bool, str]:
        t = f"{chiave} {titolo}".lower()
        for m in self.mai:
            if m in t:
                return False, f"escluso dal proprietario o per sicurezza: «{m}»"
        if chiave not in self.prezzo_minimo:
            return False, "nessun prezzo minimo dichiarato: non e' in vendita"
        return True, ""

    def minimo(self, chiave: str) -> float | None:
        return self.prezzo_minimo.get(chiave)

    def soglia(self, chiave: str) -> float | None:
        """Prezzo lordo sotto il quale il proprietario incasserebbe meno del
        suo minimo. E' il pavimento assoluto: nessuno sconto lo attraversa."""
        m = self.minimo(chiave)
        if m is None:
            return None
        return round(m / (1 - self.commissione) + 0.005, 2)

    def esposto(self, chiave: str) -> float | None:
        """Prezzo che l'ospite vede: soglia piu' margine di trattativa.

        La maggiorazione e' **una sola e dichiarata**. Maggiorare da tutt'e
        due i lati come due margini diversi e' invitare qualcuno a
        confrontare i due schermi, e succede.
        """
        s = self.soglia(chiave)
        return None if s is None else round(s * (1 + self.margine), 2)

    def limite(self, chiave: str) -> float | None:
        """Offerta piu' bassa accettabile: mai sotto la soglia."""
        e, s = self.esposto(chiave), self.soglia(chiave)
        if e is None:
            return None
        return round(max(e * (1 - self.sconto_massimo), s), 2)

    def incasso_proprietario(self, prezzo: float) -> float:
        return round(prezzo * (1 - self.commissione), 2)


# --------------------------------------------------------------------------
# il Mediatore
# --------------------------------------------------------------------------

ACCETTA, RILANCIA, RIFIUTA = "accetta", "rilancia", "rifiuta"


def valuta_offerta(chiave: str, titolo: str, offerta: float, regole: Regole) -> dict:
    """La decisione. Nessun modello linguistico partecipa a questa funzione.

    Deterministica di proposito: la stessa offerta da' sempre lo stesso esito,
    e si puo' rieseguire su una lite per mostrare perche' fu accettata.
    """
    ok, motivo = regole.vendibile(chiave, titolo)
    if not ok:
        return {"esito": RIFIUTA, "motivo": motivo}
    esposto, limite = regole.esposto(chiave), regole.limite(chiave)
    if offerta <= 0:
        return {"esito": RIFIUTA, "motivo": "offerta non valida"}
    if offerta >= esposto:
        return {"esito": ACCETTA, "prezzo": round(offerta, 2), "esposto": esposto}
    if offerta >= limite:
        return {"esito": ACCETTA, "prezzo": round(offerta, 2), "esposto": esposto,
                "sconto": round(1 - offerta / esposto, 3)}
    return {"esito": RILANCIA, "controproposta": limite, "esposto": esposto,
            "motivo": f"sotto il limite del proprietario ({limite} {regole.valuta})"}


def parole_del_mediatore(decisione: dict, titolo: str, regole: Regole) -> str:
    """La frase. Il modello, quando c'e', riscrive QUESTA — non decide niente.

    Se il provider e' assente il testo resta questo, ed e' gia' corretto:
    nessuna funzione commerciale di questo modulo dipende da un modello acceso.
    """
    v = regole.valuta
    if decisione["esito"] == ACCETTA:
        return (f"Affare fatto per «{titolo}»: {decisione['prezzo']:.2f} {v}. "
                "Te lo prepariamo per la partenza.")
    if decisione["esito"] == RILANCIA:
        return (f"Su «{titolo}» non posso scendere sotto "
                f"{decisione['controproposta']:.2f} {v}. Se ti va, chiudiamo li'.")
    return f"«{titolo}» non e' in vendita: {decisione['motivo']}."


# --------------------------------------------------------------------------
# il registro delle vendite
# --------------------------------------------------------------------------

class Portavia:
    """Catalogo e vendite. Append-only, come tutto il resto del progetto."""

    def __init__(self, percorso: Path | str = CATALOGO, regole: Regole | None = None):
        self.percorso = Path(percorso)
        self.regole = regole or Regole()
        self.movimenti: list[dict] = []
        self.carica()

    def carica(self) -> int:
        self.movimenti = []
        if not self.percorso.exists():
            return 0
        with open(self.percorso, "r", encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if riga:
                    try:
                        self.movimenti.append(json.loads(riga))
                    except json.JSONDecodeError:
                        pass
        return len(self.movimenti)

    def _scrivi(self, voce: dict) -> dict:
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(voce, ensure_ascii=False) + "\n")
        self.movimenti.append(voce)
        return voce

    def vendita(self, chiave: str, titolo: str, prezzo: float,
                soggiorno: str = "", alloggio: str = "",
                genere: str | None = None, quantita: int = 1,
                quando: str = "") -> dict:
        """Registra una vendita. `genere` decide come sara' letta a fine

        soggiorno: vedi SPIEGA_ASSENZA in testa al modulo.

        `quantita` e' un fatto sulla vendita — «due bottiglie» — e **non**
        una giacenza: questo modulo non sa quante bottiglie ci fossero,
        perche' l'inventario tiene una voce per titolo e non un conteggio.
        Dichiararlo qui e' l'unico modo onesto di scriverlo senza far
        credere che il magazzino sia gestito.
        """
        lordo = round(float(prezzo), 2)
        commissione = round(lordo * self.regole.commissione, 2)
        if quantita < 1 or int(quantita) != quantita:
            raise ValueError("quantita deve essere un intero >= 1")
        return self._scrivi({
            "tipo": "vendita", "chiave": chiave, "titolo": titolo,
            "genere": genere_valido(genere or self.regole.genere(chiave)),
            "quantita": int(quantita),
            "prezzo": lordo,
            "commissione": commissione,
            "al_proprietario": round(lordo - commissione, 2),
            "valuta": self.regole.valuta,
            "quando": quando,
            "soggiorno": soggiorno, "alloggio": alloggio,
            "momento": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def venduti(self, soggiorno: str | None = None,
                solo_generi: tuple | None = None) -> dict[str, dict]:
        """Le vendite, per chiave.

        `solo_generi` serve a chi deve spiegare un'assenza: un movimento
        senza genere e' una vendita scritta prima del 05/09 e vale MERCE,
        che e' l'ipotesi che non nasconde niente.
        """
        return {m["chiave"]: m for m in self.movimenti
                if m.get("tipo") == "vendita"
                and (soggiorno is None or m.get("soggiorno") == soggiorno)
                and (solo_generi is None
                     or m.get("genere", MERCE) in solo_generi)}

    def incasso(self, soggiorno: str | None = None) -> dict:
        """Quanto e' entrato, tenuto separato per valuta.

        Sommare euro e CHIARI darebbe un numero che non esiste. La console lo
        ha reso evidente: mostrava «9.00» e accanto l'unita' dell'ultima
        vendita, che poteva essere l'altra. Quindi: `per_valuta` e' sempre la
        verita'; i campi piatti restano solo quando c'e' una valuta sola, e
        valgono `None` quando ce n'e' piu' d'una. Un `None` che rompe una
        stampa e' meglio di un totale che non significa niente.
        """
        v = list(self.venduti(soggiorno).values())
        per_valuta: dict[str, dict] = {}
        per_genere: dict[str, dict] = {}
        for x in v:
            for indice, chiave_gruppo in ((per_valuta, x.get("valuta") or "?"),
                                          (per_genere, x.get("genere", MERCE))):
                c = indice.setdefault(chiave_gruppo, {
                    "vendite": 0, "lordo": 0.0, "commissione": 0.0,
                    "al_proprietario": 0.0})
                c["vendite"] += 1
                for k in ("lordo", "commissione", "al_proprietario"):
                    c[k] = round(c[k] + float(x["prezzo" if k == "lordo" else k]), 2)
        sola = list(per_valuta)[0] if len(per_valuta) == 1 else None
        piatti = per_valuta[sola] if sola else {
            "lordo": None, "commissione": None, "al_proprietario": None}
        return {"vendite": len(v), "valuta": sola,
                "valute": sorted(per_valuta), "per_valuta": per_valuta,
                "per_genere": per_genere,
                "lordo": piatti["lordo"],
                "commissione": piatti["commissione"],
                "al_proprietario": piatti["al_proprietario"]}


# --------------------------------------------------------------------------
# il punto in cui l'idea diventa codice
# --------------------------------------------------------------------------

def spiega_mancanti(differenza: dict, portavia: Portavia,
                    soggiorno: str | None = None) -> dict:
    """Separa cio' che e' stato COMPRATO da cio' che e' semplicemente sparito.

    E' qui che l'idea di Claudio smette di essere un'idea. La stessa lista di
    ieri — «mancano tre oggetti» — diventa «due li ha comprati, uno no», e
    solo il terzo e' un problema. Un proprietario che apre questa schermata
    vede meno conflitto e piu' incasso, che era esattamente il punto.
    """
    # Solo cio' che poteva uscire di casa o finire puo' spiegare un'assenza.
    # Una serata in vasca venduta ieri non giustifica un phon che non c'e'
    # oggi: l'oggetto e' ancora li', e se non c'e' e' un'altra storia.
    spiegano = tuple(g for g in GENERI if SPIEGA_ASSENZA[g])
    vendute = portavia.venduti(soggiorno, solo_generi=spiegano)
    comprati, non_spiegati = [], []
    for o in differenza.get("mancanti", []):
        v = vendute.get(o.get("chiave"))
        (comprati if v else non_spiegati).append({**o, "vendita": v} if v else o)
    return {
        **differenza,
        "comprati": comprati,
        "non_spiegati": non_spiegati,
        "incasso": portavia.incasso(soggiorno),
    }


def vendita_in_chiari(portavia, crediti, chiave: str, titolo: str,
                      prezzo_eur: float, compratore: str, venditore: str,
                      soggiorno: str = "", alloggio: str = "",
                      genere: str | None = None, quantita: int = 1,
                      quando: str = "") -> dict:
    """Una vendita pagata in CHIARI invece che in euro. Idea di Claudio Terzi.

    Toglie l'attrito nel momento in cui il desiderio e' vivo: chi deve
    tirare fuori la carta per un DVD da nove euro non lo compra; chi ha gia'
    un saldo lo prende.

    L'ordine dei passi non e' indifferente. **Prima si toglie al compratore,
    poi si da' al venditore**: se si invertisse, un saldo insufficiente
    lascerebbe il venditore pagato per una vendita mai avvenuta, e il libro
    dei chiari conterrebbe valore nato dal nulla. Un'eccezione qui deve
    lasciare il mondo com'era.

    La commissione resta la stessa e resta dichiarata: cambia l'unita', non
    il patto.
    """
    from .crediti import prezzo_in_chiari
    prezzo = prezzo_in_chiari(prezzo_eur)
    regole = portavia.regole
    ok, motivo = regole.vendibile(chiave, titolo)
    if not ok:
        raise ValueError(motivo)
    riferimento = f"portavia:{chiave}:{soggiorno or alloggio or '-'}"

    crediti.spendi(compratore, prezzo, "acquisto", riferimento)
    commissione = max(1, round(prezzo * regole.commissione)) if regole.commissione else 0
    al_venditore = prezzo - commissione
    if al_venditore > 0:
        crediti.emetti(venditore, al_venditore, "vendita", riferimento)

    voce = portavia._scrivi({
        "tipo": "vendita", "chiave": chiave, "titolo": titolo,
        "genere": genere_valido(genere or regole.genere(chiave)),
        "quantita": int(quantita), "quando": quando,
        "prezzo": prezzo, "commissione": commissione,
        "al_proprietario": al_venditore, "valuta": "chiari",
        "compratore": compratore, "venditore": venditore,
        "soggiorno": soggiorno, "alloggio": alloggio,
        "momento": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    return voce


def immagine_generata_ammessa_come_prova() -> bool:
    """Sempre falso, e sta scritto qui perche' sia citabile da un test.

    La VETRINA puo' generare l'immagine bella di un oggetto. La fotografia
    che dimostra che l'oggetto c'era non puo' essere generata ne' ritoccata:
    e' esclusa dalle prove nei reclami danni. Un'immagine generata non entra
    mai nella catena delle consegne.
    """
    return False
