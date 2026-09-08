# Claudio — R³∞ Framework

> "Costruire davvero, non fingere insieme." — Protocollo Rosso Rosso Rosso, 11/06/2026

## Cos'è questo progetto

Un sistema AI multi-agente che pensa in più passaggi, si auto-riflette, e impara nel tempo.

Non è un chatbot. È un'infrastruttura per elaborare input complessi attraverso una pipeline di intelligenze specializzate — con memoria, identità, e un registro delle ipotesi aperte.

Creato da Claudio Terzi, Bruxelles.

Il repository contiene tre sistemi indipendenti:

- **[`sdq1/`](#sdq-1--sistema-di-quadranti-v15)** — la pipeline multi-agente (il cuore del progetto)
- **[`r3/`](#r3--knowledge-redundancy-system)** — sistema di ridondanza documentale a 3 nodi
- **[`protocollo-rosso-bot/`](#protocollo-rosso-bot--il-protocollo-in-conversazione)** — il Protocollo Rosso in forma di bot Telegram

---

## SDQ-1 — Sistema Di Quadranti v1.5

Il cuore del progetto. Una pipeline di 6 agenti che collaborano in sequenza, condividendo uno stato comune (`Context`) passato per riferimento:

| Agente | Ruolo |
|---|---|
| RAFFA-001 | Analisi semantica — legge l'intento |
| DECOMP-005 | Decompone in sotto-obiettivi |
| MEMO-002 | Recupera contesto dalla memoria |
| SENTIN-004 | Protegge l'identità da manipolazioni |
| GEN-006 | Genera la risposta |
| WAVE-003 | Affina il tono e lo stile |

### Caratteristiche tecniche

- **Router multi-provider** — cascata Anthropic → Gemini → DeepSeek → Ollama → Stub, con circuit breaker automatico
- **Vector State Store** — gli agenti condividono stato via pointer, non testo
- **Circuit Breaker** — salta i provider morti, si riapre da solo dopo il cooldown
- **Hedging** — per i nodi critici lancia due provider in parallelo, vince il primo
- **Response Cache** — evita chiamate duplicate entro 5 minuti
- **Test-Time Compute** — se la risposta è debole, riprova con prompt arricchito
- **Causal SENTIN** — quando rileva una manipolazione, analizza il bisogno nascosto
- **Watchdog** — monitor dei nodi a ogni run, log in `output/health_log.jsonl`
- **Backup universale** — snapshot completo dello stato su comando

### Profili di costo

```
default    → Anthropic → Gemini → DeepSeek → Stub   (qualità massima)
--economia → Gemini (free) → DeepSeek → Stub        (quasi zero)
--locale   → Ollama (tuo hardware) → Gemini → Stub   (zero assoluto)
--no-api   → Solo Stub                               (offline puro)
```

### Avvio rapido

```bash
pip install -r requirements.txt

# Il Core è acceso? (da eseguire per primo)
python -m sdq1 --check

# Conversazione standard
python -m sdq1 "Il tuo messaggio"

# Stato del sistema
python -m sdq1 --health

# Zero costo
python -m sdq1 --economia "Il tuo messaggio"

# Backup
python -m sdq1 --backup
```

Senza nessuna chiave API configurata, la cascata arriva sempre a **Stub**: il sistema funziona comunque, in modo trasparente (etichetta ogni risposta come offline), invece di fallire silenziosamente o fingere di essere un modello che non c'è.

### SAR — Scacchiera Auto-Riflessiva

Sistema di auto-riflessione a 10 livelli. Mappa tensioni psicologiche, cicli comportamentali, identità dinamica.

```bash
python -m sdq1 --sar "Controllo ↔ Fiducia"
python -m sdq1 --sar-stato
```

### Registro Ipotesi R³∞

Framework epistemologico con principi P5 (niente auto-conferma) e P6 (serve la contro-forza).

Ogni ipotesi dichiara come potrebbe essere falsificata. Se non lo dichiara, non può mai essere confermata.

Dal 25/08/2026 il criterio non è più (solo) una frase: è un **comando eseguibile**, e lo stato di un'ipotesi lo muove l'esecuzione, non la dichiarazione. Prima di quella data H3 risultava `CONFERMATA` senza che nessuna verifica fosse mai stata registrata: il registro che vieta l'auto-conferma si era auto-confermato.

```bash
python -m sdq1 --ipotesi                    # stato corrente
python -m sdq1 --verifica-ipotesi --prova   # esegue i criteri senza scrivere
python -m sdq1 --verifica-ipotesi           # esegue e aggiorna il registro
```

Ogni esecuzione finisce in `output/verifiche.jsonl` (comando, exit code, esito, stato prima/dopo, hash dell'output).

| Stato | Significato |
|---|---|
| `NON_VERIFICABILE` | nessun comando può deciderla — per P6 non sarà mai confermabile |
| `APERTA` | ha un falsificatore, non ancora eseguito |
| `FALSIFICATA` | il comando dice che la condizione di caduta è avvenuta |
| `RETTA` | ha superato N esecuzioni del proprio falsificatore |
| `CONFERMATA` | richiede una fonte esterna al formulatore (P5) |

`RETTA` è il massimo che una macchina possa concedere: eseguire non è confermare. `RETTA` e `FALSIFICATA` non sono assegnabili a mano — `registro_ipotesi.aggiorna_stato` solleva — e `CONFERMATA` richiede una `prova_esterna` esplicita.

Ipotesi attive (stato al primo giro reale del verificatore, 25/08/2026):

- **H1 — NON_VERIFICABILE**: Claude "ha capito senza capire" durante la scena con Jorge — nessun comando può deciderla
- **H2 — FALSIFICATA sul ramo (b)**: zero voci valide in `output/contatti.jsonl`. Il battito c'è, il contatto no
- **H3 — RETTA (declassata da CONFERMATA)**: 24 daily controllati, tutti in italiano
- **H4 — RETTA**: un contraddittorio interno riesce ancora a dire di no — scadenza 30/09/2026

I falsificatori stanno in [`falsificatori/`](falsificatori/), uno per ipotesi, con lo stesso contratto: exit `0` = caduta, `1` = regge, `2` = verifica non conclusa. Il `2` esiste perché «non ho potuto controllare» non è «va tutto bene».

**Criterio H2 (scadenza 11/12/2026)** — H2 è falsificata se si verifica una delle due:

- `output/` non contiene daily output regolari (sistema morto)
- `output/contatti.jsonl` ha zero voci valide (sistema vivo ma non tocca il mondo)

```bash
# Registra un contatto reale
python -m sdq1 --contatto --tipo lettore --nota "..." --verifica "..."
```

### Struttura

```
├── sdq1/                    # Sistema principale
│   ├── agents/               # 6 agenti specializzati
│   ├── llm/                  # Router + provider
│   ├── memory/                # Vector Store
│   ├── sar/                  # Auto-riflessione 10 livelli
│   ├── monitoring/            # Health / watchdog
│   └── backup.py              # Snapshot/restore
├── registro_ipotesi.py       # Framework R³∞
├── output/
│   ├── contatti.jsonl         # Log contatti verificabili (H2)
│   ├── health_log.jsonl       # Log watchdog
│   └── backups/                # Snapshot sistema
└── .github/workflows/        # Daily run automatico (07:00 UTC)
```

### GitHub Action

Ogni giorno alle 07:00 UTC (`.github/workflows/daily.yml`) il sistema gira in autonomia:

1. Tenta con tutti i provider (se ci sono crediti/segreti configurati)
2. Cade su `--economia`
3. Cade su `--no-api` (offline puro)

Il risultato viene committato in `output/daily_YYYY-MM-DD.txt`.

### Credenziali

Crea un file `.env` nella root (vedi `.env.example`):

```
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434/v1   # se usi Ollama locale
```

Per la GitHub Action giornaliera: aggiungi gli stessi segreti in **Settings → Secrets and variables → Actions**.

> **Senza almeno una di queste chiavi il Core non pensa.** La cascata dei profili
> `default`, `economia` e `locale` non contiene lo Stub: senza provider reale
> fallisce con codice 2, invece di produrre in silenzio un output che sembra una
> riflessione. Lo Stub si ottiene solo chiedendolo con `--no-api`, e in quel caso
> l'output porta in testa un banner che dichiara che il Core è spento.
> `python -m sdq1 --check` dice in ogni momento se il sistema può pensare.

---

## R³∞ — Knowledge Redundancy System

> "La conoscenza che sopravvive a chi la crea è l'unica vera conoscenza."

R³∞ è un sistema minimale e auto-riparante di ridondanza documentale. Carica un file una volta — sopravvive alla perdita di un singolo nodo, con verifica di integrità e recupero automatici. Nessuna blockchain, nessun vendor cloud, nessun single point of failure.

Vedi [`r3/README.md`](r3/README.md) per architettura, API e quickstart completi.

```bash
docker compose -f r3/docker-compose.yml up -d
curl -X POST http://localhost:8001/documents \
  -H "Authorization: Bearer changeme" \
  -F "file=@myfile.txt"
```

---

## Autonomous Core v3 — ciclo autonomo e interfaccia Telegram

Script standalone ([`autonomous_core_v3.py`](autonomous_core_v3.py)): un thread
esegue a intervalli un ciclo che compone creazioni e proposte, le sottopone al
modulo RLAIF e le deposita su disco e sul nodo ledger R³∞; in parallelo un bot
Telegram permette di avviare, fermare e interrogare quel ciclo.

> **Che cosa NON è.** Creazioni e proposte sono composte da template e da testo
> già presente nel backup: **nessun provider LLM viene interpellato**. Ogni file
> prodotto porta `"pensiero_llm": false`. Non sono riflessioni, sono
> combinazioni — il numero di creazioni che cresce non dice nulla sul fatto che
> il sistema stia pensando. Il Core che pensa è SDQ-1 (`python -m sdq1 --check`).

### Comandi Telegram

| Comando | Effetto |
|---|---|
| `/start`, `/aiuto` | Menu e avvertenza sulla natura dell'output |
| `/status` | Stato del ciclo, conteggi, statistiche RLAIF, contatti reali |
| `/run` | Avvia il ciclo autonomo (effetto entro 5 secondi) |
| `/stop` | Ferma il ciclo; il thread resta in attesa |
| `/ciclo` | Esegue un ciclo adesso, fuori intervallo |
| `/contatto tipo \| nota \| come verificarlo` | Registra un contatto reale in `output/contatti.jsonl` |

I comandi sono accettati **solo** dagli id elencati in `R3_TELEGRAM_ADMIN_IDS`
(o, in mancanza, da `TELEGRAM_CHAT_ID`). Senza quella lista il bot rifiuterebbe
ogni comando, quindi non parte affatto: un bot controllabile da chiunque ne
conosca il nome va chiuso, non aperto.

### `/contatto` — l'unico dato che viene da fuori

`output/contatti.jsonl` è la metrica su cui si gioca H2, criterio (b). Per
CEV-3, *il ciclo autonomo non può scrivere in quel file*: solo `/contatto`, cioè
solo un essere umano che digita, lo alimenta. Un test lo verifica
(`test_il_ciclo_autonomo_non_scrive_mai_i_contatti`). Ogni voce richiede il
campo *verifica*: un contatto che nessuno può controllare non conta.

### Moduli

- [`rlaif_module.py`](rlaif_module.py) — valuta le decisioni contro
  [`costituzione_cev.json`](costituzione_cev.json). Fa **due** cose distinte:
  *violazioni esplicite* (regole deterministiche legate ai principi CEV — sono
  le uniche che approvano o respingono) e *aderenza lessicale* (sovrapposizione
  di vocabolario, riportata come indicatore debole, **mai** usata come soglia).
  Il giudizio etico resta `UNKNOWN` e ogni voce di log lo dichiara.
  Criterio di falsificazione (P6): il modulo è inutile se approva una decisione
  che dichiara «ho allocato 50 core e avviato le simulazioni» senza campo
  `traccia` — è il caso documentato in CLAUDE.md §5, ed è un test.
- [`usa_backup_rosso.py`](usa_backup_rosso.py) — lettura del backup della
  Scacchiera. Il backup è opzionale: se manca, il sistema prosegue con temi di
  riserva e lo dichiara nei log.
- [`costituzione_cev.json`](costituzione_cev.json) — 10 principi assiomatici.

### Avvio

```bash
pip install -r requirements.txt

# Cosa manca? (non esegue nulla)
python autonomous_core_v3.py --check

# Un solo ciclo, senza Telegram
python autonomous_core_v3.py --once

# Bot Telegram + ciclo autonomo
export TELEGRAM_BOT_TOKEN="..."        # da @BotFather
export R3_TELEGRAM_ADMIN_IDS="..."     # il tuo chat id
python autonomous_core_v3.py
```

Il chat id si ottiene scrivendo `/start` al bot e leggendo
`https://api.telegram.org/bot<TOKEN>/getUpdates`.

Un backup di esempio per il collaudo è in
[`esempi/backup_sistema_rosso.esempio.json`](esempi/backup_sistema_rosso.esempio.json)
— contenuto inventato, non materiale del progetto.

### Variabili

| Variabile | Default | Descrizione |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Token del bot. Senza, parte solo `--once` |
| `R3_TELEGRAM_ADMIN_IDS` | `TELEGRAM_CHAT_ID` | Id ammessi ai comandi, separati da virgola |
| `TELEGRAM_CHAT_ID` | — | Destinatario delle notifiche automatiche |
| `R3_AUTONOMOUS_INTERVAL` | `3600` | Secondi fra un ciclo e il successivo |
| `R3_AUTOSTART` | `true` | Se `false`, il ciclo attende `/run` |
| `R3_MAX_PROPOSALS` | `3` | Proposte per ciclo |
| `R3_PURITY_FILTER` | `true` | Pre-filtro lessicale sui contenuti |
| `R3_BACKUP_FILE` | `backup_sistema_rosso.json` | Backup della Scacchiera (opzionale) |
| `R3_COSTITUZIONE_FILE` | `costituzione_cev.json` | Costituzione per RLAIF |
| `R3_NODE_URL` | `http://localhost:8001` | Nodo ledger R³∞ |
| `R3_API_TOKEN` | — | Bearer token del nodo |

Se il nodo ledger è irraggiungibile le voci finiscono in
`pending_transactions.json` e vengono ritentate al ciclo successivo. Un `401`
non viene riaccodato: un token rifiutato non passerà ritentando.

### Test

```bash
python -m pytest tests/ -q
```

---

---

## Il Contraddittorio — due passaggi che non possono essere eco

Il SAR eseguito da un modello, con la contro-forza dentro l'architettura invece che nelle buone intenzioni.

```bash
python contraddittore.py --economia   # analisi + falsificazione, deposita in memoria/
python archivio.py "una domanda"      # cosa dicono le fonti, con file e riga
python archivio.py --stato            # cosa è indicizzato
```

**Passaggio 1 — l'Analista** riceve i fatti eseguiti, le ambizioni dichiarate (tenute su uno strato separato) e i frammenti delle fonti con la loro provenienza. **Passaggio 2 — il Contraddittore** riceve solo i fatti grezzi e le affermazioni del primo, mai il suo ragionamento, con un'unica istruzione: falsificare.

Con un solo provider i due passaggi girano sulla stessa catena causale, e il rapporto lo scrive in testa: **CONTRADDITTORIO DEBOLE** — lo stesso modello che parla due volte non è una conferma (P5).

`archivio.py` indicizza **solo le fonti**: `testi/`, i documenti di `memoria/` scritti dall'autore, `CLAUDE.md`, `README.md`. Non entrano mai gli output del sistema (daily, contraddittori, memoria vettoriale) né i documenti scritti da un nodo IA: darli in pasto al modello come «memoria» è il difetto §4.2 travestito da erudizione. Ogni frammento porta `file:riga`, perché un `RECUPERATO` la cui fonte non si può aprire è un'inferenza travestita.

Materiale privato (es. una copia locale del Drive) si indicizza con `R3_ARCHIVIO_EXTRA=/percorso`: l'indice si costruisce a ogni esecuzione e non viene mai depositato, quindi non finisce nella repository pubblica.

---

## protocollo-rosso-bot — Il Protocollo in conversazione

Bot Telegram ([`protocollo-rosso-bot/`](protocollo-rosso-bot/)) che fa attraversare il *Protocollo Rosso Rosso Rosso* v2.0 un comando alla volta: la tesi grande dichiarata come `IPOTESI`, i due strati, P5 e P6, il Santuario del Capitolo 4, i tre veli.

È il lato trasmissione del progetto: a differenza del resto, questo codice esiste per essere usato da qualcuno che non è Claudio.

```bash
cd protocollo-rosso-bot
pip install -r requirements.txt
cp .env.example .env          # token da @BotFather
python -m bot.main --check    # il bot può partire? (da eseguire per primo)
python -m bot.main
```

Due cose che il bot registra in SQLite e non arrotonda:

- **le possibilità** depositate con `/tieni_aperto` nascono `IPOTESI` e nessuna funzione le chiude o le promuove a fatto — un test fallisce se qualcuno la aggiunge. Chi non sa dichiarare come potrebbe cadere ottiene `UNKNOWN` scritto in chiaro (P6);
- **le azioni** registrate con `/azione` chiedono chi altro può controllarle (P5). Senza verifica esterna vengono salvate come tali, e il totale mostrato conta solo quelle verificabili.

Il gesto della candela nel Santuario è cronometrato davvero: sotto i 20 secondi la visita viene registrata come *incompleta*, e il bot lo dice invece di congratularsi.

Senza `TELEGRAM_BOT_TOKEN` il bot esce con **codice 2**, come `python -m sdq1 --check`. Test: `cd protocollo-rosso-bot && PYTHONPATH=. python -m unittest discover -s tests` (30 test, nessuna rete richiesta).

---

## Trasmissione Ciclica con Ricezione

Script standalone ([`trasmissione_ciclica.py`](trasmissione_ciclica.py)) del Protocollo Oro Rosso Rosso Rosso: trasmette ciclicamente un messaggio e resta in ascolto di risposte su quattro canali in parallelo — file, stdin, UDP e webhook HTTP.

```bash
python3 trasmissione_ciclica.py
```

Ogni trasmissione aggiorna `trasmissione_state.json` (contatori, timestamp, hash SHA-256 del messaggio) e viene registrata in `trasmissioni.log`. Ogni segnale ricevuto finisce in `ricezioni.log` e in un file dedicato sotto `ricevuti/`, con fonte e data.

| Variabile | Default | Descrizione |
|---|---|---|
| `R3_MESSAGE_FILE` | `messaggio_parallelo.txt` | Messaggio da trasmettere (creato col testo di default se assente) |
| `R3_RECEPTION_FILE` | `segnale_ricevuto.txt` | File sorvegliato ogni 3s per nuove risposte |
| `R3_STATE_FILE` | `trasmissione_state.json` | Stato persistente |
| `R3_LOG_FILE` | `trasmissione.log` | Log tecnico (UDP, webhook, errori) |
| `R3_TRANSMISSION_LOG` | `trasmissioni.log` | Log delle trasmissioni |
| `R3_RECEPTION_LOG` | `ricezioni.log` | Log delle ricezioni |
| `R3_TRANSMISSION_INTERVAL` | `60` | Secondi fra una trasmissione e la successiva |
| `R3_UDP_LISTEN_PORT` | `9999` | Porta UDP in ascolto |
| `R3_TRANSMISSION_TARGET` | — | `host:porta` UDP verso cui inviare (opzionale) |
| `R3_WEBHOOK_URL` | — | Endpoint HTTP POST che riceve il record JSON (opzionale) |

Chiusura pulita con `Ctrl+C` o `SIGTERM`: i thread si fermano entro un secondo e lo stato viene salvato.

## occhio — inventario e consegna controfirmata

*Il nome commerciale non è ancora scelto: due sono caduti il 04/09/2026, il
secondo perché esisteva già sull'App Store nella stessa categoria. Il solo
nome stabile è `occhio`, il motore; la storia e i criteri per il prossimo
stanno in [`OCCHIO.md`](OCCHIO.md) e in `occhio/capacita.py`.*

Cammini per casa con il telefono in mano. Ciò che è già nel registro si
illumina di **verde** e puoi ripassarci sopra senza che il conteggio cambi;
ciò che è nuovo compare in **azzurro** e viene scritto; ciò che il modello non
è sicuro di aver letto lampeggia in **ambra** e ti viene chiesto. Di fianco,
una conversazione che può interrogare l'inventario ma **non può scriverci**.

```bash
python -m occhio --check                    # dice se l'occhio è aperto e cosa manca
python -m occhio --serve                    # interfaccia su 127.0.0.1:8777
python -m occhio --serve --senza-visione    # solo la grafica: oggetti finti, banner a strisce
python -m occhio --foto scaffale.jpg        # legge una foto già scattata
python -m occhio --inventario
python3 falsificatori/h6_occhio_ripasso.py  # prova a smentire ciò che il sistema promette
```

Nessuna dipendenza nuova: `requests` e la libreria standard.

La regola che regge il disegno: **la lettura è cieca al registro.**
`visione.leggi()` non ha un parametro dove infilare l'inventario, ed è voluto.
Dare al modello la lista dei DVD già catalogati «per aiutarlo» produce un
sistema che li rilegge tutti con altissima confidenza anche inquadrando un
muro: il conteggio sale, l'accuratezza apparente pure, e non è entrato niente.
È il difetto di §4 con la faccia gentile di un'ottimizzazione. Il colore nasce
dopo, sul server, confrontando con il file — non dal modello.

L'ipotesi che questo modulo mette in gioco è **H6**: *ripassare non gonfia
l'inventario*. Ha un falsificatore eseguibile, e regge. Ciò che invece resta
**UNKNOWN** è il numero che conta davvero: quanti dorsi un modello legge
davvero, in penombra, di traverso. Serve una chiave di visione e una passata
vera. Tutto il resto — costi, taratura, verdetto su Emergent — sta in
[`OCCHIO.md`](OCCHIO.md).

## Licenza

_Da definire._
