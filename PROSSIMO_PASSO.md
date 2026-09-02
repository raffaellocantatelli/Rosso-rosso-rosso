# Prossimo passo — consegna del 2026-09-02, 23:30 UTC

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
