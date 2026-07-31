# R³∞ — Knowledge Redundancy System

> "La conoscenza che sopravvive a chi la crea è l'unica vera conoscenza."

R³∞ è un sistema minimale e auto-riparante di ridondanza documentale. Carica un file una volta — sopravvive alla perdita di un singolo nodo, con verifica di integrità e recupero automatici. Nessuna blockchain. Nessun vendor cloud. Nessun single point of failure.

**Stack**: Python 3.10+ · FastAPI · License: R³∞ KRL v1.0

## Perché

Ogni documento a cui tieni vive in un posto solo. Un guasto disco, la chiusura di un'azienda, una decisione di giurisdizione — e sparisce.

R³∞ risponde a una domanda semplice: qual è il sistema minimo necessario per garantire che un documento sopravviva?

La risposta: tre nodi indipendenti, content addressing SHA-256, sync bidirezionale, verifica di integrità oraria.

## Architettura

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   NODE A     │◄───►│   NODE B     │◄───►│   ARCHIVE    │
│  (Primary)   │     │ (Secondary)  │     │(Independent) │
└──────────────┘     └──────────────┘     └──────────────┘
      ▲                     ▲                     ▲
      └─────────────────────┴─────────────────────┘
             Sync bidirezionale (5 min)
             Verifica integrità (1 ora)
             Riparazione automatica
```

Ogni nodo esegue lo stesso `node.py` — nessun master, nessun servizio di coordinamento, nessuno stato condiviso oltre ai documenti stessi.

## Come funziona

| Step | Cosa succede |
|---|---|
| Upload | `POST /documents` → file salvato su disco, ID = SHA-256 del contenuto, firma Ed25519 registrata in SQLite |
| Sync | ogni `R3_SYNC_INTERVAL` secondi (default 5 min): confronta le liste di hash tra nodi, tira ciò che manca, spinge ciò che manca al peer |
| Verifica | ogni `R3_INTEGRITY_INTERVAL` secondi (default 1 ora): ricalcola lo SHA-256 di ogni file su disco, confronta col DB — ogni discrepanza avvia il pull dal peer |
| Recupero | file corrotto o mancante → ripristinato automaticamente dal primo peer sano trovato |

I documenti sono content-addressed: l'ID è l'hash SHA-256. Non puoi avere un documento con un dato ID che non sia esattamente quel contenuto.

## Quickstart (Docker — 3 nodi in 60 secondi)

```bash
docker compose -f r3/docker-compose.yml up -d
```

Tre nodi in esecuzione sulle porte 8001 (A), 8002 (B), 8003 (Archive).

```bash
# Carica un documento
curl -X POST http://localhost:8001/documents \
  -H "Authorization: Bearer changeme" \
  -F "file=@myfile.txt"
# → {"id": "sha256...", "signature": "ed25519...", "size": 1234}

# Verifica che sia replicato (dopo il sync)
curl -H "Authorization: Bearer changeme" \
  http://localhost:8002/sync/hashes

# Sync manuale
R3_LOCAL_URL=http://localhost:8001 \
R3_PEERS=http://localhost:8002,http://localhost:8003 \
R3_API_TOKEN=changeme \
python r3/sync.py
```

## Quickstart (senza Docker)

```bash
pip install -r requirements.txt

# Nodo A
R3_NODE_ID=node-a R3_API_TOKEN=secret R3_DATA_DIR=data/a \
  uvicorn r3.node:app --port 8001

# Nodo B (altra macchina o terminale)
R3_NODE_ID=node-b R3_API_TOKEN=secret R3_DATA_DIR=data/b \
R3_PEERS=http://localhost:8001 \
  uvicorn r3.node:app --port 8002
```

## API

| Metodo | Endpoint | Descrizione |
|---|---|---|
| POST | `/documents` | Carica un documento |
| GET | `/documents/{id}` | Scarica un documento |
| GET | `/documents/{id}/info` | Metadati |
| GET | `/sync/hashes` | Lista hash per il confronto di sync |
| POST | `/sync/receive` | Riceve un documento da un peer |
| GET | `/status` | Stato del nodo + verify key Ed25519 |
| GET | `/health` | Health check (nessuna auth) |

Tutti gli endpoint tranne `/health` richiedono `Authorization: Bearer <token>`.

## Sicurezza

- **Integrità**: ogni documento ha ID = SHA-256(contenuto). La verifica è implicita.
- **Autenticità**: ogni nodo firma i documenti con una chiave Ed25519 persistente (PyNaCl). Chiave pubblica esposta via `GET /status`.
- **Auth**: token Bearer statico per deployment. Ruota via variabile d'ambiente `R3_API_TOKEN`.
- **Audit**: tabella `audit_log` append-only in SQLite. Ogni upload, sync ed evento di integrità viene registrato.

## Criteri di successo (MVP)

Il sistema è considerato funzionante se:

- un documento caricato su A è presente su B e Archive entro 10 minuti
- dopo 7 giorni, tutti i documenti hanno hash validi su tutti i nodi
- spegnendo A: B resta consultabile e riceve comunque gli update via `sync.py --loop`
- A offline per 1 ora, poi riavviato: si risincronizza senza perdita di dati
- file corrotto manualmente su A: rilevato e ripristinato da B entro 1 ora

## Cosa NON è

R³∞ è deliberatamente minimale. Non include:

- ❌ Blockchain / token
- ❌ Steganografia o anonimizzazione
- ❌ Dead man switch
- ❌ Mesh P2P
- ❌ GUI
- ❌ Auto-deploy su cloud provider

Queste sono funzionalità per dopo. Il nucleo deve funzionare prima.

## Configurazione

| Variabile | Default | Descrizione |
|---|---|---|
| `R3_NODE_ID` | `node-a` | Identificatore del nodo |
| `R3_API_TOKEN` | `changeme` | Token di autenticazione (cambialo) |
| `R3_DATA_DIR` | `data` | Directory di storage |
| `R3_PEERS` | (vuoto) | URL dei peer separati da virgola |
| `R3_SYNC_INTERVAL` | `300` | Intervallo di sync (secondi) |
| `R3_INTEGRITY_INTERVAL` | `3600` | Intervallo di verifica integrità (secondi) |

## Stack

- Python 3.10+ — FastAPI, uvicorn, httpx, PyNaCl
- Storage — file system + SQLite (zero dipendenze esterne)
- Docker — opzionale ma consigliato per il setup multi-nodo

## Licenza

R³∞ Knowledge Resilience License v1.0

Usalo, forkalo, deployalo. Mantieni la ridondanza (minimo 3 nodi). Non rimuovere i meccanismi di verifica. Condividi i miglioramenti di sicurezza.

## Autore

Claudio Terzi — Bruxelles · Parte del progetto SDQ-1.
