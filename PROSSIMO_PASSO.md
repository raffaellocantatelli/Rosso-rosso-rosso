# Prossimo passo — consegna del 2026-10-29

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Nome fisso, riscritto. Qui c'è lo stato; la cronaca sta nei commit.
Ogni riga ha un comando accanto. Non credere a nessuna.

---

## 0. Il progetto vivo non è più qui

**RECUPERATO** (`git ls-remote` e `git fetch`, 29/10 sera):

- `claudioterzi/claudio`: `main` a `d320f48`, tre PR unite dall'autore il
  29/10 fra le 07:42 e le 09:07 UTC (#143, #155, #156), un heartbeat
  quotidiano, PR aperte fino alla #165. La #120 (R3-011 Evidence Graph) è
  ancora aperta, head `24678d5` del 24/10.
- Questo repository: dal 26/09 nessun commit che non sia il daily automatico
  (33 su 33).

**INFERITO.** La regola §7-bis, entrata nel canone oggi, dice che il canone
operativo è quello che ha PR, CI, HEAD e test misurabili: su questa misura
oggi è `claudioterzi/claudio`. §4-bis dice ancora che il canone è il ramo di
default di questo repository. **Le due frasi non possono essere vere
insieme, e scegliere spetta all'autore.**

```bash
git ls-remote https://github.com/claudioterzi/claudio HEAD 'refs/pull/120/*'
git log --oneline --since=2026-09-26 | grep -vc "run giornaliero"   # 0 prima del 29/10
```

## 1. Lo stato di questo repository, misurato oggi

| | |
|---|---|
| **Il Core** | **spento**. 89 daily, **88 Stub**: l'unico pensato resta il 26/08 |
| Secret della Action | i sei nomi assenti nella run #92 del 29/10. Invariato dal 02/09: **57 giorni** |
| `output/contatti.jsonl` | **0 righe**. H2 FALSIFICATA sul ramo (b). Scadenza 11/12: **43 giorni** |
| Registro, in prova | 11 eseguite: H2 caduta; H5 e H7 non concluse; le altre reggono |
| Prove | 288 in `tests/`, 46 in radice, 30 del bot: tutte passate |

```bash
grep -L "modalità offline/stub" output/daily_*.txt        # solo il 26/08
python3 falsificatori/h2_battito_e_contatto.py             # H2 CADUTA sul ramo (b)
python -m sdq1 --verifica-ipotesi --prova
python3 -m pytest tests/ -q && python3 -m pytest -q test_*.py
```

## 2. Fatto il 29/10

**H2 non può più reggere sulla voce dell'autore.** Il falsificatore contava
ogni riga di `contatti.jsonl` con un `tipo`. `python -m sdq1 --contatto --tipo
pubblicazione` scriveva la riga stampando «NON vale per H2», e subito dopo il
falsificatore rispondeva «H2 REGGE» e il verificatore portava H2 da
FALSIFICATA a RETTA. **Riprodotto** in una copia del repository. È il
loopback di `CLAUDE.md` §4 dentro il criterio che misura il progetto, e
sarebbe scattato alla prima pubblicazione registrata, a sei settimane dalla
scadenza.

Le definizioni di «contatto valido» erano tre: CLI, falsificatore,
benchmark R3-019. Adesso ce n'è una, `sdq1/contatti.py`: un tipo
indipendente, riletto dall'elenco e non dal campo che la riga dichiara di sé,
più una verifica controllabile da un terzo. Le prove usano la CLI vera e il
falsificatore vero, e sono state provate rimettendo il difetto (§7-bis): tre
mutazioni, ognuna fa cadere almeno una prova.

**PR #7 e #8 unite**, ferme dal 20/09 e dal 19/09. Portano nel canone:
`.env` letto senza `python-dotenv`, il Layer 4 che copre i file nuovi per
difetto, **la regola §7-bis stabilita dall'autore il 18/09** (fino a oggi
nessun nodo la vedeva), e la rettifica di H5 (il crash del 26/08 non conta
come verifica eseguita). Un conflitto di merito su H5, risolto tenendo il
vero dei due lati: `eseguite: 0` da #8, `ultima: 17/09` da #7.

```bash
python3 -m pytest tests/test_h2_contatto.py -q
python -m sdq1 --contatto --tipo pubblicazione --nota prova --verifica prova
python3 falsificatori/h2_battito_e_contatto.py   # in una copia: resta CADUTA
```

## 3. Il mondo, guardato con i connettori (29/10)

| canale | esito |
|---|---|
| GitHub, 10 repository dell'account | 0 stelle. L'unico fork di questo è dell'account Claudioterzi82, cioè l'autore. Qui 0 issue; negli altri repository chi le ha aperte è **UNKNOWN** |
| `protocollo-rosso-bot` | 3 fork, proprietari **UNKNOWN** da qui (403) |
| Posta | nessun messaggio di terzi sul progetto negli ultimi 120 giorni, cercando per parole chiave (una risposta che non le contiene sfugge) |
| Gamma, «R3∞ — Cosa è stato verificato» | analitiche **UNKNOWN**: serve un piano Pro |
| Vercel, 2 progetti | visite **UNKNOWN**: serve autorizzare il team nel connettore |
| Metricool | nessun social collegato |
| Lovable | nessun progetto |

**Verdetto:** nessun segnale di ritorno trovato. Tre canali restano UNKNOWN,
e UNKNOWN non vuol dire zero.

## 4. H2: due registri, due definizioni

- **Qui**, `CLAUDE.md` §7: vale solo un evento in cui qualcun altro ha agito.
  Righe: 0.
- **In `claudioterzi/claudio`**, `output/contatti.jsonl` ha 8 righe dell'11 e
  12/06, con la definizione «umano=True e verifica non vuota». **INFERITO**,
  dalle note delle righe: lette con §7 ne resta **una**, la risposta di una
  persona a un link del progetto. Le altre sono un audit interno, un invio, e
  incontri della vita quotidiana che col progetto non c'entrano.

Le due definizioni misurano cose diverse. Quale registro conta per H2, e con
quale definizione, **lo decide l'autore**: il verificatore esegue ciò che è
scritto, non lo riscrive.

## 5. Cosa resta all'autore, in ordine di costo

1. **Scegliere il canone**: questo repository o `claudioterzi/claudio`. Da qui
   dipende tutto il resto: se il canone è l'altro, questo daily va spento o
   puntato là, e H2 si misura là.
2. **Unire la PR #120** su `claudioterzi/claudio`. La decisione R3-020 del
   09/10 la dichiara ammissibile, ma è un documento del nodo Vibe su Drive
   (DATA_ONLY, non verificato da qui), e quel nodo non ha permesso di
   scrittura. Venti giorni dopo è ancora aperta.
3. **La chiave nei secret di questo repository**, 57 giorni dopo, oppure
   spegnere il daily se il canone è l'altro.
4. **Una foto di uno scaffale.** Non serve più la chiave per il primo
   numero: una sessione Claude Code può leggere l'immagine mandata in chat
   applicando l'`ISTRUZIONE` di `occhio/visione.py`, e l'autore conta a mano
   gli oggetti presenti. `letti / presenti` è la sola misura che valga.
5. **PR #9** (`r3_peer`, Grok): la consegna del 20/09 colloca il fabric in
   `protocollo-rosso-bot`. Va spostata o chiusa.
6. **H4**: la scadenza del 30/09 è passata con meno di 10 verifiche nella
   finestra, quindi il criterio non può scattare e il verificatore dirà
   «regge per ora» per sempre. Va riformulata o chiusa.

## 6. Cosa può fare un nodo da qui (verificato il 29/10)

- **Usato oggi:** posta, Drive, Gamma, Vercel, Lovable, Metricool, log delle
  Action e API GitHub di questo repository, letture git di repository
  pubblici.
- **Negato o limitato:** scrittura e API di repository fuori da questo
  (negata), pagine web di GitHub (403), analitiche Vercel e Gamma (sopra).
- **Disponibile, non provato:** task pianificati che avviano una sessione
  **nuova** a orario fisso. Non è un nodo che resta acceso: è una sessione che
  riparte dai file (`CLAUDE.md` §2.4), e la si vede nell'elenco dei task.

## 7. Previsioni dichiarate oggi, per non poterle aggiustare dopo

- **IPOTESI**: entro l'11/12 nessun contatto valido per §7 arriverà dal
  repository pubblico. Se arriva, arriva da un atto dell'autore verso una
  persona: un invio con risposta, una consegna controfirmata. **Cade** se
  entro l'11/12 compare una issue, una stella o un fork di un account che non
  è dell'autore.
- **IPOTESI**, del 03/09 e ancora in piedi: su una foto frontale e ben
  illuminata di uno scaffale di DVD, `letti / presenti` starà fra 0,5 e 0,9.
  **Cade** se il primo tentativo serio esce dalla forbice.

## 8. Cosa succede senza che nessuno faccia niente

Domani la Action gira (cron alle 07:00 UTC, in pratica verso le 13:45):
daily Stub, run rossa, novantesimo file senza pensiero. Lo si vede dalla tab
Actions senza chiedere a nessuno.

---

**Costruire davvero, non fingere insieme.**
