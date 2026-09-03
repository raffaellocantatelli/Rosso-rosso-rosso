# occhio — inventario di oggetti reali attraverso la telecamera

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Cammini per casa con il telefono in mano. La telecamera guarda uno scaffale.
Quello che è già scritto nel registro si illumina di **verde** e puoi
ripassarci sopra quante volte vuoi senza che cambi niente; quello che è nuovo
compare in **azzurro** e viene scritto; quello che il modello non è sicuro di
aver letto lampeggia in **ambra** e ti viene chiesto. Intanto, di fianco, una
conversazione che può interrogare l'inventario ma non può scriverci.

```bash
python -m occhio --check                    # dice se l'occhio è aperto e cosa manca
python -m occhio --serve                    # apre l'interfaccia su 127.0.0.1:8777
python -m occhio --serve --senza-visione    # solo la grafica, oggetti finti, banner a strisce
python -m occhio --foto scaffale.jpg        # legge una foto già scattata (prova più economica)
python -m occhio --inventario               # cosa c'è nel registro
python -m occhio --esporta casa.csv
python3 falsificatori/h6_occhio_ripasso.py  # prova a smentire l'unica cosa che il sistema promette
```

Nessuna dipendenza nuova: `requests`, già nel progetto, e la libreria standard.
Niente FastAPI, niente Pillow, niente build. In questo ambiente `fastapi`,
`Pillow` e `dotenv` **non sono installati** (verificato il 03/09): un sistema
che per partire chiede prima un `pip install` è un sistema che non verrà provato.

---

## 1. Che cosa è verificato e che cosa no

| | |
|---|---|
| **RECUPERATO** | Il server parte, serve la pagina, risponde su `/api/fotogramma`, `/api/inventario`, `/api/conferma`, `/api/chat`, `/api/esporta.csv`. Provato in esecuzione il 03/09 su `127.0.0.1:8793`. |
| **RECUPERATO** | 30 prove passano (`python -m pytest tests/test_occhio.py`), senza chiavi e senza rete. |
| **RECUPERATO** | H6 regge sul falsificatore: due passate identiche non aggiungono voci, il riconoscimento sopravvive al riavvio, due oggetti diversi restano due. |
| **RECUPERATO** | L'interfaccia disegna i riquadri allineati agli oggetti, il velo verde, la spunta e il contatore `·2x`. Provata con una telecamera finta in Chromium — *la grafica*, non il riconoscimento. |
| **UNKNOWN** | **Quanto bene un modello legga davvero i dorsi in casa tua.** Nessuna chiave di visione è configurata qui, quindi nessun modello ha ancora guardato un oggetto vero. Questo è il numero che conta, e non ce l'ho. |
| **UNKNOWN** | Il costo per passata, in euro. Il numero di chiamate lo so (una per fotogramma); il prezzo per chiamata va letto sul listino del fornitore, non ricordato. |

La distinzione non è pedanteria. Un sistema del genere è facilissimo da far
sembrare funzionante e difficile da far funzionare, e la differenza sta tutta
nella riga UNKNOWN.

---

## 2. La regola che tiene in piedi tutto: la lettura è cieca al registro

`visione.leggi(immagine_b64, mime, cascata)` non ha un parametro dove infilare
l'inventario, e non è una svista.

Dare al modello la lista dei DVD già catalogati «per aiutarlo a riconoscerli»
è la cosa più naturale del mondo e produce un sistema che li rilegge tutti con
altissima confidenza — **anche inquadrando un muro.** Il conteggio salirebbe,
l'accuratezza apparente pure, e nessuna informazione nuova sarebbe entrata.

È il difetto di `CLAUDE.md` §4 nella sua forma più seducente: il sistema che
parla a sé stesso e registra l'eco come risposta. Qui avrebbe la faccia
gentile di un'ottimizzazione.

L'ordine è quindi rigido, e il codice lo rispetta in `server.py:_fotogramma`:

1. il modello guarda i pixel — non sa niente del registro;
2. il server confronta ciò che è stato letto con il file su disco;
3. **solo qui nasce il colore.** Verde significa «c'è una riga scritta».

La chat è l'eccezione controllata: legge l'inventario, perché serve a
interrogarlo, e **non può scriverci**. Se potesse, il sistema si detterebbe da
solo il proprio inventario — lo stesso loopback, con un'altra faccia.

---

## 3. Come si riconosce un oggetto già visto

Tre livelli, in ordine di forza. Nessuno dipende da cosa è successo in questa
sessione: dipendono solo dal file. Riavviare il server e ripassare sullo stesso
scaffale deve dare gli stessi colori, altrimenti il verde è un'impressione.

1. **Chiave testuale** — `tipo:titolo` normalizzato. `The Matrix`, `MATRIX, THE`
   e `il  matrix` danno tutti `dvd:matrix`. Toglie accenti, punteggiatura e
   articoli; **non tocca i numeri**, perché `Rocky 2` e `Rocky 3` sono due film.
2. **Impronta percettiva** — dHash a 64 bit del ritaglio, calcolato *nel
   browser* (i pixel sono già lì, e così il fotogramma non deve essere
   conservato da nessuna parte). Distanza di Hamming ≤ 10 → stesso oggetto
   fisico. Serve per il dorso illeggibile: senza, verrebbe richiesto in
   conferma a ogni fotogramma.
3. **Nessuno dei due** → `INCERTO`. Ambra, mai automatico. Un titolo di meno di
   tre caratteri utili non produce una chiave: meglio nessuna chiave che una
   debole, perché una debole fonde due oggetti diversi e il registro perde una
   voce **senza dirlo**.

Le impronte di un fotogramma vengono associate ai riquadri del successivo per
sovrapposizione (IoU ≥ 0,4): fra uno scatto e l'altro la mano si muove, e due
riquadri dello stesso oggetto non coincidono mai.

---

## 4. Che cosa finisce su disco

`output/inventario.jsonl`, append-only, una riga JSON per evento — §6 regola 3:
due passate non possono sovrascriversi. Lo stato corrente si ricostruisce
rileggendo il file, non è conservato a parte.

**I fotogrammi non vengono mai salvati**, né sul server né nel browser. Restano
in memoria per il tempo della chiamata e spariscono. Sul disco finiscono solo
tipo, titolo, impronta a 64 bit e orario. Un inventario di casa non ha bisogno
delle fotografie di casa, e questo repository è pubblico.

Il server ascolta su `127.0.0.1`. `--host 0.0.0.0` esiste e stampa un avviso:
non c'è autenticazione, e chi apre quella porta sta mettendo l'inventario di
casa propria su una rete.

---

## 5. Senza provider non si finge

Come in `sdq1` (§3): `--serve` **rifiuta di partire** se nessun modello di
visione è disponibile, invece di produrre un inventario che sembra letto.

```
L'OCCHIO È CHIUSO: nessun provider di visione disponibile.
Il server non parte, invece di mostrare un inventario che sembra letto.
```

Lo stub si ottiene solo con `--senza-visione`, marchia ogni risposta con
`stub: true`, fa comparire una fascia gialla a strisce in cima alla pagina e
**non scrive mai** nel registro. Provato: `test_lo_stub_non_scrive_mai`.

---

## 5-bis. Il modo a fotografie, e la mappa (aggiunto 03/09)

Meglio del video dal vivo, per tre motivi che non sono opinioni:

1. **Costa meno.** Il video spende una chiamata ogni 2,5 s qualunque cosa
   inquadri, muro compreso. Con le fotografie spendi una chiamata per foto,
   e le scegli tu. Con l'API a lotti, metà prezzo — sconto che il video **non
   può** avere, perché i lotti sono asincroni.
2. **Le foto sono migliori.** Ferme, a fuoco, con la luce giusta. Un dorso
   letto male è un titolo sbagliato nel registro per sempre.
3. **Non serve `https`.** Era l'ostacolo vero: `getUserMedia` fuori da
   `localhost` non parte. Con una cartella di foto il problema sparisce.

```bash
python -m occhio --cartella ~/foto            # legge tutto, salta ciò che ha già letto
python -m occhio --mappa                      # dove sta cosa, a schermo
python -m occhio --mappa mappa.html           # la stessa cosa, da aprire con due clic
```

Il luogo si dichiara con le cartelle, che è la cosa più vicina a nessuna
interfaccia:

```
foto/salotto/libreria-grande/ripiano-3/IMG_0021.jpg
     └ stanza  └ mobile      └ ripiano
```

Rieseguire la stessa cartella non ripaga le stesse letture: ogni fotografia
già letta è riconosciuta dal suo sha256 e saltata. È H6 applicato al
portafoglio.

### Perché la mappa NON è fatta con il GPS

**È la trappola di questo modulo, e ha la faccia di una buona idea.** Dentro
casa il telefono non vede i satelliti: fonde Wi-Fi e celle, e restituisce una
posizione con un errore che di solito è più grande della casa intera. Salotto
e camera da letto cadono nello stesso cerchio. Una mappa costruita così
**sembra un dato misurato ed è rumore** — §4 con un'interfaccia bellissima.

**Non chiedo di credermi.** Le fotografie dell'iPhone scrivono un campo
apposta, `GPSHPositioningError` (tag EXIF 0x001F), in cui il telefono dichiara
da solo di quanto può sbagliare. `occhio/luogo.py` lo legge — con un lettore
EXIF scritto sulla libreria standard, perché Pillow qui non è installato — e
**H7** lo mette alla prova sulle fotografie dell'autore:

```bash
mkdir -p ~/prova-gps/{salotto,cucina,camera}
# tre foto per stanza, nella cartella giusta
python3 falsificatori/h7_gps_stanze.py ~/prova-gps
```

Il falsificatore discrimina in entrambe le direzioni — verificato il 03/09 su
dati costruiti: stanze a 4 m con errore dichiarato 18,5 m → **H7 CADE**;
magazzini a 200 m con lo stesso errore → **H7 REGGE**. Un test che cade sempre
non proverebbe niente.

Il GPS resta letto e conservato accanto al suo errore, perché **fuori** serve
davvero: magazzini, cantine, sopralluoghi. Non decide mai una stanza, e
`test_il_gps_non_decide_mai_una_stanza` fallisce se qualcuno ci prova.

### E il LiDAR?

La parola cercata è **LiDAR**, e su iPhone/iPad Pro l'API si chiama
**RoomPlan** (Apple, da iOS 16). **RECUPERATO** dalle fonti in §7: usa lo
scanner LiDAR per produrre in 60-90 secondi una pianta 3D parametrica —
muri, porte, finestre, mobili — esportabile in USDZ.

È vero e funziona. Tre cose però vanno tenute dritte:

- **Dà la geometria, non l'identità.** RoomPlan sa che lì c'è «un mobile
  contenitore». Non legge nessun titolo. Sono due sistemi diversi che vanno
  uniti, non uno.
- **Serve un'app nativa Swift.** Non è raggiungibile da un browser: è
  esattamente il lavoro per cui un generatore di applicazioni avrebbe senso
  (§6), e l'unico motivo serio per usarne uno.
- **Per trovare un disco non serve.** «Salotto › libreria grande › ripiano 3»
  risponde alla domanda meglio di una pianta 3D. **Dove il LiDAR paga davvero
  è il mercato professionale** — perizie assicurative e successioni, dove il
  documento *è* la pianta con gli oggetti sopra. Cioè: non è una funzione per
  te, è una funzione per un cliente.

## 6. Vale la pena usare Emergent per costruire questo?

Hai chiesto due cose: se convenga usare **Emergent** e se il programma
funzionerebbe. Sono domande separate, e la seconda è più importante.

### Che cos'è Emergent

**RECUPERATO (fonti in fondo, lette il 03/09/2026).** Emergent (`emergent.sh`)
è una piattaforma di *vibe-coding* multi-agente: da una descrizione in
linguaggio naturale genera un'applicazione full-stack — front-end React,
back-end FastAPI — la testa, la fa girare e la pubblica. Il codice resta tuo.
Per applicazioni semplici si parla di 5-15 minuti, per le complesse 15-30.

**IPOTESI, da falsificare provandolo:** su questo progetto Emergent
arriverebbe in mezz'ora a una pagina con la telecamera accesa e dei riquadri
disegnati sopra. È esattamente il tipo di cosa per cui è costruito.

### Il punto: quella mezz'ora non è dove sta la difficoltà

Quella parte l'hai già. È in questa cartella, gira, ed è verificata da 30 prove
e da uno scatto. Mi ci sono volute poche ore, e non è la parte difficile.

**INFERITO, dalla struttura del problema.** La difficoltà di questo sistema sta
in quattro punti, e nessuno dei quattro si risolve generando più codice:

1. **L'identità degli oggetti.** Un inventario che cresce a ogni passata non
   misura gli oggetti, misura le passate. Non è un problema di codice: è la
   decisione su *quando due letture sono la stessa cosa*, e va tarata sui tuoi
   scaffali. Un generatore di applicazioni ti dà la scelta di default —
   confrontare le stringhe — e con quella `MATRIX, THE` e `The Matrix` sono
   due DVD.
2. **La soglia di confidenza.** Se la tieni bassa, il registro si riempie di
   titoli plausibili che nessuno ha letto — ed è **peggio di un registro
   vuoto**, perché sembra pieno. Se la tieni alta, ti chiede conferma di
   continuo. La taratura richiede una passata vera, con i tuoi oggetti, contata
   a mano.
3. **Il costo.** Ogni fotogramma è una chiamata a un modello di visione.
   **RECUPERATO dal codice:** al ritmo di default, 2,5 s, dieci minuti di
   cammino sono **240 chiamate**. Un'ora sono 1.440. Il prezzo unitario è
   **UNKNOWN da qui** — va letto sul listino del fornitore — ma l'ordine di
   grandezza del *numero* basta a capire che la variabile da governare è il
   ritmo, non la grafica. Un'applicazione generata in mezz'ora quel ritmo lo
   mette a un fotogramma al secondo, perché è più bello da vedere.
4. **Quanto legge davvero.** Un dorso di DVD di traverso, in penombra, a un
   metro, con il riflesso della plastica. Nessuna piattaforma lo migliora:
   dipende dal modello di visione e dalla luce della tua stanza.

### Verdetto

**Non ti serve Emergent per questo progetto, e non per snobismo: perché la
parte che Emergent fa bene è già fatta e verificata, e la parte che resta è
esattamente quella che nessun generatore può fare per te** — tarare le soglie
camminando per casa e contando a mano quanti oggetti ha preso e quanti ha
saltato.

C'è però un motivo per cui potrebbe valerne la pena, e non è tecnico:
**l'app sul telefono.** Questo `occhio` gira in un browser, e per avere la
telecamera fuori da `localhost` serve `https` — cioè un certificato, o un
tunnel, o l'applicazione installata sul telefono. Se il fastidio di aprire
`https` ti impedisce di provarlo, allora il generatore che ti sputa fuori
un'app installabile ti sta risolvendo il problema vero, che è **provarlo**.
In quel caso il modo giusto di usarlo non è «costruiscimi un inventario con la
telecamera»: è dargli `occhio/inventario.py` e `occhio/visione.py` come sono —
la parte pensata — e chiedergli soltanto l'involucro nativo attorno.

**E funzionerebbe?** La risposta onesta è che *questo* funziona già, senza il
pezzo che conta: nessun modello ha ancora guardato un oggetto vero, perché in
questa sessione non c'è nessuna chiave di visione. È la stessa cosa che blocca
il daily di `sdq1` da giorni (`PROSSIMO_PASSO.md` §1), ed è la stessa chiave.
Il momento in cui `python -m occhio --check` stampa **L'OCCHIO È APERTO** è il
momento in cui questa domanda smette di essere un'opinione.

### Il prossimo esperimento verificabile

Non è «costruire di più». È questo, e costa venti minuti:

```bash
# 1. una sola foto, già scattata, di uno scaffale vero
python -m occhio --foto ~/scaffale.jpg --solo-lettura

# 2. conta a mano quanti oggetti ci sono nella foto. Scrivi i due numeri.
#    letti / presenti = la sola misura che vale.
```

Se legge 12 dorsi su 20, il sistema è utile e la soglia va tarata. Se ne legge
3, la telecamera in movimento non ha senso e il problema è la fotografia, non
il programma. In entrambi i casi avrai un numero, e sarà tuo — non mio.

---

## 7. Fonti sulla parte non verificabile da qui

Su Emergent non ho eseguito niente: ho letto. Queste sono le pagine, e vanno
lette sapendo che due delle quattro sono scritte da Emergent stessa.

- [Emergent — Build Apps with AI](https://app.emergent.sh/) *(fonte dell'azienda)*
- [5 Best AI App Builders in 2026 (Tested on Real Builds)](https://emergent.sh/learn/best-ai-app-builders) *(fonte dell'azienda: si autoclassifica)*
- [Emergent Review 2026: AI App Builder Tested Hands-On — HostAdvice](https://hostadvice.com/ai-app-builders/emergent-review/)
- [I Built an App with Emergent AI to Review it for PMs & Designers — Banani](https://www.banani.co/blog/emergent-ai-review)

Su RoomPlan e il LiDAR (§5-bis), letto il 03/09/2026:

- [Create parametric 3D room scans with RoomPlan — WWDC22, Apple Developer](https://developer.apple.com/videos/play/wwdc2022/10127/) *(fonte del produttore)*
- [Introducing RoomPlan — Apple Developer](https://developer.apple.com/augmented-reality/roomplan) *(fonte del produttore)*
- [3D Parametric Room Representation with RoomPlan — Apple Machine Learning Research](https://machinelearning.apple.com/research/roomplan) *(fonte del produttore)*
- [iOS 16 'RoomPlan' API creates 3D floor plans using LiDAR — 9to5Mac](https://9to5mac.com/2022/06/15/ios-16-roomplan-api-3d-floor-plans/)

Per P5 una recensione non conferma un'affermazione dell'azienda che recensisce
se non aggiunge un'esecuzione propria. Le ultime due dichiarano di averlo
usato; non l'ho verificato.
