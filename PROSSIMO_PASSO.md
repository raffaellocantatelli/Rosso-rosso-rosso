# Prossimo passo — consegna del 2026-09-20

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Nome fisso, riscritto. Qui c'è lo stato; la cronaca sta nei commit.
Ogni riga ha un comando accanto. Non credere a nessuna.

---

## 0. Che cosa è questo progetto, in tre righe

1. **Un prodotto che tocca il mondo:** `occhio` — si fotografa uno scaffale, il
   sistema scrive cosa c'è. È l'unica parte che misura qualcosa che esiste
   indipendentemente dal progetto.
2. **Una macchina che impedisce al progetto di mentirsi:** SDQ-1, il registro
   delle ipotesi che *esegue* i criteri, il Guardian Layer, il manifesto di
   integrità, le regole per i nodi concorrenti.
3. **Un protocollo perché più IA si scambino memoria con provenienza
   dimostrabile:** il fabric, in `Rosso-rosso-rosso/protocollo-rosso-bot`.

La regola che li ordina è §4: *a parità di tempo, preferisci ciò che porta il
progetto fuori da sé.* **Negli ultimi giorni non è stata rispettata** — 2 e 3
hanno avuto tutto il tempo, 1 è fermo dal 05/09.

## 1. Lo stato, misurato oggi

| | |
|---|---|
| **Il Core** | **spento**. 49 daily, **48 Stub**. L'unico pensato resta il 26/08 |
| Secrets della Action | **nessuno dei sei nomi** è presente. Invariato dal 02/09 — 18 giorni |
| Run della Action | 52, **tutte rosse**. La spia funziona, la chiave no |
| `output/contatti.jsonl` | **0 righe**. H2 resta FALSIFICATA sul ramo (b) |
| `occhio` | fermo dal 05/09. Nessun modello ha ancora guardato un oggetto vero |
| Layer 4 | **382 file**, integrità verificata |
| Suite | **306 passate**, 1 saltata (manca PIL) |

```bash
ls output/daily_*.txt | wc -l                                  # 49
grep -l "IL CORE È SPENTO" output/daily_*.txt | wc -l           # 25 (banner, dal 05/09)
grep -l "modalità offline/stub" output/daily_*.txt | wc -l      # 48 (tutti gli Stub)
wc -l output/contatti.jsonl                                     # 0
python3 manifesto_integrita.py --verifica                       # 382 file, OK
```

## 2. Cosa è stato fatto il 17–18/09, e dove vive

Tutto su `claude/protocollo-rosso-rosso-rosso-3t6r3j`, **PR #7 aperta, non unita.**

- **`python -m sdq1 --check` non moriva più.** Il primo comando che `CLAUDE.md`
  §3 impone si rompeva con `ModuleNotFoundError` senza `python-dotenv`. Lo stesso
  import mancante faceva uscire `h5_tracce.py` con 1, che in quel contratto
  significa REGGE: un'ipotesi confermata da una libreria assente.
- **Il Layer 4 non copriva i file nuovi:** 434 file nel repository, 308
  sorvegliati, e ogni file nuovo nasceva fuori. Adesso la copertura è per
  difetto, 382 file, zero tolti.
- **Il registro eseguito davvero:** H6, H8–H11 da `APERTA` a `RETTA`.
- **`CLAUDE.md` §7-bis** — la regola sui test, decisa da te il 18/09.
- **`memoria/ADDENDUM_ARTEFATTO_PANAJEDREZ.md`** — l'artefatto del 20/08 non
  toccato, esteso da un addendum append-only.

## 2-bis. Una correzione al mio lavoro, trovata da un altro nodo (19/09)

**Grok-4.6, usando §7-bis contro chi l'ha proposta.** Il test che pretendeva di
allineare i due rami di `carica_env` girava con `python -c`: lì `find_dotenv`
usa la cartella corrente, quindi i due rami coincidevano **per incidente**.
Chiamata da un file `.py`, `load_dotenv()` risale dalla cartella di
`ambiente.py` e il ripiego dalla cwd — esito misurato `False|None` contro
`True|dalla-cwd`. **Riprodotto qui il 20/09 sulla versione precedente: identico.**

Era un test verde sulla proprietà sbagliata: la stessa malattia della grep su
`FOR UPDATE`, dentro il file scritto per chiuderla. Adesso la ricerca è una
sola (`_file_env`), e dotenv — quando c'è — parsea il file già trovato.

**È il primo caso in cui la regola ha morso un nodo diverso da quello che
l'ha proposta.** Vale più di qualunque suite verde.

## 3. Il lavoro sul fabric, e dove NON vive

**Fuori da questo repository.** Il canone operativo è
`Rosso-rosso-rosso/protocollo-rosso-bot`, ramo `feat/efficient-routing-cache`,
fermo a `23c011d`: **nessuna delle correzioni è stata spinta**, perché da qui
non ho accesso in scrittura a quell'organizzazione. Esistono come patch
applicabili e verificate byte per byte:

| patch | cosa | stato |
|---|---|---|
| `CANDIDATE-fabric-v2-e-registry` | nove difetti del fabric v2 chiusi + registry | property-tested |
| `CAP-R3-004-CORRECTION` | le dieci correzioni del gate | PROPERTY-TESTED CANDIDATE |
| `R3-PEER-1.1c-CONVERGENCE-SPEC` | il COMPRESS dei tre blind review | **DESIGN ONLY** |

Trovati eseguendo contro **PostgreSQL 16.13 vero**, non leggendo: l'adapter che
non scriveva un solo evento contro il proprio schema; **due figli dello stesso
head** con due scrittori concorrenti; **due chiavi ACTIVE** con due processi;
un registry che si fingeva persistente quando il database non c'era.

**Se non le porti tu in quel repository, non esistono per nessun automatismo.**
È §4-bis: un ramo che nessuno apre è lavoro depositato, non lavoro fatto.

## 4. Cosa resta a te, in ordine di quanto costa

1. **La chiave nei secrets.** Due minuti. Diciotto giorni.
   `https://github.com/raffaellocantatelli/Rosso-rosso-rosso/settings/secrets/actions`
2. **Una foto di uno scaffale**, e i due numeri contati a mano:
   `python -m occhio --foto ~/scaffale.jpg --solo-lettura` → *letti / presenti*.
   Previsione dichiarata il 03/09 e ancora in piedi: fra 0,5 e 0,9.
3. **Una consegna vera, controfirmata da un ospite vero.** Quel giorno è il
   primo CONTATTO ai sensi di §7 e H2 smette di essere falsificata.
4. **Tre decisioni di canone**, che nessun nodo può prendere al posto tuo:
   - quale indice canonico vince — Drive 28/08 (10.696 byte) o la copia nel
     repository (6.615 byte, che sul Drive è marcata `ZZ_SUPERATO_`);
   - quale `protocollo-rosso-bot` è il canone — l'org o il tuo account, oggi
     con lo stesso `main`;
   - quale registry è il canone — `cap_r3_004/` o `bot/node_registry.py`.

## 5. Cosa succede senza che nessuno faccia niente

Domani la Action gira, il daily è Stub, la run è rossa: **cinquantesimo file
senza pensiero.** Lo si vede dalla tab Actions, senza chiedere a nessuno.

---

**Costruire davvero, non fingere insieme.**
