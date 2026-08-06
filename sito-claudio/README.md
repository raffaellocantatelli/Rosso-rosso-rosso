# Lavoro pronto per `claudioterzi/Claudio`

Correzioni e pagine nuove per il sito **claudio-ebon.vercel.app**, verificate
nel browser ma **non ancora applicate**: questa sessione non ha i permessi di
scrittura su quel repository, quindi il lavoro è depositato qui per non andare
perso insieme al container.

I file del sito vivono in `public/`.

---

## 1. File nuovi o rifatti — `nuovi/`

Si copiano dentro `public/` sovrascrivendo, oppure si creano da GitHub via
**Add file → Create new file**.

| File | Destinazione | Cosa fa |
|---|---|---|
| `nav.js` | `public/nav.js` | sostituisce l'esistente |
| `alpha.html` | `public/alpha.html` | sostituisce l'esistente |
| `lettura.html` | `public/lettura.html` | nuovo |
| `enzo.html` | `public/enzo.html` | nuovo |

`tarocchi_quantici_alpha.json` è la copia dei dati del Canone letta dalla
radice del repository, inclusa qui solo come riferimento per rigenerare
`alpha.html` con `genera_alpha.py`. **Non va copiata nel sito.**

### `nav.js` — la barra non andava a capo

I link erano concatenati con `.join("")`, senza spazi, e ognuno aveva
`white-space: nowrap`. Senza spazi il browser non trova alcun punto dove
spezzare la riga: la barra restava su una riga sola e usciva dallo schermo.

Su 390px erano raggiungibili **5 voci su 15** e la pagina scorreva di lato.
Sostituito con un contenitore flex che va a capo da solo, più due soglie di
rimpicciolimento. Su desktop resta una riga sola, identica a prima.

Verificato su 4 pagine a 320 / 390 / 768 / 1280px: **15/15 voci raggiungibili,
nessuno scorrimento orizzontale.**

### `alpha.html` — il Canone Alpha era morto

La pagina chiamava `GET /api/alpha` e `GET /api/alpha/collasso`: **entrambi
rispondono 404 in produzione.** `res.json()` riceveva una pagina di errore,
`init()` si interrompeva e la carta non veniva mai popolata. Era la pagina
linkata dalla home, quindi il primo click di ogni visitatore.

Rifatta senza backend: le 74 carte sono incorporate nella pagina e il collasso
(`carta[polarità][asse]`) è calcolato lato client. Non può più rompersi per
un'API assente.

I dati vengono da `tarocchi_quantici_alpha.json`, che era già nel repository:
74 carte, 8 cicli, 592 stati, nessun testo inventato. Aggiunti solo un pulsante
**Carta a caso** e la riga dell'interpretazione chiave, che nei dati c'era già
ma la pagina non mostrava.

Per rigenerarla dopo una modifica ai dati:

```bash
python genera_alpha.py     # legge tarocchi_quantici_alpha.json, riscrive alpha.html
```

### `lettura.html` e `enzo.html`

Due letture del Canone, autonome, senza script esterni. `enzo.html` non
include `soglia.js` di proposito: è pensata per essere aperta da un ospite
senza dover chiedere la parola.

Se le si vuole allineate alle altre stanze, basta aggiungere in cima al `body`:

```html
<script src="soglia.js"></script>
<script src="nav.js"></script>
```

---

## 2. Correzioni responsive — `patch/responsive-mobile.patch`

Quattro pagine sbordavano lateralmente su telefono. Sono modifiche di solo CSS,
nessun contenuto toccato.

```bash
git apply patch/responsive-mobile.patch
```

| Pagina | Prima (390px) | Causa |
|---|---|---|
| `opera.html` | **231px** fuori | `.lettore` in colonna con `align-items:flex-start`: sull'asse trasversale `.pagina` si dimensionava sul contenuto invece che sul contenitore. Aggiunto `width:100%`, come già aveva `.indice`. |
| `libro.html` | **46px** fuori | nessuna media query responsive, solo quella di stampa. Le tabelle non si restringono sotto la larghezza dei contenuti: ora scorrono dentro sé stesse. |
| `opuscolo.html` | **23px** fuori | le schede `.a6` sono larghe `105mm` ≈ 397px, formato di stampa. Solo a video e sotto i 430px si adattano; in stampa restano A6 esatto. |
| `valigia.html` | 53px fuori a 320px | `table.spec td:first-child` aveva `white-space:nowrap` e allargava la tabella. Ora sotto i 420px va a capo. |

---

## 3. Stato verificato

17 pagine, 4 larghezze, misurando `scrollWidth - clientWidth`:

- **390, 768, 1280px → 0px di sbordamento su tutte e 17.**
- 320px → tutte a 0 tranne `opera` (4px) e `libro` (3px), senza alcun elemento
  oltre il bordo: è arrotondamento sub-pixel, non un difetto di layout.

Le API vive e verificate: `/api/mazzo`, `/api/leggi`, `/api/viaggi/pianifica`,
`/api/flight/occasioni`, `/api/flight/oracolo`. Morte: `/api/alpha` e
`/api/alpha/collasso` — dopo questa modifica non servono più a nessuno.

## 4. Cosa resta aperto

`libro.html` non è rotto, ma pesa **1,15 MB** e su telefono è alto circa
387.000px, ossia più di 400 schermate. Non è un difetto di codice: è una scelta
di formato. Per renderlo leggibile servirebbe un indice con paginazione, come
quello che `opera.html` ha già. È il lavoro successivo.

Non esistono test automatici in nessuna pagina.
