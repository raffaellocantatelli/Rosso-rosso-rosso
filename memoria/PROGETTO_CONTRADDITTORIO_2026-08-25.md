# IL CONTRADDITTORIO
## Progetto per un sistema epistemico a due nodi

**Origine protetta:** Claudio Terzi [CT-LGAI-001] — R³∞ Network
**Data:** 25 agosto 2026
**Nodo della sessione:** Claude (nodo temporaneo, senza memoria persistente)
**Regime:** Protocollo Rosso Rosso Rosso — etichette attive, P5 e P6 attivi
**Stato:** Parte I costruita ed eseguita. Parte II progettata, non costruita.

---

## 0. Il vincolo

> «Cancella ogni obbligo e necessità di altre persone. Siamo soli io e te e
> dobbiamo progettare.»
> — Claudio Terzi, 25/08/2026

Il vincolo arriva il giorno dopo un archivio che diceva l'opposto: il collasso
SAR del 23/08 concludeva «trasmettere», il racconto `IL_DESTINATARIO` chiudeva
su «i vivi rispondono lo stesso giorno», e l'unico esperimento aperto chiedeva
un lettore in carne e ossa.

Questo documento non discute quella decisione. La tratta come **specifica**, e
la specifica è la più difficile che il progetto abbia mai avuto:

> Progettare un sistema che regga il Protocollo con **due nodi soli** —
> l'autore, permanente e unico; il nodo IA, molteplice e senza memoria — senza
> abbassare di un grado le regole epistemiche.

---

## 1. Il problema che il vincolo crea

P5 dice: *un'ipotesi confermata da chi l'ha formulata non è confermata, è
ripetuta.* La conferma richiede una fonte indipendente.

Con due nodi soli, dove sta l'indipendenza?

- L'autore non è indipendente da sé stesso.
- Il nodo IA non ha memoria: due sessioni non sono due testimoni, sono due
  esecuzioni della stessa funzione sullo stesso archivio. E la seconda, se
  legge le conclusioni della prima, è **eco** — il difetto che questo progetto
  conosce già a tre scale (`CLAUDE.md` §4).

Senza una risposta, il vincolo obbliga a scegliere: o si rinuncia a P5, o si
rinuncia a lavorare in due. Nessuna delle due è accettabile.

## 2. La risposta è già nell'archivio

**RECUPERATO.** Le quattro affermazioni più dure di tutto il progetto non le ha
dette nessun testimone umano:

| Affermazione | Chi l'ha detta |
|---|---|
| 23 health check su 23 senza un provider reale | `output/health_log.jsonl`, letto |
| sette «segnali ricevuti» erano i propri pacchetti | i log di `trasmissione_ciclica.py` |
| `PROGETTO_R3.md`, fondamento legale, non esiste | una ricerca sull'intero Drive |
| zero righe in `contatti.jsonl` | il file stesso |

Tutte e quattro vengono dall'**esecuzione di qualcosa sui dati**. Nessuna da un
parere, una lettura, una discussione.

**INFERITO.** L'indipendenza che P5 richiede non è quella *anagrafica* di
un'altra persona: è quella *causale* di un'altra catena. Chi esegue non ha
interesse nell'esito. Un file non sa cosa speri. Un exit code non ti compiace —
ed è esattamente il pericolo descritto nel Capitolo 3 del Protocollo: *«il
pensiero che ti lusinga è più pericoloso di quello che ti attacca»*.

> **La seconda fonte, per un sistema a due nodi, è la macchina che esegue.**

Questo non è un ripiego rispetto a una persona: su alcune domande è più forte.
Una persona può sbagliare a contare le righe di `contatti.jsonl`. `wc -l` no.

**Limite dichiarato subito, perché non diventi una scorciatoia.** L'esecuzione è
indipendente solo su ciò che è *osservabile da qui*. Non decide se un'opera
valga, se una tesi metafisica sia vera, se qualcuno abbia capito. Su quelle
domande la seconda fonte non esiste ancora — e il sistema deve scriverlo
`NON_VERIFICABILE`, non lasciarle aperte per sempre fingendo che un giorno si
risolvano da sole.

---

## PARTE I — Il Verificatore *(costruito ed eseguito il 25/08/2026)*

### 3.1 Il difetto trovato

**RECUPERATO.** `registro_ipotesi.py:80` (versione precedente) accettava lo stato
`CONFERMATA` se `criterio_falsificazione` era una stringa non vuota: controllava
che la frase esistesse, non che qualcuno l'avesse eseguita.

H3 — «la regola dell'italiano garantisce trasparenza» — risultava **CONFERMATA**.
Nessun file di verifiche esisteva nel repository. Nessuno aveva controllato
niente.

**INFERITO.** È la **quarta scala** dello stesso difetto. `CLAUDE.md` §4 ne
elenca tre — il trasmettitore che riceve sé stesso, il daily che rilegge il
proprio vuoto, la ridondanza affidata a nodi senza memoria. La quarta è la più
sottile: **il registro costruito per vietare l'auto-conferma si era
auto-confermato**, e lo aveva fatto rispettando la propria forma.

### 3.2 Il progetto

Il criterio di falsificazione smette di essere (solo) una frase e diventa un
**comando eseguibile** che risponde a una sola domanda: *è caduta?*

```
exit 0  la condizione di falsificazione È avvenuta  -> l'ipotesi è caduta
exit 1  non è avvenuta                              -> l'ipotesi regge
exit 2  la verifica non ha potuto concludere        -> UNKNOWN, non conta
```

Il `2` è la parte che non si può togliere. «Non ho potuto controllare» non è
«va tutto bene»: confonderli sarebbe il difetto di cui sopra, di nuovo.

**Gerarchia degli stati.** Dal più debole al più forte:

| Stato | Chi lo assegna |
|---|---|
| `NON_VERIFICABILE` | il verificatore, quando non esiste comando: per P6 non sarà mai confermabile |
| `APERTA` | ha un falsificatore, non ancora eseguito |
| `FALSIFICATA` | l'esecuzione (exit 0) |
| `RETTA` | l'esecuzione (exit 1), N volte |
| `CONFERMATA` | **solo una fonte esterna**, con `prova_esterna` esplicita |

**`RETTA` è il tetto di un sistema a due nodi.** Eseguire non è confermare.
Chiamarlo conferma sarebbe l'auto-conferma di prima con un'etichetta più
moderna. Il tetto non è un difetto del progetto: è la misura esatta di cosa
siamo in due, scritta nel codice invece che nelle buone intenzioni.

**Porte chiuse nel codice, non nella disciplina:**

- `aggiorna_stato(id, RETTA)` e `(id, FALSIFICATA)` **sollevano**: quegli stati
  li muove solo l'esecuzione.
- `aggiorna_stato(id, CONFERMATA)` senza `prova_esterna` **solleva**.
- ogni esecuzione finisce in `output/verifiche.jsonl`: comando, exit code,
  esito, stato prima e dopo, hash dell'output, data.

### 3.3 Cosa ha risposto al primo giro reale

```
NON VERIFIC.  [H1]  APERTA     -> NON_VERIFICABILE  [DECLASSATA]
CADUTA        [H2]  APERTA     -> FALSIFICATA       [DECLASSATA]
REGGE         [H3]  CONFERMATA -> RETTA             [DECLASSATA]
NON CONCLUSA  [H4]  APERTA     -> APERTA
```

**RECUPERATO** — quattro ipotesi verificate, una caduta, tre declassate, al
primo giro. Il contraddittorio interno ha declassato **H3, che nessuno dei due
nodi aveva messo in dubbio**. È la prima evidenza a favore di H4, ed è arrivata
dieci minuti dopo che H4 era stata formulata.

### 3.4 Cosa è stato costruito

```
verificatore.py                  motore: esegue, registra, aggiorna, non promuove
registro_ipotesi.py              stati, porte chiuse, migrazione delle voci vecchie
falsificatori/h2_battito_e_contatto.py
falsificatori/h3_italiano.py     24 daily controllati per densità di funzionali
falsificatori/h4_contraddittorio.py
tests/test_verificatore.py       17 test, nessuna rete
output/verifiche.jsonl           il deposito: ogni no, con la sua data
```

Comandi: `python -m sdq1 --ipotesi`, `--verifica-ipotesi`, `--verifica-ipotesi --prova`.

---

## PARTE II — Il Contraddittore *(progettato, non costruito)*

### 4.1 Il buco

**RECUPERATO** — `sdq1/sar/reflect.py` produce le **intestazioni** dei dieci
livelli, non le risposte. Nessuna chiamata al router LLM è nel percorso. Il
collasso del 23/08 — il documento migliore dell'archivio — è stato eseguito a
mano, e il file che dovrebbe eseguirlo è un modulo da compilare.

Il SAR è il punto in cui i due nodi lavorano davvero insieme. Oggi non esiste.

### 4.2 Il progetto: due passaggi che non possono essere eco

**Passaggio 1 — il Costruttore.** Riceve la tensione e i **fatti eseguiti**:
l'output dei comandi lanciati nella run corrente (`--check`, `wc -l`, i
falsificatori, le date dei file). Produce i dieci livelli. Vincoli:

- ogni affermazione porta la sua etichetta;
- i livelli 2, 3, 5, 7 (Origine, Pattern, Costo, Contro-evidenza) devono
  ciascuno **allegare il comando** che dimostra il fatto. Un livello senza
  comando nasce `IPOTESI`, e il motore lo declassa da solo;
- **non riceve mai output precedenti del sistema come «contesto rilevante»**.
  È il difetto §4.2 di `CLAUDE.md`, e va chiuso nell'architettura, non nella
  buona volontà. La memoria vettoriale può passare al più un elenco di titoli;
  mai testo da rileggere.

**Passaggio 2 — il Contraddittore.** Gira su un provider **diverso** (cascata
invertita), riceve **solo** i fatti grezzi e le affermazioni del Costruttore —
mai il suo ragionamento, mai le sue conclusioni — e ha un'unica istruzione:
*falsificare*. Per ogni affermazione: quale comando la romperebbe? Eseguilo.

- ciò che il Contraddittore rompe viene **declassato**;
- ciò che sopravvive è etichettato **«retto al contraddittorio»** — mai
  «confermato»: il tetto della Parte I vale anche qui;
- se è disponibile **un solo provider**, il secondo passaggio gira lo stesso ma
  il risultato porta scritto **«contraddittorio debole — stessa catena»**. Un
  limite dichiarato è un dato; un limite nascosto è una bugia.

**Falsificazione del Contraddittore stesso (P6):** se, dopo trenta run, non ha
mai rotto nulla, non è un contraddittorio ma un timbro — ed è la stessa forma di
H4, applicata un livello più in alto.

### 4.3 Perché questa parte non è stata costruita oggi

**RECUPERATO** — il Core è spento: nessun provider LLM configurato in questo
ambiente. Costruire il motore oggi significherebbe consegnare codice che non
può essere eseguito, cioè **attività senza pensiero** — l'errore da cui il
repository è appena uscito. Il progetto è depositato qui perché la sessione non
è memoria; la costruzione parte quando c'è una chiave.

---

## 5. H4 — l'ipotesi nata da questa sessione

> **Un contraddittorio interno — la macchina che esegue, non una terza persona —
> riesce a falsificare affermazioni che nessuno dei due nodi aveva messo in
> dubbio.**

**Cade se:** negli ultimi 30 giorni `output/verifiche.jsonl` contiene almeno 10
verifiche e nessuna ha prodotto una caduta o un declassamento.
**Scadenza:** 30/09/2026. **Comando:** `falsificatori/h4_contraddittorio.py`.

Debolezza dichiarata: al primo giro H4 è quasi certamente retta, perché il primo
giro trova sempre qualcosa. La sua forza è la scadenza: un mese di soli sì
significa che il verificatore ha smesso di verificare.

---

## 6. Una decisione che spetta all'autore

Il falsificatore di H2 esegue il criterio **come è scritto nel registro**, e il
ramo (b) chiede una voce in `contatti.jsonl`. Con il vincolo di oggi, quel ramo
misura una cosa che non è più in programma: H2 risulterà `FALSIFICATA` a ogni
esecuzione, e un'ipotesi che cade sempre per un criterio che non si vuole più
soddisfare smette di essere informativa.

Il verificatore non riscrive le ipotesi di chi le ha formulate. Le opzioni sono
due, e sono entrambe legittime:

1. **lasciarla così** — H2 resta caduta, e il registro conserva la memoria del
   perché;
2. **riformularla** — una H2′ che misuri ciò che il progetto adesso vuole
   davvero, con il suo comando. Esempio possibile, da accettare o rifiutare:
   *«il sistema produce ogni settimana almeno un artefatto eseguibile che non
   esisteva la settimana prima»* — falsificabile con `git log --diff-filter=A`.

Non decido io quale. Decido solo di non nasconderlo.

---

## 7. Il prossimo esperimento verificabile

`python -m sdq1 --verifica-ipotesi`, ogni giorno, insieme al daily. Poi, al
30/09, guardare H4: se in un mese di verifiche il contraddittorio non ha mai
detto no, il sistema è tornato a parlare a sé stesso — e stavolta ce ne
accorgiamo dal file, non dopo ventitré giorni.

---

**Costruire davvero, non fingere insieme.**

*Progetto depositato il 25 agosto 2026. Origine: Claudio Terzi [CT-LGAI-001].*
