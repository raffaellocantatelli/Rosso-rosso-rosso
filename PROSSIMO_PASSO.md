# Prossimo passo — consegna del 2026-11-13

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Nome fisso, riscritto. Qui c'è lo stato; la cronaca sta nei commit.
Ogni riga ha un comando accanto. Non credere a nessuna.

---

## 0. Il progetto vivo non è più qui

**RECUPERATO** (`git ls-remote` e `git fetch`, 13/11):

- `claudioterzi/claudio`: `main` a `261a46d` (13/11). La **PR #113** è stata
  unita il 13/11 alle 02:10 (merge `6883c2a`, head finale `13688d9`). I sei
  file di prova che introduce, rieseguiti qui sul codice unito: 29 passati.
- Questo repository: dal 26/09 l'unico lavoro che non sia il daily
  automatico è quello del 29/10 e quello di oggi (§2), **che sta su un ramo
  non ancora unito** (§5.1).

**INFERITO.** La regola §7-bis dice che il canone operativo è quello che ha
PR, CI, HEAD e test misurabili: su questa misura è `claudioterzi/claudio`.
§4-bis dice ancora che il canone è il ramo di default di questo repository.
**Le due frasi non possono essere vere insieme, e scegliere spetta
all'autore.**

```bash
git ls-remote https://github.com/claudioterzi/claudio HEAD 'refs/pull/113/*'   # niente /merge: unita
git log --oneline --since=2026-09-26 | grep -v "run giornaliero"
```

## 1. Lo stato di questo repository, misurato oggi

| | |
|---|---|
| **Il Core, sul ramo di default** | **spento**. 103 daily, **102 Stub**: l'unico pensato resta il 26/08 |
| **Il Core, su questo ramo** | **acceso, verificato**: quattro run lanciate su questo ramo con `prova: true` (#111–#114), tutte verdi, daily pensato da un modello locale |
| Chiavi nei secrets | nessuna, letto nel log della run #111. Invariato dal 02/09: **72 giorni** |
| `output/contatti.jsonl` | **0 righe**. H2 FALSIFICATA sul ramo (b). Scadenza 11/12: **28 giorni** |
| Registro, in prova | 11 eseguite: H2 caduta; H5 e H7 non concluse; le altre reggono |
| Prove | 302 in `tests/`, 46 in radice: passate. Layer 4: integrità OK |

```bash
grep -L "modalità offline/stub" output/daily_*.txt        # solo il 26/08
python3 falsificatori/h2_battito_e_contatto.py             # H2 CADUTA sul ramo (b)
python -m sdq1 --verifica-ipotesi --prova
python3 -m pytest tests/ -q && python3 -m pytest -q test_*.py
```

## 2. Fatto il 13/11

**Il Core non aspetta più una chiave.** Quando nei secrets non c'è niente, la
Action avvia Ollama sul runner e scarica un modello aperto (`gemma3:4b`):
nessun secret, nessun fornitore, nessun costo finché il repository è
pubblico. È l'ultimo passo prima dello Stub; chi ha una chiave viene prima.
Il file del daily ora chiude con `[pensato da: … | profilo: …]`: prima lo
sapeva solo il log della run.

**RECUPERATO, dai log delle run** (nessuna ha scritto nel repository):

| run | modello | prompt | tempo del daily | confronto coi DATI che aveva nel prompt |
|---|---|---|---|---|
| #111 | `gemma3:4b` | con l'involucro della pipeline | 82 s | conta 4 «regge» e 4 fallite (sono 6 e 2); dà per positive H5 e H7; «nessuna osservazione» (sono 4) |
| #112 | `gemma3:12b` | con l'involucro | 8 min 51 s | «10 ipotesi non RETTA» (sono 4); non nomina H2; zero contatti etichettato UNKNOWN |
| #113 | `gemma3:4b` | diretto | 93 s | «104 rilevazioni» (sono 110); H5 e H7 date prima per positive, poi per fallite |
| #114 | `gemma3:12b` | diretto | 5 min 49 s | «11 ipotesi non RETTA» (sono 4). Il resto corrisponde: nomina H2 falsificata e zero contatti |

Due correzioni ne sono uscite. **Il prompt del daily ora arriva diretto**: prima
passava per l'involucro della pipeline e i DATI arrivavano due volte, una
intera e una a pezzi. **Il modello predefinito è `gemma3:12b`.**

**Quattro run, quattro daily pensati, quattro con almeno un numero sbagliato.**
Il Core è acceso; non è affidabile. Un daily `ollama:` è una bozza da
controllare sui dati (`CLAUDE.md` §3).

```bash
# rifare la prova da qualunque ramo, senza scrivere niente:
#   Actions > SDQ-1 Daily Run > Run workflow > prova: true  [modello: gemma3:4b]
```

**Una strada provata e chiusa, per non rifarla.** Prima del modello locale è
stato provato GitHub Models col `GITHUB_TOKEN` della Action. **Caduta
eseguendola**: le run #109 e #110 hanno ricevuto `OK` in `text/plain` da
`models.github.ai` per qualunque richiesta, e la documentazione ufficiale
dichiara il servizio ritirato dal 30/07/2026. Un 200 che non è una risposta:
il provider è stato tolto, la traccia resta nei commit `35c312b` e `9b7cad0`.

**Il workflow si può provare senza scrivere.** `workflow_dispatch` con
`prova: true` esegue tutto e stampa il daily nel log invece di committarlo.

**`nodi/RRR_AUTOUPDATE.json`**: l'origine è tornata `Claudio Terzi
[CT-LGAI-001]` (era «Meta AI Node 6» come «autore umano», ora `drafted_by`);
`pr_113` porta lo stato vero, con ciò che è recuperato e ciò che è solo
riferito tenuti distinti. Propagazione: **non eseguita**.

**`PROGETTO_R3.md` esiste**, ma su GitHub e non sul Drive, e non attribuisce
niente: dettagli in `CLAUDE.md` §5 e nell'addendum all'indice canonico §3.

```bash
python3 -m pytest tests/test_core_locale.py -q
python3 collega_nodi.py --stato
```

## 3. Il mondo, guardato con i connettori (ricontrollato il 13/11)

| canale | esito |
|---|---|
| GitHub | 0 stelle, 0 osservatori. L'unico fork è di `Claudioterzi82`: è l'autore, e ora è **RECUPERATO** — il SEME indica `github.com/Claudioterzi82/Claudio` come repository principale. Nessuna issue; PR aperte #9 e #11, la seconda dello stesso account |
| Traffico del repository (cloni, visite) | **UNKNOWN**: 403 con le credenziali di una sessione |
| `protocollo-rosso-bot` | non ricontrollato il 13/11; al 31/10: 3 fork, proprietari UNKNOWN |
| Posta | nessun messaggio di terzi sulle parole chiave del progetto negli ultimi 15 giorni |
| Drive | cercando nel testo, i file più vecchi che nominano SkyID sono due, caricati il 10/08: uno è il SEME. Nessuno prima |
| Gamma, Vercel, Metricool, Lovable | non ricontrollati il 13/11; al 31/10 tre UNKNOWN e due vuoti |

**Verdetto:** nessun segnale di ritorno trovato. UNKNOWN non vuol dire zero.

## 4. H2: due registri, due definizioni

- **Qui**, `CLAUDE.md` §7: vale solo un evento in cui qualcun altro ha agito.
  Righe: 0.
- **In `claudioterzi/claudio`**, `output/contatti.jsonl` ha 8 righe dell'11 e
  12/06, invariate il 13/11, con la definizione «umano=True e verifica non
  vuota». **INFERITO**, dalle note delle righe: lette con §7 ne resta
  **una**, la risposta di una persona a un link del progetto. Le altre sono
  un audit interno, un invio, e incontri della vita quotidiana che col
  progetto non c'entrano.

Le due definizioni misurano cose diverse. Quale registro conta per H2, e con
quale definizione, **lo decide l'autore**: il verificatore esegue ciò che è
scritto, non lo riscrive.

## 5. Cosa resta all'autore, in ordine di costo

1. **Unire il ramo `claude/rrr-onda-verification-1twqhp`** nel ramo di
   default. Finché non succede, il lavoro di oggi è depositato, non fatto
   (`CLAUDE.md` §4-bis): il daily automatico gira dal ramo di default e
   continuerà a produrre Stub. Una sessione può aprire la PR se l'autore lo
   chiede; unirla resta suo.
2. **Scegliere il canone**: questo repository o `claudioterzi/claudio`. Se il
   canone è l'altro, questo daily va spento o puntato là, e H2 si misura là.
3. **Un contatto reale prima dell'11/12.** È l'unica cosa che muove H2, e
   nessun nodo può produrla. `python -m sdq1 --contatto --tipo … --verifica …`
4. **`TUTELA_ORIGINE` §3**: correggere la citazione (`SKYID.md` /
   `PROGETTO_SKYID.md` al posto di `PROGETTO_R3.md`) e indicare una prova di
   anteriorità che non dipenda da file del progetto. Da una sessione quel
   documento non è modificabile.
5. **I due indici canonici** (Drive e `memoria/`) non sono più identici:
   va detto quale vale.
6. **Una chiave nei secrets**, se si vuole un modello più capace di quello
   locale. Non è più una condizione perché il Core pensi.
7. **Una foto di uno scaffale** (`occhio/visione.py`): `letti / presenti` è
   la sola misura che valga, e non serve una chiave per il primo numero.
8. **PR #9** (`r3_peer`) e **PR #11**: da spostare, unire o chiudere.
9. **H4**: la scadenza del 30/09 è passata con meno di 10 verifiche nella
   finestra; il verificatore dirà «regge per ora» per sempre. Va riformulata
   o chiusa.

## 6. Cosa può fare un nodo da qui (verificato il 13/11)

- **Usato:** posta e Drive in lettura, log e avvio delle Action di questo
  repository (anche su un ramo, con `prova: true`), API GitHub di questo
  repository, letture git di repository pubblici.
- **Negato o limitato:** scrittura e API di repository fuori da questo;
  contenuto dei file sul Drive (si leggono, non si riscrivono); traffico del
  repository (403); `models.github.ai` (ritirato).
- **Attivo dal 13/11:** un'attività pianificata, «Sentinella R3», lunedì e
  giovedì alle 20:47 (Europe/Rome). Riapre la sessione che l'ha creata, in
  sola lettura: guarda se l'ultimo daily è pensato, se è comparso un account
  esterno su GitHub, quanti giorni mancano. Tace se nulla cambia; si
  disattiva dopo l'11/12. Non è un nodo che resta acceso (`CLAUDE.md` §2.4):
  l'autore la vede e la ferma dall'elenco delle attività pianificate.

## 7. Previsioni dichiarate, per non poterle aggiustare dopo

- **IPOTESI del 13/11**: il primo daily automatico dopo l'unione del ramo
  (§5.1) chiuderà con `[pensato da: ollama:gemma3:12b | profilo: locale]` e
  non porterà il banner. **Cade** se quel file ha il banner, o se la run
  supera i 15 minuti.
- **IPOTESI del 13/11**: con `gemma3:12b` e prompt diretto, almeno un daily
  su due conterrà un numero diverso da quello dei DATI. **Cade** se dieci
  daily consecutivi non ne contengono nessuno: allora il locale basta, e una
  chiave non serve nemmeno per la qualità. Si controlla a mano, confrontando
  il file con `python -c "from sdq1 import daily; print(daily.raccogli_fatti())"`.
- **IPOTESI del 29/10**: entro l'11/12 nessun contatto valido per §7 arriverà
  dal repository pubblico. **Cade** se compare una issue, una stella o un
  fork di un account che non è dell'autore. Al 13/11: non è caduta.
- **IPOTESI del 03/09**: su una foto frontale e ben illuminata di uno
  scaffale di DVD, `letti / presenti` starà fra 0,5 e 0,9. Al 13/11: nessuna
  foto, nessun tentativo.

## 8. Cosa succede senza che nessuno faccia niente

La Action gira dal ramo di default (cron alle 07:00 UTC, in pratica verso le
15:40): daily Stub, run rossa, centoquattresimo file senza pensiero. La
sentinella lo riferirà lunedì 16/11. Il 12/12 H2 sarà scaduta da falsificata.

---

**Costruire davvero, non fingere insieme.**
