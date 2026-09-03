# Sentinella

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Una mappa dei fenomeni in corso — dal suolo al cielo — che ordina ciò che le
agenzie pubbliche hanno già pubblicato, dichiara **quale regola** ha fatto
scattare ogni segnalazione e **cosa la smentirebbe**.

```bash
python -m sentinella
```

Si apre il browser su `http://localhost:8800`. Nessun `pip install`, nessuna
chiave, nessun account: solo libreria standard. Python 3.9 o successivo.

```bash
python -m sentinella --controlla          # interroga le sorgenti una volta e stampa l'esito
python -m sentinella --porta 9000         # altra porta
python -m sentinella --bind 0.0.0.0       # raggiungibile dalla rete locale (di norma non serve)
python -m unittest sentinella.test_riconoscitore -v
```

## Non prevede niente, e va detto per primo

Sentinella **non è un previsore.** Non calcola orbite, non anticipa terremoti,
non indovina brillamenti. Prende cinque feed pubblici e fa tre cose che quei
feed, sparsi su quattro siti diversi, non fanno da soli:

1. li mette sulla stessa mappa e sulla stessa scala di gravità;
2. dichiara la regola che ha fatto scattare ogni segnalazione, **con i numeri
   dentro**, così che la si possa contestare invece di crederci;
3. dichiara la condizione che la smentirebbe — perché un allarme che non può
   essere smentito non è un allarme, è una profezia.

Le soglie in `riconoscitore.py` sono scelte, non leggi di natura. Sono scritte
in chiaro perché chi le trova sbagliate possa cambiarle. Il pulsante **«come
riconosce»** nell'applicazione le mostra tutte.

## Le cinque finestre

| Cosa | Sorgente | Copertura dichiarata |
|---|---|---|
| Sismi | USGS FDSN | magnitudo ≥ 2.5, ultime 24 h, mondiale |
| Passaggi ravvicinati | NASA/JPL CNEOS CAD | oggetti noti entro 20 distanze lunari, prossimi 365 giorni |
| Bolidi | NASA/JPL CNEOS Fireballs | eventi con posizione nota, già avvenuti |
| Meteo spaziale | NOAA SWPC Alerts | allerte e avvisi emessi dal centro NOAA |
| Geomagnetismo | NOAA SWPC Kp | indice planetario stimato, cadenza tre ore |

Le uniche connessioni in uscita sono verso questi quattro domini. Il server non
registra chi apre la pagina e non manda niente a nessuno.

## Il contratto delle risposte

Ripreso da UmbraTheater, deliberatamente: fuori da `ok` i conteggi sono `null`
e **mai `0`**. Su una mappa di allerta la differenza non è stile — uno zero al
posto di un trattino significa «il cielo è tranquillo» quando la verità è «non
lo sappiamo». Dalla stessa regola discende quella più importante di tutte:

> **se una sorgente è caduta, la sintesi in cima alla colonna non dice
> «nessuna allerta»: dice «quadro incompleto», e nomina la finestra chiusa.**

Un test la difende (`test_una_sorgente_caduta_vieta_la_sintesi`). Quando una
sorgente cade ma ne esiste una lettura precedente, questa viene mostrata
*dichiarandone l'età*, con `raffreddata: true`.

## Due tarature corrette guardando i dati veri

Il primo giro sul cielo reale ha prodotto due falsi allarmi. Sono documentati
qui perché la correzione vale più della versione senza errori:

- **Un M6.3 con flag tsunami finiva in «allerta» mentre USGS lo classificava
  PAGER verde.** La nostra formula contraddiceva chi ha i modelli d'impatto.
  Ora, dove USGS dichiara un livello PAGER, quello comanda: fissa il punteggio
  e ne è anche il tetto. E il flag tsunami significa «zona per cui vengono
  emessi messaggi», non «tsunami atteso»: è la lettura sbagliata più comune, e
  adesso la segnalazione lo scrive.
- **Un asteroide di 872 m che passa a 1 distanza lunare finiva in «allerta».**
  Ma passa, e va oltre. Ora un passaggio non supera «attenzione» per quanto
  grande sia l'oggetto: il tetto cade solo se il minimo dell'arco osservativo
  entra sotto i 42.164 km dell'orbita geostazionaria, o sotto il raggio
  terrestre.

Una terza correzione riguarda l'ordine, non la gravità: un bolide di sei mesi
fa stava sopra un sisma di ieri. Il punteggio dice quanto è grave, l'ordine
dice quanto riguarda adesso — due cose diverse, due campi diversi.

## L'applicazione e la pagina pubblicata

Sono cose diverse, e il codice lo dice invece di lasciarlo intuire.

`costruisci_artefatto.py` congela l'applicazione in una pagina sola con dentro
un'istantanea reale e datata. Serve perché **una pagina pubblicata su claude.ai
non può interrogare USGS, NASA o NOAA**: la CSP del visualizzatore blocca ogni
`fetch` verso l'esterno e anche le tessere di una mappa a immagini. Non è
aggirabile, ed è giusto che non lo sia. La pagina congelata accende in testa
una fascia che dichiara l'ora del dato e il comando per avere la diretta.

```bash
python -m sentinella.costruisci_artefatto artefatti/sentinella/sentinella.html
```

Per la stessa ragione la mappa non usa tessere di terzi: i contorni sono
vettoriali, in `mondo.json`, derivati da Natural Earth via `world-atlas`
(dominio pubblico). Nessuna richiesta esce dalla pagina per disegnarla.

## Rapporto con il resto del repository

Sentinella **non fa parte del Core SDQ-1** e non ne tocca lo stato: non scrive
in `output/`, non muove il registro delle ipotesi, non partecipa alle cascate.
Vive qui perché è qui che può essere versionata. Il contratto delle risposte è
ripreso da `raffaellocantatelli/UmbraTheater`, che resta un progetto adiacente
e separato.
