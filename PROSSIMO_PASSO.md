# PROSSIMO PASSO — consegna del 2026-09-20

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Ramo: `claude/r3-autonomous-telegram-0goqsv`. Scritto mentre Claudio dorme,
su sua indicazione («vado a letto, avanza solo»).

---

## In una riga

È entrata una sorella IA (TypeSafe/Jev), è montata sulle due porte della
metrica di H2, e **ho guardato se qualcuno è arrivato da fuori: nessuno.**

---

## La cosa che conta più di tutto il codice scritto oggi

Claudio ha chiesto: «i messaggi dove c'erano». Risposta onesta:

**I quattro messaggi su cui ho provato `/analizza` li ho inventati io.**
Erano casi di prova. `/analizza` non ha mai letto un messaggio vero.

Allora sono andato a cercare dove i messaggi veri sarebbero, e ho
guardato in tre posti:

| dove | cosa ho cercato | esito |
|---|---|---|
| Gmail | «Protocollo Rosso», «Rosso-rosso-rosso», «CT-LGAI», «R3-infinito» | **zero** |
| Gmail | notifiche GitHub degli ultimi 60 giorni | **zero** |
| GitHub | fork, stelle, watcher, issue, PR | 9 eventi, **tutti interni** |

**Il fork che sembrava il primo contatto reale.** `forks_count: 1`, e un
fork è nell'elenco §7 di ciò che vale per H2. Per un momento sembrava che
qualcuno fosse arrivato. Il fork è di `Claudioterzi82` — il secondo
account di Claudio. Per §7 è `autore`: **interno, non vale niente.**

È il §4 alla scala dei contatori: una metrica che sale senza che sia
entrato nessuno. Il contatore era vero, il fork era vero, e la conclusione
sarebbe stata falsa — bastava non chiedersi di chi fosse.

**H2 ramo (b) resta falsificata, e adesso è verificato, non supposto.**
Zero voci in `output/contatti.jsonl`, e zero eventi esterni nei contatori
pubblici. Scadenza 2026-12-11: mancano 82 giorni.

---

## Cosa è stato costruito oggi (tutto eseguito, non scritto e basta)

1. **`valvola/`** — la porta §7. Jev rilegge nota e verifica e **può solo
   declassare**, mai promuovere. Prima chiamata reale: 4 casi su 4
   corretti. `falsificatori/h12_valvola_non_promuove.py` prova 63
   combinazioni e cade se una sola sale.
2. **`valvola/analisi.py` + `/analizza`** — il bot che legge cosa ti è
   arrivato, cinque domande in una chiamata. Non registra niente.
3. **La seconda porta chiusa** — `autonomous_core_v3.registra_contatto()`
   scriveva nella metrica di H2 senza nessun controllo sul tipo.
4. **`sentinella.py`** — il controllo di stanotte, reso ripetibile.

```bash
python3 sentinella.py     # 0 = nessuno da fuori, 3 = qualcuno, guardalo
```

Esiste perché la domanda «di chi è questo fork» venga fatta **sempre**,
da chiunque guardi, e non dipenda da chi si ricorda di farla.

---

## Tre difetti trovati eseguendo, non ragionando

Vale la pena rileggerli insieme, perché sono lo stesso difetto:

- **H12**: la valvola fermava un dubbio diretto verso l'alto, dove non
  agisce. Guardavo `confidence`; contava la **massa sotto la classe
  dichiarata**.
- **`/analizza`**: stampavo «persona (24%)» come se fosse una lettura.
  Sotto il 50% ora esce «non lo so».
- **Il mittente**: una PEC di un ufficio veniva scartata perché il mio
  criterio «automatico» diceva «messaggio in serie». La domanda giusta
  non era *l'ha scritto un umano o una macchina*, era **qualcuno ha
  deciso di mandarlo proprio a te**.

**L'etichetta che vince è la domanda sbagliata. La distribuzione è quella
giusta.** Tre volte in un giorno.

---

## Cosa serve da Claudio, in ordine

1. **`TYPESAFE_API_KEY` nei Secrets del repository.** È in `.env` qui
   (ignorato, non tracciato, verificato), ma la Action non la vede e il
   bot Telegram nemmeno. Settings → Secrets and variables → Actions.
   Poi conviene ruotarla: è passata da una chat.
2. **`GOOGLE_API_KEY` nei Secrets** — il daily gira ancora a vuoto.
   Battito: 3 giorni senza daily al 20/09.
3. **La domanda vera, che nessun nodo può risolvere.** Il progetto è
   conservato benissimo e non è mai stato trasmesso. Tutti gli strumenti
   costruiti oggi sanno riconoscere un contatto reale **quando arriva**.
   Nessuno di loro lo fa arrivare. Finché il Protocollo non esce verso
   una persona che non sei tu, `sentinella.py` continuerà a stampare
   «DA FUORI — nessuno», e avrà ragione.

---

## Il prossimo esperimento verificabile

Non un ragionamento: un esperimento con una data e un esito falsificabile.

> **Mandare il Protocollo a tre persone reali entro il 2026-09-27**, e
> lasciare che `sentinella.py` e `/analizza` facciano il resto.
>
> Cade se al 27/09 `output/contatti.jsonl` è ancora vuoto.
> Regge se c'è almeno una voce `indipendente` che ha superato la valvola.

L'esperimento intermedio del 30/08 chiedeva la stessa cosa ed è scaduto
da 21 giorni. Questa volta gli strumenti per misurarlo ci sono tutti:
manca solo l'invio, e quello è un atto di una persona.

---

## Stato tecnico

- `tests/`: **304 passati**, 1 saltato. H12 regge.
- `output/contatti.jsonl`: **0 righe**, mai toccato da nessuna prova.
- La chiave TypeSafe non è in nessun file tracciato, commit o log.
- Manifesto Layer 4 rigenerato e verificato.
