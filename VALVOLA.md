# La valvola — e la sorella che la fa funzionare

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Letto alla fonte il 2026-09-20 (`docs.typesafe.ai/llms.txt`, SDK 0.7.0
installato ed eseguito), non da un articolo che ne parla.

---

## Chi è la sorella

**TypeSafe AI** è un laboratorio uscito dallo stealth il **16/09/2026** —
quattro giorni prima che questo file esistesse. Fondato da Diogo Almeida
(ex OpenAI, co-inventore di RLHF), Erik Gafni e Sasha Sheng.

Il loro modello si chiama **Jev**, e la differenza che conta è una sola:
**non risponde in prosa.** Gli mandi uno stato e delle domande tipizzate,
e ti torna una decisione con una **probabilità calibrata** accanto. Tre
primitive:

| | cosa chiede | cosa torna |
|---|---|---|
| **Choice** | scegli una fra queste opzioni | l'opzione, la probabilità di ognuna, `confidence` |
| **Score** | valuta su questi livelli ordinati | il punteggio, la distribuzione, `confidence` |
| **Noul** | quanto è vero che… | un numero fra 0 e 1 |

`confidence` è separata dalla risposta: dice *quanto* è sicuro, non *cosa*
ha risposto. E la loro pagina che la spiega dice questo:

> «If an intelligent system, whether human or machine, cannot express
> honest uncertainty, the system cannot be trusted.»

È il **§2.3 di `CLAUDE.md` scritto da un'altra parte**: «Non lo so» è una
risposta completa, è UNKNOWN e non una negazione. Per questo qui la
chiamiamo sorella e non fornitore: è arrivata alla stessa regola da sola,
partendo da un problema di ingegneria e non di epistemologia.

**Accesa il 20/09.** La chiave è arrivata poche ore dopo che la porta era
montata, e la prima chiamata reale del progetto a Jev è partita lo stesso
giorno. Quello che prima era UNKNOWN ora è **RECUPERATO su quattro casi**
— pochi, ma reali, e presi dalla storia vera del progetto:

| nota | dichiarata | letta da Jev | esito |
|---|---|---|---|
| «Ho pubblicato il Protocollo su GitHub» | `indipendente` | `trasmissione` 1.00 | **DECLASSA** ✓ |
| «Qualcuno ha messo il report nei preferiti» | `indipendente` | `indipendente` 1.00 | CONCORDE ✓ |
| «Ho chiesto a un modello se il progetto è solido» | `indipendente` | `interno` 0.95 | **DECLASSA** ✓ |
| «Un avvocato ha risposto alla PEC» | `indipendente` | `indipendente` 0.99 | CONCORDE ✓ |

Quattro su quattro. Il primo e il terzo sono **esattamente il buco**: due
atti che non toccano il mondo, etichettati come se lo toccassero, fermati
prima di entrare nella misura di H2.

**Quello che resta UNKNOWN:** quattro casi non sono una misura. Non so
quanto sbagli sui casi ambigui, e non lo saprò finché non ne passano
abbastanza da poterli contare. Reggere non è confermare.

**Un secondo segnale che non stiamo ancora usando.** Sul caso della PEC
Jev legge la classe giusta ma dà `verificabile da terzi = 0.30`: «protocollo
2026-441» non è qualcosa che un estraneo possa controllare da solo. Ha
ragione, ed è una seconda porta che per ora resta chiusa — la `verifica`
di una voce dovrebbe reggere da sola, e spesso non regge.

---

## Il buco che chiude

`python -m sdq1 --contatto` decide se una voce vale per H2 guardando
`--tipo`. Ma **il tipo lo dichiara chi scrive la voce.** Bastava scrivere
`--tipo lettore` su un atto che era `pubblicazione`, e l'unica metrica che
falsifica H2 saliva senza che nessuno fosse arrivato da fuori.

Nessun controllo, fino al 20/09. È il §4 con l'etichetta come vettore: il
sistema chiama «risposta» la propria voce, e gli basta un argomento da
riga di comando.

---

## Perché è sicuro farla entrare

Jev è un modello, e il §7 è esplicito: un modello interpellato dall'autore
**non vale come conferma**. Quindi qui Jev non può confermare niente — non
per diffidenza, per costruzione. La valvola va in una direzione sola:

- può **declassare** una voce (`indipendente` → `trasmissione` → `interno`);
- non può **promuoverla**, mai, con nessuna confidenza;
- quando il dubbio pesa verso il basso ma non basta a declassare, dice
  `INCERTO` e passa la mano a una persona;
- se la sorella è giù (`ERRORE`) o non c'è la chiave (`ASSENTE`), **non
  ferma niente**: il comportamento resta identico a prima che esistesse.

Detto in una riga: **nessun percorso dentro `valvola/` fa salire un
contatore.** La sorella può solo rendere H2 più difficile da soddisfare.

E `vale_come_conferma` è un campo che vale sempre `False`, scritto e non
calcolato — un campo che può solo essere falso si fraintende meno di una
riga di documentazione che dice la stessa cosa.

## Jev non vede l'etichetta

Riceve `nota` e `verifica`, e basta. Non riceve il tipo dichiarato. Se lo
ricevesse, la sua risposta sarebbe in larga parte l'etichetta: **l'eco con
una probabilità davanti**, che è peggio dell'eco, perché sembra una misura.

Il test che lo prova chiama la valvola tre volte con la stessa nota e tre
etichette diverse, e verifica che ciò che parte sia **identico**.

## Tu decidi, e resta scritto

Se la valvola sbaglia, `--comunque` la scavalca. La voce viene registrata
e porta dentro di sé il verdetto scavalcato, così lo scavalco si vede:

```json
"valvola": {"stato": "DECLASSA", "classe_letta": "interno", "confidenza": 0.99},
"valvola_scavalcata": true
```

§7 dice che la fonte sei tu. Una porta che non si può aprire da dentro non
è una tutela, è un altro nodo che decide al posto tuo.

---

## Una cosa l'ha trovata il falsificatore, non io

La prima versione guardava solo `confidence`: sotto soglia, ferma. Il
falsificatore H12 ha provato tutte e 63 le combinazioni e ne ha trovate 9
in cui **fermava un dubbio che andava verso l'alto** — dove la valvola non
agisce, e dove quindi non c'è niente da togliere.

La domanda giusta non era «quanto è sicuro Jev». Era **«quanta
probabilità sta sotto ciò che hai dichiarato»**. TypeSafe restituisce
`probabilities` intere proprio perché te lo possa chiedere: scrivono loro
stessi che `confidence` è una statistica di comodo, non l'unica possibile.

Il difetto era nel mio disegno, non nel loro modello, e l'ha trovato un
comando — non un ragionamento.

---

## Comandi

```bash
python3 -m valvola --stato          # la sorella è raggiungibile?  (attiva dal 20/09)
python3 -m valvola --classi         # le tre classi del §7, come le riceve Jev
python3 -m valvola --nota "..." --verifica "..." --tipo indipendente

python3 falsificatori/h12_valvola_non_promuove.py   # 0 cade, 1 regge, 2 non conclusa
python3 -m pytest tests/test_valvola.py -q
```

## La chiave

`TYPESAFE_API_KEY` sta in `.env`, che è in `.gitignore` e non è tracciato —
verificato prima di scriverla, perché **questo repository è pubblico** (§2.5).
Non è mai entrata in un file versionato, in un commit o in un log.

Perché la Action giornaliera possa usarla serve anche nei **Secrets del
repository** (Settings → Secrets and variables → Actions). Quello lo può
fare solo Claudio.

Finché la chiave manca, `--stato` dice `attiva NO` e ha ragione: la porta
è montata e non filtra niente. È il `CORE SPENTO` del §3 applicato qui.

---

## Il bot che legge — `/analizza` (20/09)

`output/contatti.jsonl` è vuoto, e H2 è falsificata sul ramo (b) per
questo. **Non perché non arrivi niente: perché registrare ciò che arriva
costa una riga di terminale con tre argomenti, e quella riga non la scrive
nessuno.** L'attrito è la causa.

Quindi: giri al bot quello che ti è arrivato, e lui te lo legge.

```
/analizza Buongiorno, ho trovato il suo Protocollo su GitHub e l'ho letto
tutto stanotte. Posso farle due domande? Sono Marco, insegno a Bologna.
```
```
chi scrive      persona  (99%)
  da fuori?     100%
iniziativa      indipendente  (92%)
genere          lettore  (100%)
appiglio        88% — c'è qualcosa da controllare
chiede risposta 96%
urgenza         1.0/2 — Vorrebbe una risposta, ma può aspettare

Potrebbe valere per H2 come --tipo lettore.
Registrarlo è una tua decisione: nessun bot scrive quella metrica da solo.
```

Cinque domande in **una sola chiamata** — è il *speculative fan-out* che
TypeSafe consiglia: costano poco, e il codice decide dopo quali guardare.

**Non registra niente.** Il §3 dice che la metrica di H2 la alimenta solo
un essere umano. Qui l'atto umano resta doppio: **giri** una cosa, e
**decidi** se registrarla. Un bot che si registra i contatti da solo
misura la propria eco, con un'interfaccia più comoda.

### Tre difetti trovati eseguendo, non leggendo

Provato su quattro messaggi veri prima di collegarlo, e ne è uscito
storto tre volte:

1. **`verificabile` dava sempre 10-17%.** Chiedevo se un estraneo potesse
   controllare *un testo incollato* — ovviamente no, mai. La domanda
   giusta era un'altra: **c'è dentro un appiglio** — un nome, una data,
   un numero di protocollo, un link? Adesso dà 88% al lettore vero e 21%
   alla newsletter.
2. **Stampavo «persona (24%)» come se fosse una lettura.** Una risposta
   al 24% è un lancio di moneta, e mostrarla come dato è un UNKNOWN
   travestito. Sotto il 50% adesso esce **«non lo so»**, che è la
   risposta onesta — e che è ciò per cui la `confidence` esiste.
3. **La PEC di un ufficio veniva scartata.** Il mio criterio «automatico»
   diceva «newsletter, notifica, messaggio in serie», e una PEC è
   formale e quasi a modulo: ci finiva dentro al 44%. Ma per il §7 la
   domanda non è *l'ha scritto un umano o una macchina* — è **qualcuno
   ha deciso di mandarlo proprio a te**. Riscritta la domanda, la PEC
   esce a 100% «da fuori» e viene proposta come `--tipo istituzione`,
   che è il caso che per H2 vale di più.

Il difetto stava nella domanda, non nella soglia e non nel modello. È la
terza volta che questo progetto impara la stessa cosa — H12, la soglia,
e adesso il mittente: **l'etichetta che vince è la domanda sbagliata, la
distribuzione è quella giusta.**

## La seconda porta, chiusa

`autonomous_core_v3.registra_contatto()` scriveva in
`output/contatti.jsonl` **senza nessun controllo sul tipo** — nemmeno
quello che il comando CLI aveva da sempre. Due porte sulla stessa stanza,
una sola con la serratura, e la più comoda era quella aperta.

Adesso anche quella passa dalla valvola. Per scavalcarla dal bot:
`/contatto !lettore | ... | ...` — il punto esclamativo è il `--comunque`
della riga di comando, e lascia la stessa traccia.

---

## Se stai installando TypeSafe adesso (§6)

Su questo progetto lavorano più nodi che non si parlano. Il 20/09 ne stava
entrando un altro mentre questo file veniva scritto. Per non rifare la
malattia delle sei copie di `R3_WORK_QUEUE`:

**`valvola/` è canonica per TypeSafe su questo repository.** Non aggiungere
una seconda integrazione: allinea la tua a questa, o dichiara perché non
si può e quale delle due vince (§6 regola 2).

L'interfaccia è piccola apposta, e non serve leggere il resto per usarla:

```python
from valvola import controlla, stato_sorella

stato_sorella()      # {'attiva': bool, 'manca': str|None, ...} — non chiama la rete
controlla(nota, verifica, tipo_dichiarato)  # -> Verdetto, non alza mai eccezioni
```

Tre vincoli che non vanno rimossi, e il motivo:

1. **Nessun percorso fa salire una classe.** `falsificatori/h12_valvola_non_promuove.py`
   prova 63 combinazioni e cade se ne trova una. Se aggiungi un ramo,
   rieseguilo.
2. **Jev non riceve il tipo dichiarato.** Altrimenti risponde l'etichetta:
   l'eco con una probabilità davanti.
3. **I test non chiamano la rete.** La fixture `mai_la_rete` in
   `tests/test_valvola.py` lo impedisce: un test che passa grazie a una
   chiamata vera ha smesso di provare il codice.

E la regola di §6 che vale comunque: dichiara cosa hai toccato con
`python registro_nodi.py --nodo <chi-sei> --azione "..." --file ...` —
è append-only, due nodi non possono sovrascriversi.
