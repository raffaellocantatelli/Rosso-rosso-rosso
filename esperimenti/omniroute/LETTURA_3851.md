# OmniRoute 3.8.51 — cosa regge e cosa no, prima di eseguire

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Verifiche del 2026-09-21. Fonte: il codice, letto nel checkout
`diegosouzapw/OmniRoute` ramo `release/v3.8.51`, commit
`7a921299c5b4c28dcf837f56a1c312b61414a646`, e l'API pubblica di Docker Hub.
Non un documento che ne parla.

---

## 1. Quello che il nodo precedente aveva detto, e che regge

**RECUPERATO.** `modelVisibilityDenylist` esiste davvero in 3.8.51:

| Dove | Cosa |
|---|---|
| `src/shared/validation/settingsSchemas.ts:157` | `z.array(z.string().max(200)).max(500).optional()` |
| `src/shared/utils/modelExposureList.ts` | `isModelExposureAllowed()`, il predicato unico |
| `src/app/api/v1/models/catalog.ts` | primo punto di strozzatura: la vetrina `/v1/models` |
| `open-sse/services/autoCombo/modelExposureFilter.ts` | secondo: `filterModelExposureCandidates()` sul pool di `auto/*` |
| `docs/routing/MODEL_EXPOSURE_LIST.md` | la documentazione, `version: 3.8.51` |

**RECUPERATO.** Il ramo `release/v3.8.50` **non contiene** ne'
`modelExposureList.ts` ne' `modelExposureFilter.ts` (`git ls-tree` su
`FETCH_HEAD` di quel ramo). La funzione e' nuova davvero: Candidate A ha una
ragione di esistere, e Candidate B ha qualcosa di concreto da portare
indietro — due file piu' i punti di chiamata.

**RECUPERATO.** `/v1/chat/completions` e' servito: `next.config.mjs` riscrive
`/v1/:path*` su `/api/v1/:path*`. `PATCH /api/settings` esiste
(`src/app/api/settings/route.ts:278`) ed e' autenticato via
`requireManagementAuth`.

---

## 2. Quello che non regge, e che avrebbe fatto fallire l'esecuzione

**RECUPERATO — il tag Docker non esiste.** Su `hub.docker.com` il repository
`diegosouzapw/omniroute` ha 290 tag. `3.8.51` risponde **404**. L'ultimo della
famiglia e' `3.8.50` (e `3.8.50-web`), e `latest` punta allo stesso push del
2026-08-27T04:23Z. Quindi:

```
docker pull diegosouzapw/omniroute:3.8.51    # fallisce: manifest unknown
```

Candidate A **non si ottiene tirando un'immagine**. Si ottiene costruendola dal
sorgente del ramo `release/v3.8.51` — che e' quello che fa `candidate_a.sh`.

**RECUPERATO — la porta era sbagliata.** `Dockerfile` riga 216: `ENV PORT=20128`;
riga 270: `EXPOSE 20128`. La mappatura `-p 8081:3000` con `OMNIROUTE_PORT=3000`
non avrebbe trovato nessuno in ascolto: `src/lib/runtime/ports.ts` usa
`OMNIROUTE_PORT` come porta *canonica*, ma Next ascolta su `PORT`, che
nell'immagine resta 20128. Lo script corretto non tocca le porte dentro il
container e rimappa solo fuori (`-p 28151:20128`).

**INFERITO — la credenziale non e' un generico bearer di management.**
`requireManagementAuth` accetta: sessione dashboard, richiesta loopback fidata,
token CLI locale, token `oma_...`, oppure una API key con scope `manage`. Un
`$MANAGEMENT_TOKEN` inventato non e' una di queste. Su un container appena nato
puo' anche non servire nulla: lo script prova senza e lo registra.

---

## 3. Il limite che cambia cosa compri, e che nessuno dei due candidati toglie

**RECUPERATO** (`docs/routing/MODEL_EXPOSURE_LIST.md`, sezione *What is NOT
filtered*, e il commento in testa a `modelExposureList.ts`):

> un id di modello inviato **esplicitamente** non viene mai bloccato al
> dispatch — si filtra solo l'advertisement e l'appartenenza al candidate pool.

La denylist toglie i modelli **dalla vetrina** e **dal sorteggio di `auto/*`**.
Non impedisce a un client che scrive il nome per esteso di usarli. Se lo scopo
era smettere di *pagarli* o di *toccarli*, ne' A ne' B lo ottengono: e' il
disegno di upstream, non un difetto dell'uno o dell'altro. Il criterio E1 dello
script misura esattamente questo e lo stampa sempre.

**UNKNOWN — le cinque voci proposte colpiscono qualcosa?**
`isModelExposureAllowed` confronta la voce con `[modelId, provider/modelId]`:
match esatto (case-sensitive), poi glob `*`/`?` (case-insensitive, e `*`
attraversa le barre). Se sulla tua istanza il catalogo espone
`anthropic/claude-opus-5` sotto un provider diverso da `kilo-gateway`, la voce
**non da' errore e non fa niente**. E' il modo silenzioso in cui questa
modifica sembra funzionare senza funzionare — per questo il criterio A3 boccia
una denylist che non colpisce nessun id reale.

---

## 4. Come si esegue

```bash
git clone --branch release/v3.8.51 https://github.com/diegosouzapw/OmniRoute ./OmniRoute
OMNI_MGMT="<token manage>" OMNI_KEY="<chiave effimera>" \
  bash esperimenti/omniroute/candidate_a.sh
python3 esperimenti/omniroute/falsificatore_delta.py ./delta-3851-a
```

Il verdetto e' un codice di uscita: **0 = ADOPT A**, **1 = REJECT A**,
**2 = UNKNOWN** (gli artefatti non bastano — e allora non c'e' verdetto, non
c'e' un verdetto prudente).

I sei criteri sono dichiarati dentro `falsificatore_delta.py` **prima** di
guardare i dati, e ognuno ha in `tests/test_falsificatore_omniroute.py` un caso
che lo fa fallire da solo: un verificatore che dice sempre PASS e' il difetto
di `CLAUDE.md` §4 dentro lo strumento fatto per impedirlo — al registro delle
ipotesi e' gia' successo.

**RECUPERATO.** `python3 -m pytest tests/test_falsificatore_omniroute.py` →
11 passati, il 2026-09-21, in questa sessione.

---

## 5. Cosa non e' stato fatto qui, e perche'

**Candidate A non e' stato eseguito.** Questa sessione gira in un container
senza demone Docker (`docker info` → `no such file or directory` su
`/var/run/docker.sock`): non c'e' niente da avviare e nessun DELTA da misurare.
Lo dico invece di produrre numeri: e' la regola 2 di `CLAUDE.md` §2, e in questo
progetto e' gia' stata violata una volta da un altro modello.

Quello che si poteva verificare da qui — che la funzione esista, che sia nuova
in 3.8.51, che l'immagine non esista, che la porta sia 20128, che il dispatch
esplicito non venga filtrato — e' stato verificato alla fonte ed e' sopra.
