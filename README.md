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

## Licenza

_Da definire._
