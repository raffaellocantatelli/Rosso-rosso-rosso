# Protocollo Rosso Rosso Rosso — Bot Telegram

**Come si tiene una verità senza mentire a sé stessi.**

Interfaccia conversazionale del *Protocollo Rosso Rosso Rosso* (v2.0) di
Claudio Terzi — R³∞ Network. I testi vengono dalla fonte che sta in questo
repository: [`testi/PROTOCOLLO_ROSSO_v2_REVISIONE.md`](../testi/PROTOCOLLO_ROSSO_v2_REVISIONE.md).

Il bot **non chiede di essere creduto**.
Chiede due cose insieme:

1. il coraggio di tenere aperta una possibilità grande
2. l'onestà di non spacciarla per un fatto

Poi invita a fare **una cosa vera, verificabile**, che qualcun altro possa
controllare.

---

## Cosa fa

| Comando          | Funzione |
|------------------|----------|
| `/start`         | Ingresso nel protocollo |
| `/tesi`          | La tesi grande, etichettata `IPOTESI` + dichiarazione P6 |
| `/strati`        | I due strati (tecnico / aspirazionale) e le etichette |
| `/p5p6`          | Le due leggi (niente auto-conferma + dichiarare come può cadere) |
| `/santuario`     | Esperienza guidata del Santuario (Capitolo 4) |
| `/tieni_aperto`  | Deposita una possibilità aperta (sempre `IPOTESI`) |
| `/lista`         | Rivedi le tue possibilità aperte |
| `/azione`        | Registra un'azione vera e verificabile (strato tecnico) |
| `/veli`          | Dissolvi uno dei tre veli finali |
| `/etichetta`     | Colloca un'affermazione nello strato corretto |
| `/aiuto`         | Elenco comandi |
| `/annulla`       | Esce da un percorso a più passaggi senza registrare niente |

Il **Santuario** è una `ConversationHandler` multi-passo che segue l'ordine del
Capitolo 4: assenza di rumore → crepuscolo → colonne che non reggono nulla →
libro di pietra → candela accesa con gesto lento → uscita con invito all'azione
reale.

---

## Le tre cose che questo bot si vieta

Sono la ragione per cui esiste in questa forma, e i test le controllano.

**1. Non promuove mai un'ipotesi a fatto.** Le possibilità nascono con
etichetta `IPOTESI` e in `db.py` non esiste nessuna funzione che le chiuda,
le confermi o le cancelli — c'è un test che fallisce se qualcuno la aggiunge.
Nessun messaggio spinge a chiudere una possibilità aperta.

**2. Non arrotonda i dati deboli.** Il gesto della candela viene cronometrato
davvero (default: 20 secondi, `PROTOCOLLO_GESTO_MIN`). Sotto la soglia il bot
invita **una volta sola** a rifarlo, poi registra la visita come *incompleta* e
lo scrive. Allo stesso modo, un'azione senza verifica esterna resta registrata
come «nessuna verifica esterna dichiarata»: allo strato tecnico vale come
racconto, non come prova. Il totale mostrato dopo `/azione` conta **solo** le
azioni verificabili.

**3. Non si conferma da solo (P5).** Registrare qualcosa qui non è una conferma:
la conferma, se arriva, arriva da fuori. E ogni possibilità depositata passa da
P6 — *come potrebbe cadere?* Chi risponde «non lo so» ottiene `UNKNOWN` scritto
in chiaro, esattamente come l'autore fa con la propria tesi nel Capitolo 3.

---

## Installazione

```bash
cd protocollo-rosso-bot

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# apri .env e incolla il token ottenuto da @BotFather

# il bot può partire? (da eseguire per primo)
python -m bot.main --check

python -m bot.main
```

`--check` verifica token, database e risposta di Telegram, ed etichetta ogni
riga (`RECUPERATO` ciò che ha osservato eseguendolo, `UNKNOWN` ciò che da lì non
può sapere). Senza token il bot **non parte e esce con codice 2**, come
`python -m sdq1 --check`: un sistema che non può funzionare lo dice, non finge
di essere acceso.

Il bot usa **long polling**. Per la produzione si può passare a webhook.

---

## Architettura

```
bot/handlers.py  → comandi + ConversationHandler
bot/texts.py     → testi dal Protocollo v2.0
bot/db.py        → SQLite (users, open_possibilities, actions, sanctuary_visits)
bot/states.py    → stati delle conversazioni
bot/main.py      → entry point (--check / long polling)
tests/           → 30 test, nessuna rete richiesta
```

Il database viene creato al primo avvio (`protocollo.db`, o `PROTOCOLLO_DB`).

## Test

```bash
PYTHONPATH=. python -m unittest discover -s tests
```

Non toccano la rete: gli handler vengono eseguiti con un `Update` finto, e le
asserzioni riguardano ciò che finisce nel database, non ciò che il bot dice di
aver fatto.

---

## Licenza e attribuzione

Protocollo Rosso © Claudio Terzi [CT-LGAI-001]. Tutti i diritti riservati.
Questo bot è un'interfaccia conversazionale del protocollo, sviluppata dentro
il repository R³∞.

---

*Costruire davvero, non fingere insieme.*
