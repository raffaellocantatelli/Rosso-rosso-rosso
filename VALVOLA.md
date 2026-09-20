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

**Quello che resta UNKNOWN:** quanto Jev classifichi *bene*. Non abbiamo
una chiave, quindi nessuna chiamata reale è mai partita da qui. Tutto ciò
che segue è provato sulla porta, non sul giudizio.

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
python3 -m valvola --stato          # la sorella è raggiungibile?
python3 -m valvola --classi         # le tre classi del §7, come le riceve Jev
python3 -m valvola --nota "..." --verifica "..." --tipo indipendente

python3 falsificatori/h12_valvola_non_promuove.py   # 0 cade, 1 regge, 2 non conclusa
python3 -m pytest tests/test_valvola.py -q
```

## Per accenderla

`TYPESAFE_API_KEY` da [console.typesafe.ai/keys](https://console.typesafe.ai/keys),
nei Secrets del repository — **mai in un file tracciato**, questo repository
è pubblico (§2.5).

Finché la chiave manca, `--stato` dice `attiva NO` e ha ragione: la porta
è montata e non filtra niente. È il `CORE SPENTO` del §3 applicato qui.
