# Artefatto — UmbraTheater

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

`dossier.html` è una pagina autoportante che presenta
[raffaellocantatelli/UmbraTheater](https://github.com/raffaellocantatelli/UmbraTheater),
la dashboard OSINT self-hosted. È stata pubblicata come Artifact il 2026-09-03:

<https://claude.ai/code/artifact/d3abf879-d428-4b62-adb8-101292481ad0>

## Cosa NON è

**UmbraTheater non entra nel canone R³∞.** È un progetto adiacente dello stesso
autore, con licenza MIT propria e nessuna dipendenza dal Protocollo. Questa
cartella esiste per tenere l'artefatto *fuori* dal canone pur versionandolo: il
codice di UmbraTheater resta nel suo repository, qui c'è solo la pagina che lo
racconta. Il vincolo è già scritto, come «non assorbire UmbraTheater nel canone
R³∞», nelle code di lavoro di un altro nodo in `memoria/` (cronaca, non stato:
vale perché è una scelta ragionevole, non perché qualcuno l'ha scritta).

La pagina **non contiene dati in diretta** e non può contenerne: un Artifact
pubblicato non può fare `fetch` verso host esterni. Il pannello interattivo
ricalcola gli inviluppi applicando le regole del backend a valori d'esempio, e
lo dichiara in testa al pannello stesso. Nessun numero della pagina è
presentato come una misura.

## Da dove viene ogni affermazione

**RECUPERATO** — letto in `raffaellocantatelli/umbratheater@2e4b591`
(clone del 2026-09-03), non in un documento che ne parla:

| Affermazione nella pagina | Fonte |
|---|---|
| Contratto dell'inviluppo, `total`/`returned` a `null` fuori da `ok` | `backend/app/feeds.py`, `_envelope()` |
| Tetti 250 / 180 / 400 | `backend/app/feeds.py`, `CAP_*` |
| Quattro stati (`ok`, `errore`, `senza_chiave`, `senza_propagatore`) | `backend/app/feeds.py` |
| Stringhe `coverage` dei quattro layer | `backend/app/feeds.py`, ogni chiamata a `_envelope` |
| SGP4 obbligatorio, niente posizioni inventate | `backend/app/feeds.py`, `satellites()` |
| Resa del pannello: `—`, `≥ N`, etichetta TETTO | `frontend/public/app.js`, `riga()` |
| Colori dei layer (`#ff5d5d`, `#7cffc4`, `#6cb6ff`, `#ffb347`) | `frontend/public/app.js` e `styles.css` |
| Architettura, porte 3000/8000, proxy `/api/` | `docker-compose.yml`, `frontend/nginx.conf` |
| Cache 45 s | `backend/app/settings.py`, `.env.example` |
| Tabella clean-room e dieci righe in comune | `ATTRIBUTIONS.md` |

## Un punto scoperto, trovato leggendo il codice

**RECUPERATO.** `ships_status()` in `backend/app/feeds.py` costruisce
l'inviluppo con `status = OK if attiva else SENZA_CHIAVE` e **senza `items`**.
Con `AIS_API_KEY` configurata lo stato è quindi `ok` e `returned` vale `0`,
perché il client websocket AISStream non è ancora collegato: il pannello stampa
uno zero che non significa «nessuna nave».

È lo stesso difetto che il resto del progetto elimina — l'unico posto dove il
contratto non si applica ancora da sé. La pagina lo dichiara nello stato
«con chiave» del layer navi invece di nasconderlo.

**IPOTESI** — un terzo stato (`in_attesa_di_client`, con `returned: null`)
chiuderebbe il caso. **Falsificabile così:** se dopo averlo introdotto esiste
ancora una configurazione in cui un layer senza fonte collegata stampa `0`,
l'ipotesi è falsa. Non è stata implementata qui: sta nel repository di
UmbraTheater, e la decisione è dell'autore.

## Rigenerare l'artefatto

`dossier.html` è un file singolo: nessuna dipendenza, nessun passo di build.
Si apre in un browser così com'è. Per ripubblicarlo come Artifact va passato
lo **stesso URL** qui sopra, altrimenti se ne crea uno nuovo.

La verifica clean-room riportata nella pagina va rifatta a ogni contributo che
tocchi il backend di UmbraTheater: se cambia, cambia anche la tabella qui.
