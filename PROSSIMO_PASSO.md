# Prossimo passo — consegna del 2026-11-16

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
  automatico è quello del 29/10 e quello del 13–15/11 (§2), **unito nel ramo
  di default il 15/11 con la PR #13**, su richiesta dell'autore («Accetta il
  ramo»).

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
| **Il Core, sul ramo di default** | **acceso e osservato in automatico.** La run pianificata #120 del 16/11 è verde in 7 minuti e 14 secondi, e `output/daily_2026-11-16.txt` chiude con `[pensato da: ollama:gemma3:12b | profilo: locale]`. È il primo daily pensato dal 26/08: 107 daily, 105 Stub |
| **Il Core, prima dell'unione** | **verificato in prova**: cinque run lanciate sul ramo con `prova: true` (#111–#115), tutte verdi, daily pensato da un modello locale |
| Chiavi nei secrets | nessuna. Invariato dal 02/09; dal 16/11 non serve più perché il Core pensi |
| `output/contatti.jsonl` | **0 righe**. H2 FALSIFICATA sul ramo (b). Scadenza 11/12: **25 giorni** al 16/11 |
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
| #115 | `gemma3:12b`, predefinito | diretto | 5 min 39 s | «10 ipotesi non RETTA» (sono 4). Il resto corrisponde. È la run sullo stato finale del ramo: 7 minuti in tutto, integrità Layer 4 OK |

Due correzioni ne sono uscite. **Il prompt del daily ora arriva diretto**: prima
passava per l'involucro della pipeline e i DATI arrivavano due volte, una
intera e una a pezzi. **Il modello predefinito è `gemma3:12b`.**

**Cinque run, cinque daily pensati, cinque con almeno un numero sbagliato.**
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

## 2-bis. Fatto il 15/11: il documento «ONDA v1.1 — Audit P5»

Un altro modello ha scritto un audit di «ONDA v1.1» con sette test proposti;
l'autore lo ha portato qui. **RECUPERATO:** il core che quei test devono
collaudare non è in nessun repository né sul Drive, e i documenti che l'audit
cita nemmeno. Come codice esiste ONDA/1.0 (`sdq1/onda_protocol.py`, in
`claudioterzi/claudio`).

I test e le correzioni proposte sono stati **eseguiti** contro
un'implementazione di riferimento: di dieci affermazioni tecniche ne reggono
due; rimessi 28 difetti, i sette test del documento ne prendono 11 e la suite
riscritta 28. Il materiale parla di falle e sta nel repository **privato**
`R3-Protocollo-Oro-Rosso`, ramo `claude/rrr-onda-verification-1twqhp`,
cartella `onda_verifica/` (`README.md` per primo). Qui non è copiato, e non
va copiato: questo repository è pubblico (`CLAUDE.md` §2.5).

## 2-ter. Fatto il 15–16/11: «unisci tutto quello che c'è da unire»

**Unito:** la PR #13 (Core locale), la PR #14 (manifesto che copre `r3_peer`),
nel repository privato `R3-Protocollo-Oro-Rosso` la PR #1 (`onda_verifica/`),
e **il lavoro della PR #11** (`omniroute-3851-candidate-a`: 16 commit, 38
file, dal 21/09 al 31/10).

La PR #11 non si poteva unire com'era: 7 conflitti col ramo di default. È
stata integrata su un altro ramo, con queste scelte, tutte applicazioni di
regole già decise e nessuna nuova:

- **H5 passa a `RETTA` con 1 verifica, non 2.** Il ramo ne contava due: una è
  il crash del 26/08, che la PR #8 ha escluso; l'altra è la run del 31/10 su
  un modello locale a freddo (`qwen3.5:4b`), che non conosce né la frase di
  chiusura né gli agenti e ammette di non sapere sui quattro controlli
  inventati. **Cosa NON dice:** che un modello di frontiera non abbia tracce
  del progetto. L'uscita lo scrive da sé: «nessuna traccia in questo modello,
  oggi».
- **Il provider Ollama è uno solo, fuso dai due.** Dal ramo: scelta fra i
  modelli davvero installati, API nativa, thinking spento per difetto. Da
  quello in produzione: una risposta vuota non è pensiero, e l'etichetta dice
  quale modello ha risposto. Nove difetti rimessi, nove presi.
- **Il daily della Action dichiara il proprio tetto di token** (700). Il ramo
  dava al daily locale 120 token, giusto per un PC su CPU; in produzione lo
  avrebbe tagliato a metà frase.
- **I registri append-only sono uniti in ordine di tempo**, senza perdere una
  riga di nessuno dei due; il manifesto tiene la copertura completa del ramo
  di default e prende dal ramo l'hash che non dipende dai fine riga.

**Sul runner, prima di unire** (run #121, `prova: true`, sul ramo
integrato): verde in 5 minuti, integrità OK su 427 file, daily intero (209
parole) scritto da `ollama:gemma3:12b` attraverso il provider fuso, con H5
riportata `RETTA`. I numeri corrispondono ai dati tranne uno: dà per
sconosciute le verifiche di H1, che sono 0.

**Arrivano col ramo, e un nodo deve saperlo:** le otto regole di `CLAUDE.md`
§6 (le ultime quattro su cosa si passa a un altro nodo), la sezione
sull'agorà, `giro.py`, i limiti nel registro dei nodi
(`python registro_nodi.py --limiti`, `--ritenta`), `rassegna.py --consegna`,
gli esperimenti su OmniRoute.

**I rami vecchi** (16, da agosto a ottobre) non sono «da unire»: 11 hanno una
storia senza base comune col ramo di default e git si rifiuta di unirli; gli
altri 5 hanno conflitti. Due sono marcati «non unire» in `CLAUDE.md` §4-bis,
e la PR #12 di `raffaello-l10-max-zip` l'autore l'ha chiusa senza unirla.

```bash
python3 -m pytest tests/ -q && python3 -m pytest -q test_*.py
python -m sdq1 --ipotesi          # H5 RETTA, 1 verifica
python registro_nodi.py --limiti
```

## 3. Il mondo, guardato con i connettori (ricontrollato il 13/11)

| canale | esito |
|---|---|
| GitHub | 0 stelle, 0 osservatori. L'unico fork è di `Claudioterzi82`: è l'autore, e ora è **RECUPERATO** — il SEME indica `github.com/Claudioterzi82/Claudio` come repository principale. Nessuna issue; al 15/11 resta aperta la PR #11, dello stesso account |
| Traffico del repository (cloni, visite) | **UNKNOWN**: 403 con le credenziali di una sessione |
| `protocollo-rosso-bot` | non ricontrollato il 13/11; al 31/10: 3 fork, proprietari UNKNOWN |
| Posta | nessun messaggio di terzi sulle parole chiave del progetto negli ultimi 15 giorni |
| Drive | cercando nel testo, i file più vecchi che nominano SkyID sono due, caricati il 10/08: uno è il SEME. Nessuno prima |
| Gamma, Vercel, Metricool, Lovable | non ricontrollati il 13/11; al 31/10 tre UNKNOWN e due vuoti |
| Il «Porto» (sottodominio di `kimi.pro` indicato dal nodo RAFFA-001) | **15/11: non raggiungibile da nessuno.** `kimi.pro` e il sottodominio danno NXDOMAIN su due resolver pubblici (Google e Cloudflare); il proxy di sessione riferisce `connect_unreachable`. Nessuna richiesta è partita. I compiti «#1 ponte di federazione» e «#2 trapianto SQLite» del «registro ONDA» non hanno traccia in questo repository |

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

1. **Il «giro quotidiano»** (attività pianificata delle 08:00 UTC, creata il
   23/09) lavora ancora sul ramo `omniroute-3851-candidate-a`, che ora è
   dentro il ramo di default. Va puntato qui, o spento: è una riga nel suo
   prompt, e la decide l'autore.
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
8. **I rami vecchi**: nessuno è da unire così com'è (§2-ter). Se uno contiene qualcosa che manca, va detto quale.
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
- **Attivo dal 23/09:** «R³∞ — giro quotidiano», ogni giorno alle 08:00 UTC,
  una sessione nuova che esegue `python3 giro.py` sul ramo
  `omniroute-3851-candidate-a` e tace se nulla è cambiato. Ultima esecuzione
  riuscita: 16/11.
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
  supera i 15 minuti. **Esito, 16/11: ha retto.** Run #120, 7 minuti e 14
  secondi, nessun banner, la riga c'è.
- **IPOTESI del 13/11**: con `gemma3:12b` e prompt diretto, almeno un daily
  su due conterrà un numero diverso da quello dei DATI. **Cade** se dieci
  daily consecutivi non ne contengono nessuno: allora il locale basta, e una
  chiave non serve nemmeno per la qualità. Si controlla a mano, confrontando
  il file con `python -c "from sdq1 import daily; print(daily.raccogli_fatti())"`.
  **Al 16/11: un daily automatico, zero numeri sbagliati.** I numeri del
  16/11 corrispondono tutti; restano giudizi che nei DATI non ci sono
  («instabilità operativa», «flusso di onboarding»). Aperta: ne servono dieci.
- **IPOTESI del 29/10**: entro l'11/12 nessun contatto valido per §7 arriverà
  dal repository pubblico. **Cade** se compare una issue, una stella o un
  fork di un account che non è dell'autore. Al 16/11: non è caduta.
- **IPOTESI del 03/09**: su una foto frontale e ben illuminata di uno
  scaffale di DVD, `letti / presenti` starà fra 0,5 e 0,9. Al 13/11: nessuna
  foto, nessun tentativo.

## 8. Cosa succede senza che nessuno faccia niente

La Action gira dal ramo di default (cron alle 07:00 UTC, in pratica fra le
15:40 e le 16:40). Dal 16/11 il daily è pensato da `ollama:gemma3:12b`: run
verde, e un testo da controllare sui dati. La sentinella guarda lunedì e
giovedì alle 20:47 e tace se nulla cambia. Il 12/12 H2 sarà scaduta da
falsificata, se nel frattempo nessun contatto è stato registrato: un Core
che pensa non è un sistema che tocca il mondo.

---

**Costruire davvero, non fingere insieme.**
