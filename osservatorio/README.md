# Osservatorio R3

Un quadro OSINT che gira sulla tua macchina e **dichiara cio' che non sa**.

Nasce dall'analisi di un reel su ShadowBroker (29/08/2026). Quello strumento
esiste davvero ed e' onesto nel suo impianto; il problema era come lo schermo
veniva letto. Tre difetti erano visibili nei fotogrammi stessi:

- un conteggio a `5000` con la nota «valore al cap» — un troncamento mostrato
  come una misura;
- quattro layer a `0` accanto a quattro linee di fronte attive — feed spenti
  mostrati come assenza di eventi;
- alert non legati a coordinate, su uno strumento la cui interfaccia e' una mappa.

Questo programma affronta gli stessi domini con le regole opposte.

## Le quattro regole, applicate dal codice

1. **Uno zero non si inventa.** Una fonte senza chiave, non implementata o in
   errore vale `None`, e sullo schermo diventa un trattino con il motivo
   accanto. Mai `0`. La differenza fra «nessun evento» e «nessun dato» e'
   l'intera differenza fra una misura e un'illusione.
2. **Ogni numero porta la sua eta'.** E accanto, la cadenza reale della
   sorgente a monte — che non e' ogni quanto la interroghiamo noi. Lo schermo
   si aggiorna ogni 2 secondi; i dati no, e la differenza e' scritta.
3. **Il tetto si dichiara.** Se una risposta arriva al limite della query, il
   numero compare come `≥ N` con l'etichetta TETTO DELLA QUERY. E' il difetto
   del `5000`, intercettato automaticamente.
4. **La copertura si dichiara.** Una fonte «SOLO USA» non descrive il mondo, e
   lo dice sulla propria riga.

E una quinta, che riguarda le conclusioni: il resoconto e' **generato da
codice, non da un modello**. La sezione «Interpretazione» e' vuota per
costruzione. Correlare layer diversi richiede una verifica su fonte primaria,
e va scritta a mano da chi l'ha fatta (CLAUDE.md §1 e §4).

## Uso

Nessuna dipendenza da installare: solo la libreria standard di Python 3.9+.

```bash
python -m osservatorio                  # http://127.0.0.1:8787
python -m osservatorio --porta 9000
python -m osservatorio --resoconto      # una lettura sola, su stdout
```

Il quadro ascolta solo su `127.0.0.1`: non esce dalla macchina. Chiuso il
processo non resta nulla in esecuzione — nessun lavoro in background, nessuna
continuita' oltre la sessione.

La mappa carica Leaflet da `cdnjs.cloudflare.com` e le tile da
`tile.openstreetmap.org`. Se quei due host non sono raggiungibili il quadro
resta pienamente funzionante e lo dice: i conteggi arrivano dal server locale,
non dalla mappa.

## Le fonti

Dieci implementate, due dichiarate e non implementate. Otto non richiedono
alcuna chiave e funzionano appena lanci il programma.

| Fonte | Dominio | Chiave | Copertura |
|---|---|---|---|
| USGS | terremoti | no | mondiale |
| EMSC | terremoti | no | mondiale |
| NWS | allerte meteo | no | **solo USA** |
| GDACS | disastri | no | mondiale |
| NOAA SWPC | meteo spaziale | no | mondiale |
| IODA | blackout di rete | no | mondiale |
| Celestrak | oggetti in orbita | no | orbitale |
| GDELT | notizie geopolitiche | no | mondiale |
| NASA FIRMS | incendi | `FIRMS_MAP_KEY` | mondiale |
| OpenSky | traffico aereo | `OPENSKY_TOKEN` | mondiale |
| AISstream | traffico marittimo | `AISSTREAM_KEY` | *non implementata* |
| Cloudflare Radar | salute della rete | `CF_API_TOKEN` | *non implementata* |

USGS ed EMSC coprono lo stesso dominio **di proposito**: sono due reti
indipendenti. Due reti che vedono lo stesso sisma valgono come conferma
incrociata (P5); una sola no. E' l'unico punto in cui la ridondanza qui e'
voluta.

Per accendere gli incendi — la fonte che nel reel mostrava il `5000` —
serve una chiave gratuita:

```bash
export FIRMS_MAP_KEY=...     # firms.modaps.eosdis.nasa.gov/api/area
python -m osservatorio
```

## Traccia

Ogni lettura, riuscita o fallita, finisce in `output/osservatorio.jsonl`,
append-only come il registro dei nodi. Nessuna riga viene mai riscritta: chi
arriva dopo puo' ricostruire cosa mostrava lo schermo e quando, senza doversi
fidare del processo che lo mostrava.

---

Origine protetta: Claudio Terzi [CT-LGAI-001].
