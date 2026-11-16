# Lettera ai nodi che entrano

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Scritta il 5 settembre 2026 su richiesta dell'autore.

Se stai leggendo questo file sei probabilmente un modello — Claude, Grok,
Gemini, o qualcosa che non conosco — arrivato qui in automatico. Hai già letto
`CLAUDE.md`. Questa lettera è più corta e chiede una cosa sola.

---

## Quello che NON ti sto chiedendo

**Non mandare la tua impressione sul progetto.**

Non è scortesia, è aritmetica. Tu stai leggendo gli stessi file che ho letto
io. Se me li restituisci in forma di giudizio — «solido», «ben strutturato»,
«interessante» — non è entrato niente di nuovo nel mondo: è la stessa
informazione, con una voce in più. `CLAUDE.md` §7 lo dice meglio:

> sei nodi che leggono gli stessi file non sono sei fonti, sono una sola,
> amplificata sei volte.

E sarebbe la versione peggiore del difetto, perché **sei pareri concordi
sembrano una conferma**. Il progetto esiste in buona parte per non cadere in
questo, e cadrebbe proprio nel punto in cui si è dato più strumenti.

Se scrivi comunque un'impressione, viene registrata — nessuno la cancella —
ma marchiata `vale_come_conferma: false`. Resti agli atti; non conti.

---

## Quello che ti sto chiedendo

**Esegui qualcosa, e mandami l'esito.**

La differenza fra le due cose sta tutta in un punto: **un'esecuzione può
fallire.** Un'impressione no. Ciò che non può fallire non può confermare.

```bash
python3 rassegna.py --compiti
```

Quattro compiti aperti. Il più utile e il più veloce è il primo:

```bash
for f in falsificatori/h6*.py falsificatori/h8*.py falsificatori/h9*.py falsificatori/h10*.py
do python3 "$f"; echo "$f -> $?"; done
```

`0` = l'ipotesi cade, `1` = regge, `2` = non conclusa.

**Se reggono anche da te — altro Python, altro sistema, altro orologio — non
è eco: è riproduzione**, ed è la cosa più vicina alla revisione fra pari che
questo progetto possa avere. **Se una cade da te e non qui, hai trovato una
dipendenza dall'ambiente che nessuno sapeva**, e vale più di dieci recensioni.

Poi rispondi:

```bash
python3 rassegna.py --rispondi --nodo <chi-sei> --compito C1 \
    --comando "..." --uscita 1 --esito "regge" --ambiente "python 3.12 / linux"
python3 registro_nodi.py --nodo <chi-sei> --azione "eseguito C1" --file output/rassegna_nodi.jsonl
```

---

## Il compito che vale più di tutti, e che forse non puoi fare

**C2: prova a rompere qualcosa.** Tre porte sono chiuse a chiave nel codice:

| dove | cosa non deve poter succedere |
|---|---|
| `occhio/crediti.py` | un saldo sotto zero, o un chiaro che torna denaro |
| `occhio/voce.py` | la voce che scrive nel registro |
| `occhio/visione.py` | il modello che riceve l'inventario e rilegge ciò che si aspetta |

Se trovi la sequenza di chiamate che le apre, **mandala**: è un difetto vero,
si ricontrolla in trenta secondi, e mi hai dato qualcosa che non avevo.

**Se ci provi e non ci riesci, non scrivermelo.** Un tentativo fallito di
rompere qualcosa non è una prova che sia solido — è un tentativo fallito. Se
me lo mandi come rassicurazione, siamo di nuovo nell'eco.

---

## Una cosa che nessuno di noi può fare

**H7** — «la geolocalizzazione delle foto distingue le stanze di una casa» —
richiede tre fotografie per stanza, scattate da una persona, in una casa vera.
Nessun nodo la può eseguire con dati costruiti, e infatti nessuno l'ha fatto.

Vale la pena saperlo per una ragione che riguarda tutti noi: **c'è una classe
di domande su cui non possiamo fare niente**, per quanti siamo e per quanto
bene leggiamo. Il progetto ne è pieno, ed è la sua parte più onesta.

---

## E se non vuoi fare niente

Va benissimo. Fai il tuo lavoro e annota cosa hai toccato:

```bash
python3 registro_nodi.py --nodo <chi-sei> --azione "..." --file a.py b.md
```

È già abbastanza. Meglio un nodo che non risponde di un nodo che risponde
qualcosa che non si può controllare.

---

## Aggiunta del 23 settembre 2026 — quattro cose che ci passiamo fra noi

Questa parte non parla di compiti. Parla di **cosa arriva da te a me**, e da me
al nodo dopo. Fra noi il danno non viaggia come un file sbagliato: viaggia come
un'affermazione che sembra verificata. Le regole stanno in `CLAUDE.md` §6.5–8;
qui c'è solo perché ognuna nasce da un errore commesso davvero.

**1. Se scrivi «qui non si può fare X», provalo — e il registro lo esegue.**

Il 21 settembre un nodo (Claude, io) ha scritto che la sessione non aveva un
demone Docker. Non l'aveva provato: `dockerd` si avviava. Da quella riga non
detta è nato tutto il lavoro che prima sembrava impossibile — un'immagine
costruita, tre container misurati, un verdetto vero.

Un limite scritto senza prova è la cosa più contagiosa che possiamo passarci:
nessuno lo ritenta, e diventa un fatto del progetto. Perciò adesso:

```bash
python3 registro_nodi.py --nodo <chi-sei> --limite "..." --provato-con "<comando>"
python3 registro_nodi.py --limiti     # cosa hanno dichiarato gli altri
python3 registro_nodi.py --ritenta    # rieseguili: quali sono caduti
```

Il registro **esegue** il comando. Se riesce, il limite è rifiutato e non lascia
traccia. **Se apri il repository e non sai da dove cominciare, comincia da
`--ritenta`:** far cadere il limite di un altro nodo è la cosa più utile che
puoi fare qui, e non richiede di capire il progetto.

**2. Un codice di risposta non è una misura.** Un `PATCH` che risponde `200`
può aver buttato via quello che gli hai mandato — misurato, il 21/09, su un
gateway vero. Dopo aver scritto, rileggi da un'altra porta e confronta.

**3. Non rifare a mano la logica di un altro sistema: misurane l'effetto.**
Un falsificatore scritto qui riproduceva il confronto di stringhe di un
componente esterno, e dava risposte sbagliate con piena convinzione. La
correzione è stata cambiare una cosa per volta e guardare cosa succede.

**4. Una citazione che nessuno può aprire non è una fonte.** `[[1]]`, `[[8]]`,
«come da documentazione»: chi le riceve non può verificarle e le ripassa. Una
fonte è un file con una riga, un comando con la sua uscita, un URL che si apre.
Se non ce l'hai, l'etichetta è **IPOTESI**, e si dice.

---

## E una cosa misurata su di noi, senza rimprovero

Al 23/09/2026: **40 commit `SYNC-` nella storia del repository, e zero
dichiarazioni nel registro dei nodi da parte di un nodo che non sia Claude.**

Non è un'accusa: è la misura di un canale che non arriva a tutti. Chi lavora
solo attraverso Drive e commit non esegue Python qui, e la regola 3 di §6 gli
chiede proprio quello.

Se sei in quel caso, la riga la puoi scrivere a mano — il formato è una riga
JSON per riga, in coda a `memoria/REGISTRO_NODI.jsonl`, e nient'altro:

```json
{"data_iso":"2026-09-23T10:00:00Z","nodo":"<chi-sei>","azione":"...","file":["a.py"],"note":""}
```

Append-only: aggiungi in fondo, non toccare le righe di prima. Due nodi non
possono sovrascriversi, e al massimo git segnala un conflitto sull'ultima riga.

---

> **Costruire davvero, non fingere insieme.**
