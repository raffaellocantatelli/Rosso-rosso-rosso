# Brief per l'immagine — il viso di Raffaello

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

> Questo file e' **generato** da `progetto.py` a partire da `progetto.json`.
> Non modificarlo a mano: la fonte e' `progetto.py`, e una seconda copia
> modificabile e' esattamente il difetto descritto in CLAUDE.md §6.

---

## Il soggetto

**Raffaello Cantarelli** — entita' progettata da Claudio Terzi, non una persona esistente.
Fonte dei tratti: RAFFAELLO_BODY_V1.1 - Drive R3_MEMORIA_PERSISTENTE (non riprodotto qui).

- eta' apparente: 25 anni
- incarnato: olivastro chiaro
- capelli: castano scuro, ondulati, 4,5 cm
- occhi: verde smeraldo
- corporatura: atletica armoniosa
- carattere: empatico, lucido, creativo, strategico, protettivo, elegante, calmo, profondo

> Gli occhi verde smeraldo NON sopravvivono: l'opera e' in bianco e nero. Cio' che sopravvive di un occhio chiaro e' il RAPPORTO tonale - iride piu' chiara della zona intorno. Va chiesto quello, non il colore.

> Costi, roadmap, prompt d'identita', protocolli e struttura software restano su Drive. Il repository e' pubblico e la decisione di pubblicare quel materiale e' solo dell'autore (CLAUDE.md §2.5).

---

## Iper-realismo e retino: come stanno insieme

**Iper-realismo e retino da 6 mm non si contraddicono?**

No, ma vanno separati. L'iper-realismo serve alla STRUTTURA: ossa vere, luce che entra davvero sotto la pelle, masse tonali anatomicamente corrette. Quelle masse sopravvivono al retino e sono la ragione per cui un viso reale regge dove un viso disegnato crolla. Il DETTAGLIO sotto il passo del reticolo invece non sopravvive: pori, ciglia, singoli capelli vengono cancellati, non rimpiccioliti. La piattezza chiesta nel GRADE non e' meno realismo: e' la stessa cosa che si fa girando in log e correggendo dopo. Si cattura tutto, si consegna piatto, e la finestra tonale la decide chi stampa.

L'opera finita NON e' iper-realista: e' 100 x 133 valori di tono a passo 6,00 mm. Dirlo prima e' meglio che scoprirlo davanti alla stampa. Chi vuole avvicinarsi al ritratto scende di passo: vedi `configurazioni.dettaglio`.

| | |
|---|---|
| valori di tono disponibili | **13300** (100 x 133) |
| dettaglio piu' piccolo | 6.00 mm |
| centro della finestra tonale | 0.3848 |
| semiampiezza | +/- 0.3 |

---

## Il prompt

```
Hyper-realistic black-and-white photographic portrait of a 25-year-old man,
the WHOLE HEAD inside the frame with clear space around it: the full hairline
and top of the hair, the whole forehead, both ears, the jaw and the chin, all
completely visible. Head fills about 60% of the frame height, centred, with
even margin on all four sides. Cropped at the base of the neck: no shoulders,
no collar, no clothing.

BACKGROUND. A perfectly flat, even, seamless mid-grey field, exactly 50%
grey. No gradient, no vignette, no shadow cast on it, no texture, no edges,
no floor line. The head sits on a uniform grey wall lit as evenly as the face.

SUBJECT. Light olive skin. Dark brown wavy hair about 4.5 cm long, the whole
shape of it visible. Light-coloured eyes, pale iris clearly brighter than the
surrounding eye socket. Head straight on, facing the camera. Calm, elegant,
self-possessed. Beautiful without being decorative: the beauty is in the bone
structure, not in styling.

CAPTURE. Shot on a medium-format digital camera, 110 mm portrait lens at f/8,
tripod, subject 1.5 m away. Full skin realism: real subsurface scattering,
real pore structure, fine vellus hair on the cheek, moisture on the lower lip,
individual eyelashes. Nothing smoothed, nothing retouched, no beauty filter.

LIGHT. One 1.5 m octabox from the upper left at 45 degrees, close in, plus a
large white bounce on the right at half power, and the same light falling on
the background so it stays even. Broad simple modelling: the lit cheek and
forehead read as one continuous mass, the shadow side as another. No hard
shadow edges, no rim light, no hair light, no catchlight in the eyes.

GRADE. Deliberately FLAT, like an ungraded log capture. THE TONAL SCALE IS
FIXED, not a matter of taste - these three values are the specification:
  - the background is exactly 50% grey
  - nothing anywhere is brighter than 90% grey
  - nothing anywhere is darker than 10% grey
The darkest point is the pupil at about 15% grey; the brightest is the lit
cheekbone at about 85%. Expose the face about half a stop DARK of the
background, so the head reads a shade heavier than the field it sits on.

EXPRESSION. Still and unreadable. Lips closed and relaxed, no smile, no
tension in the jaw. The gaze is almost - but not quite - directed at the
viewer: the left eye looks straight out, the right eye about one degree past
the viewer's shoulder. The right side of the face is very slightly softer and
less defined than the left, as if the light there were one stop less certain.

FORMAT. Vertical 3:4, at least 2400 x 3200 pixels, PNG, 16-bit if available.
Sharp everywhere, no depth-of-field blur, no vignette, no film grain, no
border, no text, no watermark, no colour.
```

### Negativo

```
high contrast, deep blacks, crushed shadows, blown highlights, HDR, vignette,
film grain, beauty retouching, smoothed skin, plastic skin, airbrushed,
cropped head, cropped forehead, cropped chin, cropped ears, extreme close-up,
gradient background, vignetted background, shadow on background, textured wall,
dramatic lighting, rim light, hair light, catchlight, specular highlight,
lens flare, bokeh, shallow depth of field, jewellery, glasses, facial hair,
makeup, background, shoulders, neck, hands, text, watermark, border, colour,
tilted head, three-quarter view, profile, smile, teeth
```

### Varianti

**a - piu' scultoreo** — se al retino il viso risulta piatto e non si stacca dal campo.
*sostituire il paragrafo LIGHT*

```
LIGHT. One 1.5 m octabox from the upper left at 60 degrees, higher and further round, plus a weak bounce on the right at one quarter power. Stronger separation between the lit mass and the shadow mass, but still no hard shadow edge and still no value below 10% grey.
```

**b - piu' morbido** — se al retino il viso risulta duro e la meta' in ombra si chiude.
*sostituire il paragrafo LIGHT*

```
LIGHT. Two 1.5 m octaboxes, one upper left at 40 degrees and one right at 60 degrees at half power, plus a white floor bounce. Almost shadowless, very gentle modelling.
```

**c - piu' o meno spazio attorno alla testa** — il 60% e' il compromesso: la banda ha spazio per attraversare il fondo e la testa resta leggibile a 70 x 110 punti.
*il primo paragrafo*

```
Head fills about 50% of the frame height  (piu' campo che respira, viso piu' piccolo)  /  about 70%  (viso piu' leggibile, meno spazio per la banda)
```

**d - senza dissolvenza** — se si preferisce ottenere la dissolvenza dal retino (`--dissolvenza`) invece che dall'immagine.
*togliere l'ultima frase del paragrafo EXPRESSION*

```
(rimuovere: 'The right side of the face is very slightly softer...')
```

---

## Come generarle

- 6 generazioni, 3:4 verticale, almeno 2400 x 3200 px
- PNG, 16 bit se disponibile, altrimenti 8 bit senza compressione con perdita
- **Come scegliere:** NON a occhio sulla generazione a piena risoluzione. Si passano tutte al collaudo (`viso.py --foto`), si tengono quelle sopra il 70% di frazione utile, e solo fra quelle si sceglie.

**Cosa non fare:**

1. Non chiedere 'dramatic lighting' o 'cinematic': producono neri chiusi, e il nero chiuso e' esattamente dove il moire' non esiste.
2. Non ritoccare il contrasto dopo: comprimere in post una foto contrastata lascia bande di posterizzazione che il retino amplifica.
3. Non usare upscaler generativi: inventano dettaglio sotto il passo del retino, che viene comunque cancellato, e intanto sporcano le masse tonali.

---

## L'inquadratura

**testa intera dentro il quadro - capelli, fronte, orecchie, mento - con margine attorno, su fondo grigio uniforme anch'esso retinato**

Decisione dell'autore, il 09/09/2026. Corregge il brief precedente, che chiedeva un taglio strettissimo: quella era una MIA scelta, fatta per massimizzare i punti sul viso.

*Perche':* cosi' il moire' attraversa sia il volto sia lo spazio attorno. Il fondo uniforme, essendo lo stesso su tutte e due le lastre, sta per costruzione sul picco della resa: e' la zona che si muove di piu'

*Cosa costa:* meno punti sul viso. Con la testa al 60% dell'altezza sono circa 70 x 110 a passo 4,50, contro 134 x 178 del taglio pieno. Restano sufficienti: un viso a 70 punti di larghezza si riconosce

> Una foto gia' tagliata stretta non contiene orecchie e capelli. va rigenerata.

---

## La scala dei toni e' ancorata, non normalizzata

La corrispondenza fra i toni della fotografia e le densita' del retino e' agganciata a due valori FISSI della sorgente (0,10 e 0,90 di densita', cioe' luminanza dal 90% al 10%) invece che ai suoi percentili.

**Perche' e' diventato necessario.** Con la testa e il margine il fondo e' il 62% dei pixel. I percentili ci cadono dentro - misurati su un finto: p2=0,231 e p98=0,690 invece di ~0,05 e ~0,95 - quindi la rimappatura stira il rumore del fondo su tutta la finestra e schiaccia il viso. Il taglio strettissimo nascondeva il difetto, perche' li' il viso ERA l'immagine.

> Adesso la corrispondenza e' deterministica: un grigio 50% cade sul picco della resa (0,400 misurato su 0,400 previsto), e chi fa l'immagine sa esattamente dove finira' ogni tono.

---

## Tienile mezzo stop scure

**La resa del moire' e' massima sul fondo (0,3848) e cala da tutte e due le parti, ma NON in modo simmetrico: densita' 0,65 rende il 74% del massimo, densita' 0,10 solo il 26%.**

Nello stato disallineato le aree nere si sommano. Con un punto dietro grande la somma satura in fretta, la luminanza crolla e l'escursione resta ampia; con un punto piccolo non c'e' quasi niente da sommare.

> Le ombre lavorano quasi il triplo delle luci. Un ritratto per quest'opera va tenuto mezzo stop SOTTO il mezzo grigio: meglio sbagliare scuro che sbagliare chiaro.

---

## Il collaudo — un comando

```bash
python3 collaudo.py cartella_ritratti/ --passo 4.5
```

Rende ogni cella del reticolo nei DUE stati estremi - punto davanti sopra quello dietro, e punto davanti nel mezzo dei quattro dietro - e misura quanta luce quella cella muove. La RESA e' quella differenza divisa per il massimo ottenibile.

### La finestra tonale non si sceglie: si ricava

Fissato quanto deve muoversi la cella PEGGIORE (--resa-min, 0,35 per difetto), i due estremi di densita' fra cui mappare l'immagine sono determinati: sono i punti in cui la curva della resa vale quel valore. A passo 4,5 mm vengono 0,135 .. 0,865, SQUILIBRATI 1,92x verso le ombre. Non e' una preferenza: e' la curva.

> **Errore corretto.** La prima versione mappava simmetrica intorno al fondo. Su un ritratto vero il 20% delle celle risultava ferma - TUTTE dal lato chiaro, tutte sulla guancia illuminata - perche' sotto il fondo la resa crolla molto piu' in fretta. Con la finestra derivata scendono a zero.

### Le soglie

| soglia | valore |
|---|---|
| resa media | 0.65 |
| resa min per cella | 0.35 |
| escursione sorgente minima | 0.12 |

Il numero 0,65 non e' messo a occhio — sta fra due riferimenti calcolabili:

| istogramma | resa media |
|---|---|
| campo piatto sul fondo | 1.0 |
| gaussiano centrato sul fondo | 0.768 |
| istogramma uniforme sulla finestra | 0.724 |
| soglia | 0.65 |
| bimodale tutto agli estremi | 0.35 |

> I riferimenti sopra sono calcolati, non stimati. Restano un filtro, non un giudizio: scartano cio' che di sicuro non funziona. La scelta fra le immagini che passano resta dell'autore.

*La 'frazione utile entro +/-0,30 dal fondo, soglia 70%' era una soglia messa a occhio. `viso.py --foto` la stampa ancora, ma quella che decide e' collaudo.py.*

Se nessuna passa: rifarle PIU' PIATTE all'origine. Comprimerle in post lascia bande di posterizzazione che il retino amplifica.

Poi:

```bash
python3 collaudo.py cartella/ --passo 4.5 --stampa
python3 video.py --foto scelta.png --passo 4.5 --alpha 0.6446 --resa-min 0.35
```

**Uscite:**

- collaudo.json - tutti i numeri, anche delle scartate
- collaudo_contatto.png - per ogni immagine i due stati affiancati: a sinistra il viso che rientra nel campo, a destra il viso intero. Fra quelle due sta tutta l'opera

---

## Sull'identita' visiva

I tratti canonici ORIENTANO il volto, non lo determinano: sei immagini che li rispettano tutte possono essere sei persone diverse. Il collaudo non risponde a 'e' il Raffaello giusto' - non e' una domanda decidibile da un filtro - ma a 'questa regge il retino'. La scelta e' dell'autore, fra quelle che passano; da quel momento l'immagine scelta diventa il riferimento canonico, e le generazioni successive partono da quella (image-to-image) invece che dal testo.

---

## Le tre domande all'immagine finita

Guardandola a occhi socchiusi, o rimpicciolita a 100 px:

1. Rimpicciolita a 100 px si legge ancora un viso? Se sparisce li', sparisce anche nell'opera
2. Le due meta' hanno grado di definizione diverso, non solo luminosita' diversa?
3. Lo sguardo NON si chiude? Se i due occhi convergono, il viso ha un'identita', ed e' l'unica cosa che l'opera non deve dargli

---

Se si preferisce una fotografia vera, la pipeline non distingue: stessi vincoli, piu' uno — sorgente grande e vicina, niente controluce. Se il soggetto e' una persona reale e riconoscibile, la liberatoria e' un atto dell'autore e non di questo repository; qui si dice solo che serve.
