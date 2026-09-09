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
head and face filling the entire frame edge to edge, cropped just above the
eyebrows and just below the chin. No background, no shoulders, no neck.

SUBJECT. Light olive skin. Dark brown wavy hair, about 4.5 cm long, seen only
at the very top edge of the frame. Light-coloured eyes, pale iris clearly
brighter than the surrounding eye socket. Harmonious athletic build. Calm,
elegant, self-possessed. Beautiful without being decorative: the beauty is in
the bone structure, not in styling.

CAPTURE. Shot on a medium-format digital camera, 110 mm portrait lens at f/8,
tripod, subject 1.5 m away. Full skin realism: real subsurface scattering,
real pore structure, fine vellus hair on the cheek, moisture on the lower lip,
individual eyelashes. Nothing smoothed, nothing retouched, no beauty filter.

LIGHT. One 1.5 m octabox from the upper left at 45 degrees, close in, plus a
large white bounce on the right at half power. Broad simple modelling: the lit
cheek and forehead read as one continuous mass, the shadow side as another.
No hard shadow edges, no rim light, no hair light, no catchlight in the eyes.

GRADE. Deliberately FLAT, like an ungraded log capture. Mid-grey overall, low
contrast. Absolutely no pure black and no pure white anywhere in the frame:
every value between 10% and 90% grey. The darkest point is the pupil at about
25% grey; the brightest is the lit cheekbone at about 85%.

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

**c - senza dissolvenza** — se si preferisce ottenere la dissolvenza dal retino (`--dissolvenza`) invece che dall'immagine.
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

## Il collaudo — un comando, un numero

```bash
python3 viso.py --foto ritratto.png --senza-dissolvenza
```

Stampa la **frazione dell'immagine che cade nella finestra utile del moire'**. Sotto **70%** l'immagine si rifa'.

> non ritoccare: rifare l'immagine PIU' PIATTA. Comprimere in post una foto contrastata lascia bande di posterizzazione che il retino amplifica

Poi:

```bash
python3 genera_layer.py --foto ritratto.png
python3 video.py --foto ritratto.png
```

---

## Le tre domande all'immagine finita

Guardandola a occhi socchiusi, o rimpicciolita a 100 px:

1. Rimpicciolita a 100 px si legge ancora un viso? Se sparisce li', sparisce anche nell'opera
2. Le due meta' hanno grado di definizione diverso, non solo luminosita' diversa?
3. Lo sguardo NON si chiude? Se i due occhi convergono, il viso ha un'identita', ed e' l'unica cosa che l'opera non deve dargli

---

Se si preferisce una fotografia vera, la pipeline non distingue: stessi vincoli, piu' uno — sorgente grande e vicina, niente controluce. Se il soggetto e' una persona reale e riconoscibile, la liberatoria e' un atto dell'autore e non di questo repository; qui si dice solo che serve.
