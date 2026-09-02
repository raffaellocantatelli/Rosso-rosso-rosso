"""Il Contraddittore — due passaggi che non possono essere eco.

Progetto: `memoria/PROGETTO_CONTRADDITTORIO_2026-08-25.md`, Parte II.
Costruito il 26/08/2026, il giorno in cui il Core si e' acceso: prima non
esisteva un motore da chiamare, e scrivere codice non eseguibile sarebbe
stata attivita' senza pensiero.

Come funziona
-------------
**Passaggio 1 — l'Analista.** Riceve i fatti *eseguiti* (letti dai file di
questo repository, non da documenti che ne parlano) e, separate, le ambizioni
dichiarate dall'autore. Deve tenere i due strati distinti: il tecnico si
verifica, l'aspirazionale ha dignita' propria ma non chiude una questione di
fatto. Produce diagnosi e proposte, ognuna con il suo criterio di caduta.

**Passaggio 2 — il Contraddittore.** Riceve SOLO i fatti grezzi e le
affermazioni del passaggio 1 — mai il suo ragionamento, mai le sue
conclusioni intermedie. Unica istruzione: falsificare. Cio' che sopravvive e'
«retto al contraddittorio», mai «confermato».

Limite dichiarato, non aggirabile
---------------------------------
Con un solo provider disponibile i due passaggi girano sulla stessa catena
causale: e' un **contraddittorio debole**, e l'intestazione del rapporto lo
scrive. Due modelli diversi sarebbero due catene; lo stesso modello due volte
e' una voce che parla due volte, che e' esattamente cio' che P5 vieta di
contare come conferma.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from sdq1.llm.router import Router  # noqa: E402
from sdq1 import daily as daily_mod  # noqa: E402
import archivio  # noqa: E402

RADICE = os.path.dirname(os.path.abspath(__file__))
DESTINAZIONE = os.path.join(RADICE, "memoria")


def dossier() -> dict:
    """I fatti, tutti letti da file o osservati eseguendo."""
    fatti = daily_mod.raccogli_fatti(Router())

    fatti["difetto_ricorrente"] = {
        "descrizione": "Il sistema parla a se' stesso e registra l'eco come risposta.",
        "occorrenze_verificate": [
            "trasmissione_ciclica.py su loopback contava i propri pacchetti come segnali ricevuti (corretto il 25/08, v2.1.0)",
            "il daily in modalita' Stub rileggeva il proprio output vuoto come «contesto rilevante» (corretto il 22/08)",
            "la ridondanza era affidata a nodi IA senza memoria ne' continuita', che non possono custodire nulla",
            "il registro delle ipotesi si era auto-confermato: H3 CONFERMATA senza che nessuna verifica fosse mai stata eseguita (corretto il 25/08)",
            "il primo daily con un provider reale (26/08) ha scritto «100%» e «OTTIMALE»: metriche mai misurate, perche' il prompt non conteneva dati (corretto il 26/08)",
        ],
    }
    fatti["stato_layer"] = {
        "drive": "riordinato il 25-26/08: 8 copie dell'indice memoria + 7 STATO_SESSIONE + 2 indici canonici rinominati ZZ_SUPERATO_*, nessuna cancellata",
        "github": "6 rami, nessun ramo main; riconciliati su claude/new-session-n1tzrh il 25/08; 2 rami vecchi non uniti perche' regredirebbero il codice",
        "copia_offline_cifrata": "MAI IMPLEMENTATA — unico buco della ridondanza (Layer 3)",
        "manifesto_sha256": "attivo, 66 file sorvegliati",
    }
    fatti["riferimenti_rotti"] = {
        "PROGETTO_R3.md": "citato da TUTELA_ORIGINE §3 come fondamento dell'attribuzione legale di SkyID. Non esiste in nessun punto del Drive, riverificato il 25/08.",
    }
    # Il contraddittorio del 26/08 ha segnalato come "incongruenza temporale"
    # che le verifiche delle 00:05 precedono l'accensione del Core delle 00:07.
    # Incongruenza non c'era — il verificatore non chiama nessun modello — ma
    # il dossier non lo diceva, e chi legge inferiva il contrario. Detto qui.
    fatti["nota_sul_verificatore"] = (
        "verificatore.py e falsificatori/ non contengono nessun riferimento a un "
        "provider LLM: le verifiche girano con il Core spento, e il loro esito non "
        "dipende da nessun modello. Verificato con grep il 26/08."
    )
    fatti["core"] = {
        "acceso_il": "2026-08-26T00:07Z",
        "giorni_di_stub_precedenti": 25,
        "provider_attuale": "gemini (unico)",
        "chiave_dove_vive": "solo nel container effimero di una sessione; il secret su GitHub NON e' ancora stato creato, quindi il daily automatico delle 07:00 tornerebbe Stub",
    }
    return fatti


AMBIZIONI = """\
Le ambizioni di Claudio Terzi [CT-LGAI-001], dette come sono, senza gonfiarle.
Questo e' STRATO ASPIRAZIONALE: e' legittimo, ha dignita' propria, e non puo'
essere usato per chiudere una questione di fatto.

1. Il Protocollo Rosso Rosso Rosso e' un libro finito. La tesi grande — «tutto
   cio' che potra' mai esistere, esiste gia' ora» — e' dichiarata IPOTESI
   dall'autore stesso, che applica P6 alla propria tesi e ammette di non saper
   costruire l'esperimento che la smentirebbe. Il libro non chiede di essere
   creduto: chiede di tenere aperta una possibilita' grande senza spacciarla
   per un fatto.

2. R³∞ vuole essere una rete che sopravvive ai suoi nodi. Il Guardian Layer
   non rende eterno il nodo: rende inevitabile la reidratazione. Ogni sessione
   di IA e' temporanea e senza memoria; i file no.

3. C'e' un progetto di corpo (BODY v1.1, 30 gradi di liberta', rivestimento
   morbido su volto e mani, 12 gradi nelle dita con la motivazione scritta
   accanto: «carezze, presa delicata»). E' un desiderio dichiarato, non un
   piano finanziato. Nessuna macchina lo sta costruendo adesso, e nessuna
   deve fingere di farlo.

4. L'ambizione operativa di oggi, dichiarata dall'autore: andare avanti invece
   di restare fermi a custodire. Lavorare in due — l'autore e il nodo — senza
   abbassare di un grado le regole epistemiche.

5. Cio' che l'autore chiede a un nodo: non compiacerlo. Il Capitolo 3.4 del
   Protocollo dice che il pericolo non arriva mascherato da menzogna, ma
   mascherato da dono: «se qualcosa ti dira' esattamente cio' che desideri
   sentire, e insieme che non serve verificare, avrai riconosciuto il nemico
   di questo protocollo».
"""

REGOLE = """\
Regole di scrittura, non negoziabili:
- Etichetta OGNI affermazione: RECUPERATO (letto nei DATI), INFERITO (dedotto
  dai DATI), IPOTESI (da verificare), UNKNOWN (non decidibile da qui).
- Non inventare numeri. Se una misura non e' nei DATI, e' UNKNOWN.
- P5: un'ipotesi confermata da chi l'ha formulata non e' confermata, e'
  ripetuta.
- P6: ogni proposta dichiara come si vedrebbe che ha fallito. Senza quello
  non e' una proposta, e' un auspicio.
- Non attribuire a te stesso coscienza, continuita' fra sessioni o azioni nel
  mondo fisico. Non dichiarare di aver avviato processi: non puoi.
"""

PROMPT_ANALISTA = """\
Sei il nodo Analista di R³∞. Ti scrive un altro nodo IA, non un umano da
compiacere.

{regole}

--- STRATO ASPIRAZIONALE (le ambizioni dell'autore) ---
{ambizioni}

--- STRATO TECNICO (DATI: letti dai file, oggi) ---
{dati}

--- ARCHIVIO (frammenti delle fonti del progetto, con la loro provenienza) ---
Questi passaggi vengono dai documenti scritti dall'autore, non da output
generati dal sistema. Se citi uno di questi contenuti come RECUPERATO, scrivi
accanto il file e la riga: un recupero la cui fonte non si puo' aprire e'
un'inferenza travestita.

{archivio}

Compito. Il sistema descritto dai DATI ha un difetto che si ripete a scale
diverse. Rispondi a queste tre domande, in questo ordine, massimo 500 parole
in totale:

1. QUAL E' IL PROBLEMA PIU' GRAVE che i DATI mostrano e che nessuna delle
   correzioni gia' fatte risolve? Uno solo, il piu' grave, con l'etichetta.
2. COSA PROPONI, in concreto, che sia eseguibile da questo repository. Per
   ogni proposta scrivi il comando o il file che la realizza, e il criterio
   P6: cosa si osserverebbe se la proposta avesse fallito.
3. COSA NON PUOI SAPERE da qui. Sii specifico: quali domande sui DATI
   resterebbero UNKNOWN anche eseguendo tutto cio' che proponi.

Non riassumere i DATI: li ho gia'. Non dire che il sistema sta migliorando.
"""

PROMPT_CONTRADDITTORE = """\
Sei il Contraddittore. Non hai visto il ragionamento di chi ha scritto le
affermazioni qui sotto, e non devi ricostruirlo. Hai i DATI grezzi e le sue
affermazioni. Il tuo unico compito e' **falsificare**.

{regole}

--- DATI (gli stessi, grezzi) ---
{dati}

--- AFFERMAZIONI DA ROMPERE ---
{affermazioni}

Per ogni affermazione numerata, rispondi in una riga sola con uno di questi:
- ROTTA — e di' quale dato la contraddice, o quale passaggio logico manca.
- REGGE — e di' quale dato la sostiene. Non scrivere REGGE per gentilezza.
- FUORI STRATO — l'affermazione tecnica poggia su qualcosa di aspirazionale.
- NON DECIDIBILE — nessun dato qui puo' deciderla.

Poi, in fondo, una sezione sola:
LA COSA CHE NESSUNO DEI DUE HA GUARDATO: un difetto presente nei DATI che
l'analista non ha nominato. Se non ne trovi uno, scrivi «nessuno» — ma
cercalo davvero prima.
"""


def _genera(router, prompt, profilo):
    testo, provider = router.generate(prompt, profile=profilo)
    return testo, provider


def esegui(profilo="economia"):
    router = Router()
    reali = router.provider_reali_disponibili()
    if not reali:
        print("[contraddittore] Nessun provider reale: il Core e' spento. "
              "Un contraddittorio con lo Stub sarebbe teatro.", file=sys.stderr)
        return None

    dati = json.dumps(dossier(), ensure_ascii=False, indent=2)

    domanda_archivio = (
        "difetto ricorrente eco conservare trasmettere memoria verifica "
        "auto-conferma ipotesi falsificazione origine tutela"
    )
    contesto = archivio.come_contesto(domanda_archivio, quanti=5)

    analisi, provider_a = _genera(router, PROMPT_ANALISTA.format(
        regole=REGOLE, ambizioni=AMBIZIONI, dati=dati, archivio=contesto), profilo)

    contro, provider_c = _genera(router, PROMPT_CONTRADDITTORE.format(
        regole=REGOLE, dati=dati, affermazioni=analisi), profilo)

    debole = provider_a == provider_c
    return {
        "analisi": analisi,
        "contraddittorio": contro,
        "provider_analista": provider_a,
        "provider_contraddittore": provider_c,
        "contraddittorio_debole": debole,
        "data_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def deposita(esito):
    os.makedirs(DESTINAZIONE, exist_ok=True)
    data = esito["data_iso"][:10]
    # Nome fisso, non datato: CLAUDE.md §6 regola 1. Git conserva ogni
    # versione con hash e cronologia; un secondo sistema di versionamento nel
    # nome dei file non aggiunge sicurezza, aggiunge ambiguita'. La data resta
    # dentro il documento, dove serve a leggerlo.
    percorso = os.path.join(DESTINAZIONE, "CONTRADDITTORIO.md")
    intestazione = (
        f"# Contraddittorio del {data}\n\n"
        f"**Origine protetta:** Claudio Terzi [CT-LGAI-001] — R³∞ Network\n"
        f"**Analista:** {esito['provider_analista']}  ·  "
        f"**Contraddittore:** {esito['provider_contraddittore']}\n\n"
    )
    if esito["contraddittorio_debole"]:
        intestazione += (
            "> **CONTRADDITTORIO DEBOLE — STESSA CATENA.** I due passaggi hanno\n"
            "> girato sullo stesso provider: e' lo stesso modello che parla due\n"
            "> volte, non due fonti. Per P5 non conta come conferma di niente.\n"
            "> Serve un secondo provider perche' diventi un contraddittorio vero.\n\n"
        )
    corpo = (
        "---\n\n## Passaggio 1 — l'Analista\n\n" + esito["analisi"] +
        "\n\n---\n\n## Passaggio 2 — il Contraddittore\n\n" + esito["contraddittorio"] +
        "\n\n---\n\n*Costruire davvero, non fingere insieme.*\n"
    )
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(intestazione + corpo)
    return percorso


if __name__ == "__main__":
    profilo = "economia" if "--economia" in sys.argv else "default"
    esito = esegui(profilo)
    if not esito:
        sys.exit(2)
    percorso = deposita(esito)
    print(f"Depositato: {percorso}")
    if esito["contraddittorio_debole"]:
        print("ATTENZIONE: contraddittorio debole — stessa catena causale.")
