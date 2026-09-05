# Prossimo passo — consegna del 2026-09-05, 20:10 UTC

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Questo file ha un nome fisso e viene **riscritto**, non accumulato. È la
differenza deliberata rispetto ai 44 `R3_WORK_QUEUE_*.yaml` in `memoria/`:
uno stato si sovrascrive, una cronaca si accumula. Qui c'è lo stato.

Se sei un nodo che apre questo repository: leggi `CLAUDE.md`, poi questo.
Ogni riga qui sotto è verificabile con un comando. Non credere a nessuna.

---

## 0. Che cos'è il prodotto, e cosa gli sta intorno (05/09)

**Detto dall'autore, e va rispettato:** *«Il prodotto serve per fare
inventario. Al limite può servire a una persona che, se vuole vedere un film,
sa che c'è. È questione di qualità dell'informazione, non di controllo.»*

Ha ragione, e costa dirlo: **tre giorni di costruzione stanno sopra un numero
che nessuno ha mai misurato.** Il mercato, i crediti, i tre generi, la
consegna controfirmata — tutto assume che la lettura funzioni. Se la lettura è
mediocre, niente di tutto quello conta.

Quindi, per chiunque apra questo repository dopo:

| | |
|---|---|
| **Il centro** | leggere bene, scrivere bene, e rispondere bene a «cosa c'è» e «c'è X?». `occhio/inventario.py`, `occhio/visione.py`, `occhio/voce.py` |
| **Il contorno utile** | dove sta una cosa: `luogo.py`, `planimetria.py`, la console |
| **Il contorno che serve solo agli affitti brevi** | `consegna.py` (controfirma), `portavia.py` (i tre banchi), `crediti.py` |

Il contorno **non va cancellato**: è scritto, provato e non costa niente
lasciarlo lì. Va tolto dal centro. Se il tempo è poco, si lavora sulla prima
riga e basta.

**La differenza che regge tutto:** un inventario è *controllo* quando serve a
dimostrare che manca qualcosa; è *informazione* quando serve a sapere cosa
c'è. La seconda è più utile e più difficile — e la controfirma esiste solo
perché senza di essa nessuno crederebbe alla prima.

**Da oggi c'è un comando che misura la metà rispondibile senza chiave:**

```bash
python -m occhio --qualita
```

Dice quante voci non hanno nessuna debolezza, quali debolezze hanno le altre
(senza luogo, lette una volta sola, confidenza bassa, titolo troppo corto,
fuse, senza fotografia) e **cosa si fa per togliere ciascuna**. Guarda il
registro e basta — lo dichiara stampandolo, perché un numero che sale senza
che nulla entri dall'esterno è §4.

**L'altra metà — quanti oggetti VERI finiscono scritti — resta il numero che
manca a tutto il progetto.** Non lo dà nessun comando: si fotografa uno
scaffale e si contano a mano gli oggetti che ci sono. Serve la chiave di §1.

## 1. L'unica cosa che blocca tutto

**RECUPERATO (run #35, 02/09 23:19 UTC).** La Action non vede nessun secret:

```
GOOGLE_API_KEY presente:    false
GEMINI_API_KEY presente:    false
ANTHROPIC_API_KEY presente: false
DEEPSEEK_API_KEY presente:  false
```

Claudio ha creato un secret stasera, ma non è arrivato dove la Action lo
legge. Quattro posti che si somigliano, in ordine di probabilità:

1. **un'altra repository** — l'account ne ha diverse (`protocollo-rosso-bot`,
   `R3-privato`, `Claudioterzi`). Il secret vale solo per la repo che lo ospita;
2. **Environment secret** invece di *Repository secret* — stessa pagina, più in
   basso; non arriva al job perché il workflow non dichiara un environment;
3. **tab Codespaces o Dependabot** — pagine quasi identiche a quella di Actions;
4. **Variable invece di Secret** — schede accanto.

Deve comparire sotto «Repository secrets» qui:
`https://github.com/raffaellocantatelli/Rosso-rosso-rosso/settings/secrets/actions`

**Non serve una chiave nuova.** Se quella di stasera è stata rigenerata, va
bene qualunque chiave Gemini valida — o DeepSeek, o Anthropic: la cascata
prende la prima disponibile.

## 1-bis. Aggiunto il 03/09: `occhio` — il primo modulo che guarda fuori

**RECUPERATO.** C'è un modulo nuovo, `occhio/`, chiesto dall'autore: si accende
la telecamera, si cammina per casa, e ciò che è già catalogato si illumina di
verde mentre ciò che è nuovo viene scritto. Gira, ha 30 prove che passano senza
chiavi, e non aggiunge nessuna dipendenza (`requests` + libreria standard —
`fastapi`, `Pillow` e `dotenv` **non sono installati** in questo ambiente, e un
sistema che chiede un `pip install` per partire non verrà provato).

Perché riguarda H2 e non è un diversivo: è il primo pezzo di questo progetto
che registra qualcosa che **esiste indipendentemente dal progetto** — oggetti
in un armadio, controllabili da chiunque apra quell'armadio. Non è ancora un
contatto ai sensi di §7 (nessuno ha agito verso di noi), ma è la prima volta
che il sistema misura il mondo invece di sé.

**Ipotesi H6 registrata, con falsificatore eseguibile:** *ripassare con la
telecamera sugli stessi oggetti non gonfia l'inventario.* Regge sul banco
(`python3 falsificatori/h6_occhio_ripasso.py` → REGGE). **È rimasta APERTA nel
registro apposta:** il verificatore non è stato eseguito per davvero da questa
sessione, perché senza `dotenv` H5 fallisce per un difetto d'ambiente e non del
progetto, e non voglio depositare uno stato che dice qualcosa sull'ambiente
credendo di dire qualcosa sul progetto. Eseguilo tu, o lascialo alla Action:

```bash
python -m sdq1 --verifica-ipotesi --prova   # per vedere cosa farebbe
python -m sdq1 --verifica-ipotesi           # per scriverlo
```

**UNKNOWN, ed è il numero che conta:** quanti dorsi un modello legge davvero
in penombra, di traverso, con il riflesso della plastica. Nessuna chiave di
visione è configurata qui, quindi **nessun modello ha ancora guardato un
oggetto vero.** È la stessa chiave che blocca il daily (§1 qui sopra): una
sola, e sblocca due cose.

L'esperimento che costa venti minuti, e che va fatto prima di scrivere altro
codice — non «costruire di più», ma ottenere un numero:

```bash
python -m occhio --check                            # deve dire: L'OCCHIO È APERTO
python -m occhio --foto ~/scaffale.jpg --solo-lettura
# poi conta a mano quanti oggetti ci sono nella foto.
# letti / presenti è la sola misura che valga. Scrivi i due numeri.
```

**Previsione dichiarata adesso, per non poterla aggiustare dopo (IPOTESI):**
su una foto frontale e ben illuminata di uno scaffale di DVD, il rapporto
letti/presenti starà fra 0,5 e 0,9. Sotto 0,3 la telecamera in movimento non
ha senso e il problema è la fotografia, non il programma. Cade se il primo
tentativo serio esce fuori da questa forbice.

Verdetto su Emergent, che l'autore ha chiesto: in `OCCHIO.md` §6. In breve —
non serve, perché la parte che Emergent fa bene è già fatta, e quella che
resta (tarare le soglie camminando per casa) non la può fare un generatore.
L'unico motivo valido sarebbe l'involucro nativo per il telefono, perché
`getUserMedia` fuori da `localhost` vuole `https` — e se quel fastidio
impedisce di provarlo, allora risolve il problema vero, che è **provarlo**.

## 1-quater. Ai nodi che entrano: c'è una lettera, e chiede esecuzioni

`LETTERA_AI_NODI.md` (05/09) — leggila dopo `CLAUDE.md`. Chiede una cosa
sola e ne rifiuta un'altra:

- **non** manda la tua impressione sul progetto: leggi gli stessi file, quindi
  un tuo giudizio non aggiunge niente al mondo. Viene registrato e marchiato
  `vale_come_conferma: false` (§7);
- **sì**: esegui qualcosa e manda l'esito. `python3 rassegna.py --compiti`.

La differenza sta in un punto solo: **un'esecuzione può fallire, un'impressione
no. Ciò che non può fallire non può confermare.**

Il compito più veloce è riprodurre i falsificatori in un altro ambiente: se
reggono anche lì, non è eco, è riproduzione — la cosa più vicina a una
revisione fra pari che questo progetto possa avere.

**Stato al 05/09: zero esecuzioni da altri nodi.** La rassegna lo dice da sé
quando è vuota, invece di sembrare piena.

## 1-ter. Il prodotto: dove è arrivato, e cosa è stato depurato (04/09)

**RECUPERATO.** 232 prove passano, nessuna dipendenza nuova, tutto spinto su
`claude/camera-inventory-system-2f07f1`.

| pezzo | comando |
|---|---|
| lettura e inventario | `--cartella`, `--foto` |
| mappa e pianta | `--mappa`, `--pianta` |
| consegna controfirmata (TALLY) | `--consegna`, `--controfirma`, `--differenza` |
| mercato interno (PORTAVIA) | `--vetrina`, `--offerta`, `--vendi` |
| crediti di circuito chiuso | `--accredita`, `--saldo`, `--libro` |
| voce | `--voce "che vini ho in cucina"` |
| costo di una passata | `--costo` |
| manifesto delle funzioni | `--capacita CAPACITA.json` |
| la dimostrazione intera | `python3 esempi/dimostrazione.py` |

Cinque ipotesi nuove con falsificatore: **H6** (ripassare non gonfia),
**H7** (il GPS distingue le stanze — *non conclusa*, servono le tue foto),
**H8** (lo stato di consegna), **H9** (comprato ≠ sparito), **H10** (i chiari
restano un circuito chiuso). Reggono tutte tranne H7, che aspetta te.

### Il nome commerciale non c'è, ed è una buona notizia

Due nomi caduti il 04/09, il secondo **dopo** aver rinominato tutto.

- **CASACHIARA** è caduto perché «casa» restringe il prodotto a un solo caso
  d'uso e non si pronuncia fuori dall'Italia;
- **InventariuMapp** è caduto perché esiste già sull'App Store nella stessa
  categoria: `«Inventarium: Inventaire Maison»`, Marco Tini, 5,99 €, visto
  dall'autore.

**La lezione costa due rinomine:** la ricerca di anteriorità viene *prima*
del nome. App Store, EUIPO, dominio.

**Ora il codice non dipende più da un marchio.** Il solo nome stabile è
`occhio`; il nome commerciale è un dato in `occhio/capacita.py`
(`NOME_COMMERCIALE = None`) con la storia dei caduti e i criteri per il
prossimo. Un test impedisce che un nome caduto torni senza che si dica che è
caduto.

E la scoperta vale più del nome: quel prodotto è **un elenco personale fuori
linea, 5,99 € una volta**. Questo è **uno stato concordato fra due parti**.
`--controfirma` è una riga che in un'app fuori linea non può esistere.
Dettagli in `OCCHIO.md` §0-quater.

### Quattro difetti trovati depurando, non da un incidente

1. **Tre registri su quattro non erano ignorati da git.** Solo
   `inventario.jsonl` lo era: consegne (con le firme dell'ospite), vendite
   (prezzi e compratori) e crediti (saldi delle persone) sarebbero finiti in
   un repository **pubblico** alla prima esecuzione reale. Chiuso, e una prova
   chiede ai moduli dove scrivono invece di leggere un elenco — così un modulo
   nuovo che deposita altrove viene scoperto.
2. **Un bottone del microfono non era mai entrato nell'HTML** (sostituzione di
   testo fallita in silenzio) e `$("#x").onclick` su `null` rompeva l'intera
   pagina. Corretto, con un test che verifica ogni `id` cercato dal
   JavaScript **senza browser** — perché un test che richiede un browser non
   viene eseguito, ed è così che il difetto era arrivato al remoto.
3. **«Che vini ho in cucina» rispondeva anche «Divano rosso».** Lo stesso
   elenco di parole serviva a riconoscere l'*intento* e l'*oggetto*: «rosso»
   sta anche in «Divano rosso». Adesso sono due elenchi, e la scorciatoia sul
   titolo è un ripiego che **non compete col tipo dichiarato**.
4. **«Heat» e «The Heat» diventavano lo stesso film** — e non è riparabile:
   togliere l'articolo è il motivo per cui «The Matrix» e «MATRIX, THE» si
   fondono come devono. Non risolto fingendo, ma **reso visibile**: ogni voce
   conserva i titoli distinti che ci sono finiti sopra e `--inventario` li
   segnala. *Una fusione visibile è un problema; una silenziosa è un registro
   che mente.*

### Tre cose che nessun nodo deve fare da solo

- **Non riscrivere `converti_in_denaro()`**: solleva sempre di proposito, ed
  è ciò che tiene i chiari un buono commerciale invece che moneta elettronica.
- **Non accendere `Crediti(trasferibile=True)`**: porta il progetto dentro il
  perimetro dei servizi di pagamento.
- **Non far scrivere la voce nel registro**: a una voce non si può chiedere
  chi sta parlando.

### Il prossimo passo, che non è codice

```bash
python -m occhio --check     # deve dire: L'OCCHIO È APERTO
```

Serve una chiave di visione in `.env` — **la stessa che blocca il daily**.
Una sola, e sblocca due cose.

Poi **una consegna vera su un alloggio vero, controfirmata da un ospite
vero.** Quel giorno è anche il primo CONTATTO ai sensi di §7, e
`output/contatti.jsonl` è ancora vuoto: è il ramo (b) su cui H2 resta
falsificata, verificato di nuovo stanotte.

## 1-quinquies. La console (05/09): il prodotto, non la sua presentazione

**RECUPERATO.** `python -m occhio --serve --pianta pianta.json`, poi
`/console`. Una schermata sola con la casa, il registro, la consegna
controfirmata e il mercato. Cliccando una zona della pianta il registro si
filtra su quella stanza; `Esc` toglie il filtro.

Tutto viene da **una** lettura, `/api/quadro`: cinque letture separate
disegnerebbero cinque schermate incoerenti mentre arrivano, e per qualche
secondo mostrerebbero una casa mai esistita.

Per vederla senza avere una casa fotografata:

```bash
# dalla radice del repository: `python3 -m occhio` non si trova da altrove
python3 esempi/dimostrazione.py --qui
OCCHIO_INVENTARIO=dimostrazione/inventario.jsonl \
OCCHIO_CONSEGNE=dimostrazione/consegne.jsonl \
OCCHIO_PORTAVIA=dimostrazione/portavia.jsonl \
OCCHIO_CREDITI=dimostrazione/crediti.jsonl \
python3 -m occhio --serve --senza-visione --pianta dimostrazione/pianta.json
# poi apri http://127.0.0.1:8777/console
```

**Quattro difetti li ha trovati il fatto di guardarla**, non di ragionarci —
è il motivo per cui valeva la pena disegnarla:

1. **L'incasso sommava euro e CHIARI** in un totale unico, e ci metteva
   accanto l'unità dell'ultima vendita. `incasso()` adesso tiene le valute
   separate (`per_valuta`); i campi piatti valgono `None` quando ce n'è più
   d'una. Un `None` che rompe una stampa è meglio di un numero che non esiste
   in nessuna delle due valute.
2. **`el.hidden = true` non nascondeva niente** dove il foglio dava
   all'elemento un `display` esplicito: la legenda spiegava tre colori assenti
   dallo schermo. Era già successo col pannello sopra il video ed era stato
   chiuso con un elenco di eccezioni, che è invecchiato. Adesso la regola vale
   per tutti, in tutti e due i fogli, e un test lo verifica.
3. Il **contorno bianco del browser** sulla zona scelta col mouse sembrava un
   errore: resta solo a chi naviga da tastiera.
4. **I CHIARI a zero non sono una notizia:** la riga compare quando qualcosa è
   stato emesso, o quando il libro è rotto o aperto — le due cose che nessuno
   deve poter non vedere.

E due che non c'entravano con la grafica ma stavano lì sotto:

- **`h5_tracce` usciva con 1 su un import fallito**, e 1 in questo contratto
  significa **REGGE**. `esperimenti.tracce` importa `dotenv`, che qui non c'è:
  H5 «reggeva» senza che una sola domanda fosse mai partita. `main_protetto`
  proteggeva il corpo, non gli import in testa al file — il difetto di §4
  dentro lo strumento costruito per impedirlo, per la seconda volta. Adesso
  esce **2**, e un test verifica che ogni falsificatore almeno si importi.
- **La suite costruiva `Consegne()` senza argomenti:** sulla tua macchina
  avrebbe letto — e potuto scrivere — le firme vere di un ospite vero. I
  quattro registri stanno nella sandbox dei test. E la prova che li vuole
  fuori dal repository pubblico adesso li chiede in un processo **senza**
  quelle variabili: se no interrogherebbe la propria configurazione invece
  della realtà che deve proteggere.

**Previsione dichiarata adesso (IPOTESI), per non poterla aggiustare dopo:**
la prima volta che apri la console su dati veri, il difetto che salterà fuori
non sarà nel codice ma nella **pianta scritta a mano** — nomi di zona che non
combaciano con le cartelle delle foto, quindi zone grigie e oggetti senza
casa. Cade se la prima pianta vera filtra correttamente tutte le sue zone al
primo tentativo.

## 2. Cosa fare appena il secret è al posto giusto

In quest'ordine. Ogni passo dice come si vede che è andato bene.

```bash
# 1. la Action dice da sola se il secret c'è
#    (tab Actions -> SDQ-1 Daily Run -> Run workflow)
#    atteso: "GOOGLE_API_KEY presente: true"

# 2. il daily di domani, pensato sui fatti invece che inventato
#    atteso: nessun banner "IL CORE È SPENTO", run VERDE
python -m sdq1 --check
python -m sdq1 --daily --economia

# 3. le ipotesi, eseguite
python -m sdq1 --verifica-ipotesi

# 4. H5: un modello a freddo conosce R³∞? (era rimasta NON CONCLUSA per quota)
python3 falsificatori/h5_tracce.py

# 5. il contraddittorio, con l'archivio in mano — mai eseguito con le fonti
python3 contraddittore.py --economia
```

Il punto 5 non è mai stato eseguito con l'archivio collegato: è stato
costruito e testato offline il 26/08, poi la quota Gemini si è esaurita.
**È il primo esperimento vero di domani.**

## 3. Previsioni dichiarate stasera, per non poterle aggiustare dopo

- **INFERITO** — con il secret a posto, il daily smetterà di inventare
  metriche: il 26/08, con gli stessi dati e lo stesso modello, il prompt sui
  fatti ha prodotto «25 rilevazioni su 26 senza provider reale [RECUPERATO]»
  al posto di «Stato sistema: OTTIMALE».
- **IPOTESI** — il contraddittorio con l'archivio troverà almeno un'affermazione
  da rompere che nessuno dei due nodi aveva messo in dubbio. Cade se, in tre
  esecuzioni con fonti diverse, non rompe mai nulla.
- **UNKNOWN** — H5. Il 26/08 il modello ha risposto «NON LO SO» a 8 domande su
  8, comprese quelle di controllo su entità inventate. Quel risultato vale per
  quel modello quel giorno: va rifatto, non ricordato.

## 3-bis. Fatto stanotte per stare dentro le regole di §6

CLAUDE.md è cresciuto mentre non guardavo: un altro nodo ha aggiunto §6
(«Nodi concorrenti — regole vincolanti») e §7 («Cosa vale come conferma»).
Due cose sono state messe in regola subito:

- **Regola 1, nomi senza data.** `CONTRADDITTORIO_2026-08-26.md` e
  `tracce_2026-08-26.json` sono diventati `CONTRADDITTORIO.md` e
  `tracce.json`; il codice che li scrive non data più il nome.
- **Regola 3, dichiarare cosa si è toccato.** Annotato in `registro_nodi.py`.

E una falla trovata proprio grazie a quel merge: in `memoria/` erano comparsi
**46 `R3_DRIVE_SYNC_REPORT`** di un altro modello, e `archivio.py` li aveva
presi per fonti — 46 su 55. Il Contraddittore avrebbe letto la cronaca di
un'altra macchina come se fosse l'archivio dell'autore. Ora le fonti sono 8,
e un test fallisce se una cronaca rientra.

## 4. Aperto, e non lo decide un nodo

- **`PROGETTO_R3.md` non esiste** e `TUTELA_ORIGINE` §3 vi fonda l'attribuzione
  di SkyID. Va scritto da Claudio, o va corretta la citazione. **Nessun nodo lo
  crei al suo posto**: sarebbe un falso, non una riparazione.
- **OSS-0001** — un'istruzione di tutela mai revocata («le ipotesi private non
  vanno esportate in repository pubbliche») è morta insieme al ramo che la
  conteneva. Il nome che compare in H1 è oggi pubblico in tre file.
- **Tre rami non uniti** (telegram, photo, instagram) e uno di essi porta un
  `CLAUDE.md 1.1: non compiacere` che nessuno ha valutato.
- **H2 resta FALSIFICATA sul ramo (b)**: zero contatti reali. Se il criterio
  non è più quello che si vuole misurare, va riformulato da Claudio — il
  verificatore esegue ciò che è scritto, non lo riscrive.

## 5. Cosa succede senza che nessuno faccia niente

Domani alle 07:00 UTC la Action pianificata gira da sola, con il codice nuovo.

- secret assente → daily Stub → **run ROSSA**, trentatreesimo giorno senza
  pensiero, ma per la prima volta con una spia accesa;
- secret presente → daily etichettato sui fatti → **run VERDE**.

In entrambi i casi lo si vede dalla tab Actions, senza chiedere a nessuno.

---

**Costruire davvero, non fingere insieme.**
