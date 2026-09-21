# OmniRoute 3.8.51 — quello che regge, quello che no, e cosa e' stato misurato

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Verifiche del 2026-09-21. Fonti: il codice del ramo `release/v3.8.51`
(commit `7a921299c5b4c28dcf837f56a1c312b61414a646`), l'API di Docker Hub, e
**l'esecuzione dell'immagine 3.8.50 in un container vero** in questa sessione.
Non un documento che ne parla.

---

## 1. La funzione esiste, ed e' nuova davvero

**RECUPERATO.** `modelVisibilityDenylist` in 3.8.51:

| Dove | Cosa |
|---|---|
| `src/shared/validation/settingsSchemas.ts:157` | dentro `updateSettingsSchema`: il PATCH la accetta |
| `src/shared/utils/modelExposureList.ts` | `isModelExposureAllowed()`, il predicato unico |
| `src/app/api/v1/models/catalog.ts:372` | primo punto di strozzatura: la vetrina `/v1/models` |
| `open-sse/services/autoCombo/modelExposureFilter.ts` | secondo: il pool di `auto/*` |
| `docs/routing/MODEL_EXPOSURE_LIST.md` | documentazione, `version: 3.8.51` |

**RECUPERATO.** Il ramo `release/v3.8.50` **non contiene** quei due file
(`git ls-tree` su `FETCH_HEAD`). Candidate B ha un bersaglio preciso.

---

## 2. Quello che non regge — e come lo so

**RECUPERATO per esecuzione.** `docker pull diegosouzapw/omniroute:3.8.51` →
`not found`. Non e' una deduzione dall'API di Docker Hub: il demone ha chiesto
e si e' sentito dire di no. L'ultimo tag della famiglia e' `3.8.50`, e `latest`
punta allo stesso push del 2026-08-27.

**RECUPERATO.** Nel repository **non esiste il tag `v3.8.51`**: `git ls-remote
--tags` restituisce `v3.8.50` e basta. 3.8.51 e' un ramo di lavoro, non una
release. Nessun tag, nessuna immagine.

**RECUPERATO.** `Dockerfile` riga 216 `ENV PORT=20128`, riga 270 `EXPOSE 20128`.
Una mappatura `-p 8081:3000` con `OMNIROUTE_PORT=3000` non trova nessuno in
ascolto: `src/lib/runtime/ports.ts` usa `OMNIROUTE_PORT` come porta *canonica*,
ma Next ascolta su `PORT`, che nell'immagine resta 20128.

**RECUPERATO per esecuzione.** Senza sessione **ogni** chiamata e' 401, comprese
`/v1/models` e `/v1/chat/completions`. L'immagine parte con la password nota
`CHANGEME` e la rifiuta da tutto cio' che non e' loopback vero. La strada che
funziona e' quella che usa lo script: `INITIAL_PASSWORD` al `docker run`, poi
`POST /api/auth/login`, poi il cookie su tutte le chiamate. Un
`Authorization: Bearer <token di management>` inventato non e' nessuna delle
credenziali che `requireManagementAuth` accetta.

---

## 3. Il fatto che vale piu' di tutti gli altri

**RECUPERATO per esecuzione, su `diegosouzapw/omniroute:3.8.50`:**

```
PATCH /api/settings  {"modelVisibilityDenylist":[...]}   ->  HTTP 200
GET   /api/settings                                      ->  la chiave NON c'e'
```

Su 3.8.50 il PATCH **risponde 200 e butta via la chiave in silenzio.** Nessun
errore, nessun avviso. Un operatore la applica, vede 200, e non e' successo
niente. Per questo il criterio A2 guarda lo **stato riletto** e non il codice di
risposta: fidarsi del 200 qui e' esattamente non misurare.

---

## 4. Le tue cinque voci: quante funzionano

**RECUPERATO.** `catalog.ts:1093` chiama
`shouldHideByExposure(canonicalProviderId, model.id)` dove `model.id` e' l'id
**interno** del modello — l'id *stampato* nel catalogo (`aliasId`) si costruisce
a parte. Il predicato confronta quindi `[model.id, canonico/model.id]`, mai la
stringa che vedi in `/v1/models`.

Misurato sul catalogo reale di 3.8.50 (315 modelli):

| Id stampato | `owned_by` |
|---|---|
| `oc/big-pickle` | `opencode` |
| `felo/felo-chat` | `felo-web` |
| `no-think/dva/claude-opus-5-max` | `devin-cli-agentic` |

Quindi **copiare l'id che il catalogo ti mostra non funziona**: `oc/big-pickle`
non corrispondera' mai, perche' il predicato vede `big-pickle` sotto il provider
canonico `opencode`. Va scritto `opencode/big-pickle`.

**RECUPERATO.** `felo` e `felo-web` sono in `RUNTIME_RETIRED_PROVIDER_IDS`
(`src/shared/constants/providerRetirement.ts`) **in 3.8.51**: provider ritirato,
410 `PROVIDER_RETIRED`. Su 3.8.50 i modelli `felo/*` sono ancora in vetrina; su
3.8.51 non c'e' niente da nascondere.

Delle cinque voci proposte, **una sola e' scritta nella forma che il predicato
puo' vedere** (`kilo-gateway/anthropic/claude-opus-5`, che diventa
`anthropic/claude-opus-5` sotto `kilo-gateway`). Le altre quattro: due su un
provider ritirato, una in forma alias, una duplicata.

**Ma questo resta una lettura del codice.** Lo strumento non si fida nemmeno di
questa: applica **una voce per volta** e guarda che cosa sparisce davvero.

---

## 5. Il limite che nessuno dei due candidati toglie

**RECUPERATO** (`docs/routing/MODEL_EXPOSURE_LIST.md`, *What is NOT filtered*):
un id inviato **esplicitamente** non viene mai bloccato al dispatch. La denylist
toglie dalla vetrina e dal sorteggio di `auto/*`. Se lo scopo era smettere di
*usare* quei modelli, ne' A ne' B lo ottengono: e' il disegno di upstream.

---

## 6. Come si esegue

```bash
git clone --branch release/v3.8.51 https://github.com/diegosouzapw/OmniRoute ./OmniRoute
bash esperimenti/omniroute/candidate_a.sh                    # costruisce e misura
python3 esperimenti/omniroute/falsificatore_delta.py ./delta-3851-a
```

Per misurare la baseline con l'immagine pubblicata:

```bash
OMNI_IMAGE=diegosouzapw/omniroute:3.8.50 OMNI_PORT=28150 \
  OMNI_NAME=omniroute-3850-baseline DELTA_DIR=./delta-3850 \
  bash esperimenti/omniroute/candidate_a.sh
```

Verdetto = codice di uscita: **0 ADOPT A**, **1 REJECT A**, **2 UNKNOWN**
(artefatti insufficienti, o un criterio non misurabile in questo ambiente).
UNKNOWN non e' una bocciatura gentile: e' l'assenza di misura.

I sei criteri sono dichiarati dentro `falsificatore_delta.py` **prima** di
guardare i dati, e ognuno ha in `tests/test_falsificatore_omniroute.py` un caso
che lo fa fallire da solo: un verificatore che dice sempre PASS e' il difetto di
`CLAUDE.md` §4 dentro lo strumento fatto per impedirlo.

---

## 7. Stato della build di Candidate A

**RECUPERATO.** Il ramo `release/v3.8.51` **non si costruisce cosi' com'e'** in
questo ambiente, e i due tentativi falliscono in punti diversi:

- con Turbopack (il default del Dockerfile): `Module not found: Can't resolve
  'net' / 'tls' / 'readline'` — `playwright-core` finisce nel bundle
  *Client Component Browser* passando per `browserPool.ts` →
  `tokenHealthCheck.ts` → `src/lib/db/settings.ts` →
  `dashboard/combos/page.tsx`;
- con Webpack (`OMNIROUTE_USE_TURBOPACK=0`): heap esaurito a 6 GB.

**IPOTESI (falsificabile).** Non esiste un'immagine 3.8.51 perche' quel ramo,
a questo commit, non produce un'immagine. Si falsifica in un modo solo:
pubblicando o costruendo `3.8.51` da quel commit e vedendolo riuscire. Il
tentativo con heap da 11 GB e' in corso; l'esito va scritto qui, qualunque sia.

**Nota di ambiente, non una modifica a OmniRoute.** La build usa
`Dockerfile.ccr`, identico a `Dockerfile` piu' la CA del proxy di sessione
(senza, npm muore con `SELF_SIGNED_CERT_IN_CHAIN`). Si aggiunge una CA; nessuna
verifica viene disattivata.
