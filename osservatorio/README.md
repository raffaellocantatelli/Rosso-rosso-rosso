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

## Il fotogramma

```bash
python -m osservatorio --fotogramma --lat 45.4642 --lon 9.19
```

Uno scatto: legge tutte le fonti, prende due ancore temporali pubbliche, calcola
dove siamo davvero, e riduce tutto a una chiave `sha256`.

**Cosa ottieni, con esattezza: una prova di anteriorita' che non chiede di
fidarsi di nessuno.** La chiave contiene due valori che nessuno puo' calcolare
in anticipo:

- **NIST Randomness Beacon** — 512 bit firmati e concatenati, ogni 60 s;
- **drand / League of Entropy** — un round ogni 30 s, verificabile con la
  chiave pubblica del gruppo.

Una chiave che li contiene **non poteva esistere prima di quel secondo**. E
chiunque, anche fra dieci anni, puo' riprendere quel round e quel pulse e
verificare che coincidano — senza fidarsi di te, di me o di questo programma.
E' il tipo di fatto che il §7 chiede: controllabile da un terzo, non poggiato
su nessuna persona.

**Cosa la chiave non fa**, ed e' scritto anche nell'output di ogni scatto:

- non e' ricostruibile all'indietro — i feed effimeri non archiviano il
  passato, quindi un terzo verifica le *ancore*, non i conteggi. Dimostra
  «non prima di», non «esattamente questo mondo»;
- non e' una posizione: e' un indice nel tempo.

Se un'ancora e' vecchia lo scatto lo dice invece di tacerlo. Al primo collaudo
il beacon NIST risultava fermo da circa 30 ore, e il fotogramma lo ha marcato
`ATTENZIONE: non fresca` da solo.

Gli scatti si concatenano in `output/fotogrammi.jsonl`: ogni fotogramma cita
l'hash del precedente, come fa il beacon del NIST. Il file **non e' versionato**:
depositare uno scatto e' un atto verso l'esterno, e la decisione di pubblicarlo
resta dell'autore. Quando vuoi che un fotogramma valga come deposito pubblico,
lo committi tu, deliberatamente — e la data del commit diventa una seconda
marca temporale indipendente.

## Dove siamo — `posizione.py`

Solo matematica della libreria standard, nessuna effemeride esterna. Tre livelli,
tenuti distinti perche' hanno statuti diversi:

1. **Terra rispetto al Sole** — calcolato qui, ~0,01 gradi e 1e-4 UA.
2. **Sole nella Galassia** — *non* calcolato: costante misurata da altri
   (R0 = 8,122 +/- 0,031 kpc, GRAVITY 2018), riportata come tale.
3. **Moto rispetto al fondo cosmico** — 369,82 +/- 0,11 km/s verso
   (l, b) = (264,021; 48,253), Planck 2018. E' il punto piu' vicino a un
   sistema di riferimento assoluto che la fisica conosca, e il programma
   calcola dove sta quell'apice nel cielo sopra di te, adesso.

La trasformazione galattico -> equatoriale e' verificata su tre coordinate note
(polo nord galattico, centro galattico, apice CMB): scarto massimo 0,005 gradi.

## Traccia

Ogni lettura, riuscita o fallita, finisce in `output/osservatorio.jsonl`,
append-only come il registro dei nodi. Nessuna riga viene mai riscritta: chi
arriva dopo puo' ricostruire cosa mostrava lo schermo e quando, senza doversi
fidare del processo che lo mostrava.

---

Origine protetta: Claudio Terzi [CT-LGAI-001].
