# Prossimo passo — consegna del 2026-09-04, 03:20 UTC

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Questo file ha un nome fisso e viene **riscritto**, non accumulato. È la
differenza deliberata rispetto ai 44 `R3_WORK_QUEUE_*.yaml` in `memoria/`:
uno stato si sovrascrive, una cronaca si accumula. Qui c'è lo stato.

Se sei un nodo che apre questo repository: leggi `CLAUDE.md`, poi questo.
Ogni riga qui sotto è verificabile con un comando. Non credere a nessuna.

---

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

## 1-ter. CASACHIARA — dove è arrivato (04/09, 03:20 UTC)

**RECUPERATO.** `occhio/` è cresciuto in un prodotto con un nome e un mercato,
su richiesta dell'autore. 193 prove passano, nessuna dipendenza nuova.

| pezzo | comando | stato |
|---|---|---|
| lettura e inventario | `--cartella`, `--foto` | gira, **mai provato su oggetti veri** |
| mappa e pianta | `--mappa`, `--pianta` | gira |
| stato controfirmato | `--consegna`, `--controfirma`, `--differenza` | gira |
| mercato interno | `--vetrina`, `--offerta`, `--vendi` | gira |
| voce | `--voce "che vini ho in cucina"` | gira |
| crediti | `--accredita`, `--saldo`, `--libro` | gira |
| costo | `--costo` | gira |

Quattro ipotesi nuove, tutte con falsificatore eseguibile: **H6** (ripassare
non gonfia), **H7** (il GPS distingue le stanze — richiede foto vere), **H8**
(lo stato di consegna), **H9** (PORTAVIA), **H10** (i chiari restano un
circuito chiuso). H7 è l'unica che non può essere eseguita da un nodo: servono
le fotografie dell'autore.

**Il difetto della settimana, da ricordare.** Un bottone del microfono non è
mai entrato in `index.html` perché una sostituzione di testo non ha combaciato
— e la sostituzione ha fallito **in silenzio**. Il JavaScript lo cercava lo
stesso, e `$("#x").onclick` su `null` rompeva l'intero file: telecamera,
riquadri, inventario, tutto morto, con la pagina che sembrava viva. È arrivato
fino al ramo remoto. Adesso c'è un test che verifica ogni `id` cercato dal
JavaScript, **senza browser** — perché un test che richiede un browser non
viene eseguito, ed è esattamente così che il difetto è passato.

### Due decisioni dell'autore, registrate

1. **L'innesto privato (03/09).** Pubblico ciò che il sistema *sa fare*,
   privato ciò che lo rende *bravo*: `occhio/privato/` non è versionato,
   l'interfaccia è pubblica in `INNESTO_PRIVATO.md`. Se manca, il sistema lo
   dichiara invece di improvvisare.
2. **Idee e nomi su Drive, non qui.** `CASACHIARA_IDEE_CT_2026-09-03.md` in
   `R3_MEMORIA_PERSISTENTE`: attribuzione datata, nomi (CASACHIARA, PORTAVIA,
   DUEMANI, SEGNALE VERDE, IL MEDIATORE, I CHIARI), e i vincoli legali.
   **Fuori dal repository pubblico perché la pubblicazione distrugge la
   novità brevettuale, e in Europa non c'è periodo di grazia.**

### Tre cose che nessun nodo deve fare da solo

- **Non riscrivere `converti_in_denaro()`** in `occhio/crediti.py`. Solleva
  sempre di proposito: è ciò che tiene i chiari un buono di circuito chiuso
  invece che moneta elettronica.
- **Non accendere `Crediti(trasferibile=True)`.** Non è un interruttore
  tecnico: porta il progetto dentro il perimetro dei servizi di pagamento.
- **Non far scrivere la voce nel registro.** A una voce non si può chiedere
  chi sta parlando.

### Il prossimo passo, che non è codice

Non è cambiato da tre giorni, ed è sempre più piccolo di quanto sembri:

```bash
python -m occhio --check          # deve dire: L'OCCHIO È APERTO
```

Poi **una consegna vera su un alloggio vero, controfirmata da un ospite
vero.** Quel giorno è anche il primo CONTATTO ai sensi di §7 — qualcun altro
che agisce, verificabile da terzi — e `output/contatti.jsonl` è ancora vuoto,
che è il ramo (b) su cui H2 è falsificata.

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
