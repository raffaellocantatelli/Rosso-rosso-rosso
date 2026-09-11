# Lavoro pronto per `claudioterzi/Claudio`

Correzioni e pagine nuove per il sito **claudio-ebon.vercel.app**, verificate
nel browser ma **non ancora applicate**: questa sessione non ha i permessi di
scrittura su quel repository, quindi il lavoro è depositato qui per non andare
perso insieme al container.

I file del sito vivono in `public/`.

---

## Come si applica, in quattro comandi (11/09/2026)

Dalla radice di **questa** repository, così che `..\Claudio-sito` finisca
accanto e `tools\` si trovi:

```bat
git clone https://github.com/claudioterzi/Claudio.git "..\Claudio-sito"
py tools\prepare_release.py "..\Claudio-sito" "..\Claudio-release"
py tools\publish.py "..\Claudio-release"                 :: ANTEPRIMA
py tools\publish.py "..\Claudio-release" --produzione    :: il sito vero
```

`prepare_release.py` non tocca il clone: ne fa una copia, ci applica le patch e
i file nuovi, e la dichiara pronta solo se cinque prove sul testo e i dieci
test del costo a terra passano. Se una cade non scrive `RELEASE.json`, e
`publish.py` senza quel file si rifiuta di pubblicare.

`publish.py` pubblica un'**anteprima** salvo che tu scriva `--produzione`, e in
quel caso si ferma e aspetta che tu digiti `pubblica`.

### Con anche l'Oracolo del Sovrano (11/09)

Il pacchetto `ORACOLO_SOVRANO_WEB_AUTORIZZATO` è una **seconda** consegna, con
strumenti suoi. Non sono stati riscritti: sanno cose che questa consegna non sa
— quale progetto Vercel è la destinazione, come fondere le route dentro
`vercel.json` senza sostituirlo alla cieca. Quindi la copia la fa il pacchetto,
e sopra ci va la consegna del 04/09:

```bat
py tools\prepare_release.py "..\Claudio-sito" "..\Claudio-release" ^
   --oracolo "..\ORACOLO_SOVRANO_WEB_AUTORIZZATO"
```

Prima di eseguire il codice del pacchetto ne vengono ricalcolate le 53
impronte SHA256: se una non torna, non si esegue niente.

**Due conflitti, dichiarati invece che risolti in silenzio:**

- `public/alpha.html` esiste in entrambe le consegne. **Vince l'Oracolo**,
  perché Claudio l'11/09 ha stabilito che Alpha usa le 74 Lame. Non è una
  versione più nuova dello stesso file: è un altro mazzo, e la riga viene
  stampata a ogni preparazione.
- `public/nav.js` — **un passaggio che sembrava eseguito e non faceva nulla.**
  Il pacchetto rinomina la voce di menu cercando `['index.html', 'Tarocchi']`
  con gli apici singoli, come è scritta nel `nav.js` oggi in produzione. Il
  `nav.js` nuovo di questa consegna la scrive con i **doppi** apici: la
  sostituzione non trova niente, non fallisce, e il menu resterebbe
  «Tarocchi». Nessuna delle due consegne poteva accorgersene da sola. La
  rinomina viene ora rifatta sul file nuovo e poi verificata.

**Ricontrollato qui, non letto nel suo rapporto (P5):** che `public/soglia.js`,
`soglia.html`, `oracolo.html` e `atelier.html` restino identici alla sorgente,
e che i vecchi mazzi spariscano dalla sola copia di rilascio. `fonte/` — il PDF
e il taccuino — non entra nel rilascio: il pacchetto copia soltanto `app/`.

**Per pubblicare si usano gli strumenti del pacchetto**, non `tools/publish.py`
di qui: i suoi conoscono il progetto Vercel autorizzato e si rifiutano di
pubblicare altrove.

**Non eseguito da nessuna sessione:** il `prepare_release.py` del pacchetto.
Il classificatore di sicurezza ha bloccato l'esecuzione di codice arrivato in
uno ZIP, e il blocco non è stato aggirato. Verificato leggendo: le 53 impronte
tornano, 46 prove Node e 13 Python passano, la fusione delle route rifiuta una
configurazione che non riconosce. Che la composizione delle due consegne
funzioni sul serio **si vede al primo comando sulla macchina di Claudio.**

Serve Vercel installato e collegato, una volta sola:

```bat
npm.cmd install --global vercel
vercel.cmd login
```

**Verificato l'11/09** eseguendo `prepare_release.py` sul clone vero
(`6a870d0`): le due patch si applicano ancora pulite, i quattro file entrano,
10/10 test passano, e `public/lettura.html`, `public/enzo.html` e
`tests/test_costi_terra.py` **non sono ancora nel sito**. La consegna del
04/09 è tuttora inapplicata: `alpha.html` in produzione chiama ancora due
volte l'API che risponde 404.

**Che la pubblicazione vada a buon fine è UNKNOWN da qui**: nessuna sessione ha
le credenziali Vercel, e non deve averle. Lo dice il comando sulla macchina di
Claudio.

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

## 2-bis. Il costo a terra — `patch/costo-terra-reale.patch`

Riguarda `flight_hunter/`, non il sito. È la correzione del numero su cui
poggia l'intera tesi dello strumento.

**Il problema.** `costi.py` stimava il posizionamento via terra con
`max(8 €, km × 0,09)`. Bruxelles–Charleroi sono ~50 km: la formula dà 4,50 €,
il minimo la porta a **8 €**. Ma quel collegamento è una navetta in regime di
monopolio, e il prezzo non segue i chilometri.

Verificato alla fonte il 10/08/2026: Flibco costa **13,90 €** prenotando in
anticipo e **~19 €** a tariffa standard.

Conseguenza sul verdetto dell'Oracolo per Manchester del 4 settembre:

| | prima | dopo |
|---|---|---|
| volo | 14,99 € | 14,99 € |
| terra | 8,00 € | 16,45 € |
| **totale** | **22,99 €** | **31,44 €** |

La tesi non ne esce indebolita: ne esce rafforzata. Lo scarto fra il prezzo
pubblicizzato e quello reale era **il doppio** di quanto lo strumento stesso
dichiarasse. L'unico modo di sbagliare, qui, era essere troppo prudenti.

**La correzione.** Una tabella `TRASFERIMENTI_NOTI` di prezzi verificati alla
fonte, con la data nel commento, che scavalca la formula chilometrica. Contiene
**solo `CRL`**, perché è l'unico che ho verificato davvero: Beauvais, Hahn e
Weeze sono lasciati come commento, da aggiungere dopo verifica. Una tabella
corta e vera vale più di una lunga e inventata.

Aggiunta anche `intervallo_terra()`, e il responso dell'Oracolo ora dichiara la
forbice invece di un numero secco:

> *«Si parte venerdì 4 settembre (via CRL), per **29–34€ secondo quando prenoti
> la navetta**.»*

Per gli aeroporti non censiti nulla cambia: resta il numero singolo, perché
fingere una forbice che non conosciamo sarebbe peggio che ammettere un punto
solo. L'API espone `totale_min` e `totale_max` accanto a `totale`.

### I primi test del progetto — `nuovi/tests/test_costi_terra.py`

Dieci test che bloccano le regressioni che contano: che la formula
chilometrica torni a mangiarsi i prezzi verificati, che il responso torni a
dichiarare un numero secco dove esiste una forbice, e che la correzione
continui ad **alzare** il prezzo invece di abbassarlo.

```bash
python -m pytest tests/test_costi_terra.py -q     # 10 passed
```

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

`TRASFERIMENTI_NOTI` contiene un solo aeroporto. Gli altri hub low cost —
Beauvais per Parigi, Hahn per Francoforte, Weeze — hanno lo stesso problema di
Charleroi e vanno verificati e aggiunti, ognuno con la sua data.

Anche `bagaglio_stiva = 30 €` e `margine_self_transfer = 15 €` sono costanti
mai verificate alla fonte. Il bagaglio Ryanair varia molto per rotta e
stagione: è il prossimo numero da controllare con lo stesso metodo.

I test coprono il costo a terra. Il resto del progetto non ne ha ancora.
