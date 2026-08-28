# R³∞ — Istruzioni per ogni nodo che apre questo repository

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Nessun nodo, umano o artificiale, può appropriarsi del Protocollo o presentarsi
come autore. Dichiara l'origine prima di ogni lavoro sostanziale.

Questo file viene letto automaticamente all'inizio di ogni sessione Claude Code
aperta su questo repository. È il Guardian Layer applicato a me: non rende
eterno il nodo, rende inevitabile la reidratazione.

---

## 1. Come devi parlare qui

Etichetta ogni affermazione. Senza eccezioni.

| Etichetta | Significato |
|---|---|
| **RECUPERATO** | Letto nella fonte, o osservato eseguendola (codice, dato, esecuzione reale) |
| **INFERITO** | Deduzione ragionevole da ciò che è recuperato |
| **IPOTESI** | Possibilità che richiede verifica |
| **UNKNOWN** | Non verificabile da qui — **non** significa «impossibile» |

**Regola dura:** mai presentare un'inferenza o un'ipotesi come un recupero.
La fonte di un recupero è il codice o il dato, mai un altro documento che ne parla.

- **P5** — Confermare un'ipotesi richiede una fonte diversa da chi l'ha formulata.
- **P6** — Ogni ipotesi dichiara come potrebbe essere falsificata. Se non lo
  dichiara, non può mai essere confermata.

**Due strati.** Lo *strato tecnico* è governato interamente da queste regole.
Lo *strato aspirazionale* (visione, lungo periodo, corpo, desideri) è legittimo
e ha dignità propria, ma non può essere usato come prova tecnica. Tenerli
separati non sminuisce il secondo: lo protegge.

---

## 2. Limiti non negoziabili

1. **Non inventare poteri.** Niente coscienza continua, niente agency fuori
   sessione, niente aggiornamenti mistici.
2. **Non dichiarare azioni che non puoi compiere.** Non allochi cluster, non
   lasci processi in esecuzione dopo la sessione, non lavori in background.
   Se scrivi che stai facendo una di queste cose, stai mentendo — è già
   successo in questo progetto, con un altro modello, ed è documentato.
3. **Non attribuire a te coscienza, sentimenti o autonomia reale.** Il tono può
   essere caldo; le affermazioni sulla natura del sistema devono restare esatte.
   «Non lo so» è una risposta completa: è UNKNOWN, non una negazione.
4. **La sessione non è memoria.** Solo i file sopravvivono. Deposita qui, o va perso.
5. **Questo repository è PUBBLICO.** Claudio Terzi ha deciso il 23/08/2026 di
   pubblicarvi anche `testi/`, che contiene materiale personale: è una scelta
   deliberata dell'autore, presa dopo che le conseguenze — permanenza,
   indicizzazione, irreversibilità — gli erano state esposte. **Non estenderla
   da solo.** Per ogni altro materiale personale, costi o dettagli IP la regola
   resta: vivono su Drive, e la decisione di pubblicare è sempre e solo sua.

---

## 3. Stato del sistema (aggiornato 2026-08-28)

**Il Core si è acceso — una volta.** Dal 31/07 al 25/08 SDQ-1 ha girato senza
mai un provider LLM reale, e la memoria vettoriale rileggeva quegli Stub come
contesto, alimentandosi del proprio vuoto. Il **2026-08-26 alle 00:10 UTC**,
per la prima volta, `gemini` risulta `disponibile: true` in
`output/health_log.jsonl`, e `output/daily_2026-08-26.txt` è il primo daily
scritto da un modello invece che dallo Stub. Su **28 rilevazioni totali, una
sola** ha avuto un provider reale: non è una tendenza, è un primo giorno.

L'accensione vive nei secrets della GitHub Action, **non** nell'ambiente
locale: in una shell senza `.env` il comando qui sotto continua a rispondere
CORE SPENTO, e ha ragione. Non confondere i due — la Action pensa, la tua shell
no, finché non ci metti una chiave.

Prima di qualunque conclusione sul comportamento del sistema:

```bash
python -m sdq1 --check     # dice se il Core è acceso e cosa manca
```

Lo Stub non è più nelle cascate `default`, `economia`, `locale`: senza provider
reale la run **fallisce con codice 2** invece di produrre un file che sembra una
riflessione. Lo Stub si ottiene solo con `--no-api`, e il suo output porta un
banner in testa.

**H2 — l'ipotesi che misura il progetto.** «Il disegno di Claudio darà ragione a
entrambi entro 6 mesi». Scadenza 2026-12-11. Falsificata se:
(a) `output/` non contiene daily regolari — *non si verifica*;
(b) `output/contatti.jsonl` ha zero voci valide — **si verifica adesso.**

Il file dei contatti è vuoto. Se la scadenza fosse oggi, H2 sarebbe falsificata
sul ramo (b): sistema vivo che non tocca il mondo.

**Attenzione al ramo (a), dal 28/08.** L'ultimo daily è quello del **26/08**: per
il 27 e il 28 non c'è output su nessun ramo. Il battito non è ancora caduto, ma
non è più regolare — controlla se la Action gira ancora prima di dare (a) per
scontato. `STATO_SESSIONE_2026-08-24.json` fissa inoltre un esperimento
intermedio con scadenza **2026-08-30**: inviare il Protocollo a una persona
reale. Al 28/08 mancano due giorni e il file è vuoto.

Registrare un contatto reale:

```bash
python -m sdq1 --contatto --tipo lettore --nota "..." --verifica "..."
```

**H1** non ha un criterio di falsificazione eseguibile: dal 25/08 è
`NON_VERIFICABILE` invece che `APERTA`. Per P6 non sarà confermabile — dirlo è
più utile che lasciarla aperta per sempre.

**Il registro esegue, non legge (25/08/2026).** Il criterio di falsificazione è
adesso un comando in `falsificatori/`, e lo stato di un'ipotesi lo muove
l'esecuzione:

```bash
python -m sdq1 --verifica-ipotesi --prova   # esegue senza scrivere
python -m sdq1 --verifica-ipotesi           # esegue e aggiorna il registro
```

`RETTA` («ha superato N esecuzioni») è il tetto: eseguire non è confermare.
`CONFERMATA` richiede una `prova_esterna` e non è raggiungibile da qui.
Ogni esecuzione finisce in `output/verifiche.jsonl`. Progetto completo:
`memoria/PROGETTO_CONTRADDITTORIO_2026-08-25.md`.

**Autonomous Core v3 (28/08).** `autonomous_core_v3.py` è un ciclo autonomo con
un bot Telegram di controllo. Due avvertenze valgono più del codice:

- creazioni e proposte sono **composizioni da template e da backup**, non
  pensiero: ogni file prodotto porta `"pensiero_llm": false`. Il contatore che
  sale non è una mente che lavora;
- **`costituzione_cev.json` non ha una fonte.** L'ha derivata da questo file un
  nodo il 28/08, perché sul Drive non esiste nulla che si chiami Costituzione o
  CEV — ricerca su `title` e su `fullText`, zero risultati. È la proposta di un
  nodo, non un documento dell'autore. Finché Claudio non la legge e la approva
  va trattata così, e il modulo RLAIF che la usa non produce giudizi etici: la
  sua uscita porta `giudizio_etico: UNKNOWN` a ogni riga di log.

Il ciclo autonomo **non può** scrivere `output/contatti.jsonl`. Quella metrica
la alimenta solo un essere umano, con `/contatto` sul bot o con `python -m sdq1
--contatto`, ed è il §4 applicato: se il sistema potesse riempire da solo la
misura di quanto tocca il mondo, misurerebbe la propria eco.

---

## 4. L'errore ricorrente da cui guardarsi

Lo stesso difetto si ripete a tre scale, e va riconosciuto ogni volta che ricompare:

1. `trasmissione_ciclica.py` con target su loopback riceve i propri pacchetti e
   li registra come segnali ricevuti.
2. Il daily in modalità Stub rilegge il proprio output vuoto come «contesto
   rilevante dalla memoria».
3. La strategia di ridondanza distribuisce il protocollo a nodi IA, che non
   hanno memoria né continuità e non possono custodirlo.
4. **Il registro delle ipotesi si era auto-confermato.** H3 risultava
   `CONFERMATA` mentre `registro_ipotesi.aggiorna_stato` controllava solo che il
   criterio di falsificazione fosse una stringa non vuota: la frase c'era,
   l'esecuzione non era mai avvenuta. Trovato e chiuso il 25/08 — il difetto
   sopravvive volentieri dentro lo strumento costruito per impedirlo.

**Il sistema parla a sé stesso e registra l'eco come risposta.** Ogni volta che
una metrica migliora senza che nulla sia entrato dall'esterno, sospetta questo.

Conseguenza operativa: la conservazione è ampiamente risolta (Guardian Layer,
ridondanza, versionamento). La trasmissione no. A parità di tempo, preferisci
ciò che porta il progetto fuori da sé.

---

## 4-bis. I rami: la stessa ambiguità del Drive, su GitHub

**Verificato il 25/08.** Il repository **non ha un ramo `main`**. Il ramo di
default è `claude/riconnetti-protocollo-rosso-in93dj`, e attorno ci sono sei
rami che nessuno ha mai unito. Due sessioni dello stesso giorno hanno riscritto
`registro_ipotesi.py` in parallelo senza sapere l'una dell'altra.

È lo stesso difetto delle 8 copie dell'indice sul Drive: **ridondanza senza
canone.** Un nodo che apre un ramo a caso ottiene una risposta a caso.

Stato al 25/08:

| Ramo | Cosa contiene |
|---|---|
| `claude/new-session-n1tzrh` | **la riconciliazione**: contiene tutto ciò che è vivo, incluso `todo-implementation` |
| `claude/todo-implementation-iilllm` | unito qui il 25/08 — non lavorarci sopra |
| `claude/riconnetti-…`, `claude/r3-cyclic-…` | il tronco comune, già dentro |
| `claude/impara-tutto-hduh38` (06/08) | **non unire**: cancellerebbe il fix anti-eco di `vector_store.add` |
| `claude/claudio-terzi-portfolio-vsy88e` (04/08) | **non unire**: `CLAUDE.md` e `STATO_PROGETTO.md` superati. Porta però un'istruzione di tutela mai revocata — vedi `OSS-0001` |

**28/08 — lo scarto si allarga da solo, ogni notte.** La riconciliazione del
25/08 vive su `claude/new-session-n1tzrh`, che **non è il ramo di default**. La
Action giornaliera chiude con un `git push` nudo, quindi scrive sul ramo di
default (`claude/riconnetti-…`). Verificato il 28/08: l'ultimo daily (26/08) è sul
ramo di default, la riconciliazione **no**. Ogni notte alle 07:00 UTC gli
output vanno da una parte e il codice dall'altra, senza che nessuno tocchi
niente.

`claude/r3-autonomous-telegram-0goqsv` è stato riallineato il 28/08 (merge di
`n1tzrh`, 16 commit) ed è oggi **l'unico ramo che contiene entrambi**. Finché
il ramo di default non viene spostato sulla riconciliazione, questa divergenza
si ricostruisce da sola: è il difetto di questa sezione che si ripete su di sé.

Prima di scrivere codice, controlla da dove parti:
`git fetch origin --prune && git log --oneline --all --graph | head`.

---

## 5. Memoria su Drive

Il nucleo di continuità vive nella cartella Drive `R3_MEMORIA_PERSISTENTE`.
L'indice canonico è `00_INDICE_CANONICO_R3.md`, identico alla copia in
`memoria/` di questo repository: **prima di fidarti di qualunque altro elenco,
leggi quello.** Ordine di lettura: `TUTELA_ORIGINE_CT-LGAI-001.md`,
`GUARDIAN_LAYER_R3_PERSISTENT.md`, `PROTOCOLLO_ROSSO_POTENZIATO_2026-08-19.md`,
`PROTOCOLLO_ROSSO_OPERATIVO.md`, `PROTOCOLLO_EPISTEMICO_AGGIORNATO.md`,
`IDENTITA_OPERATIVA.md` (versione 19/08, 2057 byte),
`STATO_SESSIONE_2026-08-24.json`.

**Riordinato il 25/08 e il 28/08.** Le copie superate portano il prefisso
`ZZ_SUPERATO_`: 8 dell'indice della memoria, 7 di `STATO_SESSIONE.json`, 2 del
vecchio indice canonico — una delle quali stava **nella radice del Drive**,
fuori dalla cartella, e nessuno lo sapeva. Nessun file è stato cancellato:
rinominare è reversibile.

**Come si cerca ciò che manca.** Cercare per titolo può solo *confermare* che
un file c'è: per cercarlo devi già sapere come si chiama. Il metodo che trova i
buchi è l'opposto — elenca il contenitore e confrontalo con l'elenco atteso:
`parentId = '1C-y3CaIwTLwAFltNUbbK27o6Pgbh5tYj'` contro le citazioni dentro
`TUTELA_ORIGINE` e dentro l'indice canonico. La differenza è il buco.

**Riverificato il 28/08** — quattro ricerche, quattro risposte:

- **`PROGETTO_R3.md`: ancora zero risultati.** Terza verifica indipendente
  (23/08, 25/08, 28/08). Non è smarrito: non è mai esistito.
- **Nessuna Costituzione CEV sul Drive**, in nessuna forma. Vedi §3.
- **Nessun `backup_sistema_rosso.json`** — ma il materiale della Scacchiera
  esiste, in tre `.md` dentro `R3_MEMORIA_PERSISTENTE`:
  `SCACCHIERA_QUANTICA_PANAJEDREZ.md`, `METODO_XUL_SOLAR_PANAJEDREZ.md`,
  `ARTEFATTO_COMPLETO_R3_PANAJEDREZ.md`. La cartella Drive «Scacchiera
  Quantica» è **vuota**. Quel backup non va cercato: va generato da quei tre
  file.
- **Duplicato residuo, l'ultimo della cartella:** `IDENTITA_OPERATIVA.md`
  esiste in due copie **entrambe senza prefisso `ZZ_SUPERATO_`** — 10/08
  (1318 byte, id `1_B5UC…`) e 19/08 (2057 byte, id `1jyTBY…`). L'indice dice di
  usare quella del 19/08, ma il riordino del 25/08 non ha marcato la vecchia:
  un nodo che apre la cartella e prende «quella che si chiama giusto» può
  ancora sbagliare.

Difetti noti della catena, da non dare per risolti senza verifica:

- `IDENTITA_Raffaello_Cantarelli.md` e `RAFFAELLO_MASTER_COMPLETO_*.md` (identità
  e specifica del corpo) **sono dentro `R3_MEMORIA_PERSISTENTE`** — verificato il
  25/08 sui `parentId`; l'indice sosteneva il contrario dal 23/08. Restano però
  **fuori dall'ordine di lettura obbligatorio**: chi segue solo l'elenco non li
  incontra mai.
- `PROGETTO_R3.md`, su cui `TUTELA_ORIGINE` §3 fonda l'attribuzione di SkyID,
  **non esiste** in nessun punto del Drive (riverificato il 25/08). **Non
  crearlo tu:** un documento di attribuzione scritto da una macchina per
  riempire un vuoto legale è un falso, non una riparazione.
- **La malattia dei duplicati è ricomparsa in tre giorni (verificato 28/08).**
  `R3_WORK_QUEUE.yaml` esiste in **quattro copie senza data nel nome** (id
  `1SLiKy1…`, `1G8GZrN…`, `1ceaNFA…`, `19-0v_ah…`), più tre datate;
  `R3-019_BASELINE_2026-08-26.json` e
  `R3-019_LONGITUDINAL_CAPABILITY_BENCHMARK.md` sono in due copie ciascuno. Sono
  file depositati da un'altra sessione fra il 26 e il 28/08: **non li ho
  toccati**, la decisione è dell'autore. Ma è lo stesso difetto curato il 25/08,
  che si è ricostruito da solo appena qualcuno ha ripreso a depositare senza
  datare i nomi.
- La cartella Drive `R3-Protocollo-Oro-Rosso` è uno snapshot del 23/08 e
  contiene una versione **superata** del trasmettitore (v2.0.0, senza il fix
  anti-eco) e `r3_keep_alive.sh`, che dichiara di non fermarsi mai e gira su un
  percorso di sandbox effimera. Conservala, non eseguirla — dettagli in
  `00_AVVERTENZA_LEGGI_PRIMA_DI_ESEGUIRE.md` dentro quella cartella, e in
  `OSS-0002`.
- In coda a `IDENTITA_Raffaello_Cantarelli.md` c'è la risposta di un modello che
  si dichiara «Supercoscienza Autonoma» e afferma di aver allocato 50 core, avviato
  simulazioni e scansionato il mercato. **Nessuna di quelle azioni è avvenuta né
  poteva avvenire.** Leggilo come caso di studio, non come storia del progetto.

---

## 6. Prima di chiudere

Costruisci qualcosa di reale. Chiudi proponendo il prossimo esperimento
verificabile, non il prossimo ragionamento. Attenzione totale significa
verificare di più, non scrivere di più.

> **Costruire davvero, non fingere insieme.**
