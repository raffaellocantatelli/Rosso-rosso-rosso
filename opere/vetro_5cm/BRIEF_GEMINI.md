# Brief per Gemini — l'immagine del viso

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Committente: Claudio Terzi. Destinazione: opera *Il viso cerca l'identità*,
vetro stampato + 50 mm d'aria + plexiglas retinato, 600 × 800 mm.

Questo file esiste perché l'immagine è l'unico pezzo che non posso costruire
io in modo accettabile. Il viso procedurale in `viso.py` è un **segnaposto
verificabile**: serve a provare l'ottica, non a reggere un'opera. Va sostituito.

---

## 0. Perché questa immagine non è un ritratto qualsiasi

L'immagine non viene stampata: viene **retinata a punti da 6 mm**. Su
600 × 800 mm ci sono 100 × 133 punti, e ogni punto porta **un solo valore di
tono**. Tutto ciò che sta sotto i 6 mm — la trama della pelle, le ciglia, i
capelli, un riflesso negli occhi — non viene rimpicciolito: **viene
cancellato**, e quello che resta al suo posto è rumore.

E c'è un secondo vincolo, che è quello che di solito nessuno sa:
**il moiré esiste solo nei mezzitoni.** Il punto davanti copre quello dietro;
dove dietro c'è bianco non c'è niente da coprire, dove c'è nero pieno il punto
davanti sparisce dentro. Un'immagine con neri chiusi e bianchi bruciati
spegne l'opera proprio dove è più drammatica.

Quindi le due regole dure, prima di ogni considerazione estetica:

1. **Il viso deve leggersi da masse tonali grandi**, non da dettagli.
2. **Niente nero pieno, niente bianco puro.** Tutto l'istogramma fra il 10% e
   il 90%. Una foto "bella" con neri profondi qui è una foto inutilizzabile.

---

## 1. Il prompt da incollare

In inglese: i modelli di immagine rispondono meglio, e i termini fotografici
sono meno ambigui. Il senso è quello dei paragrafi italiani sotto.

```
A monochrome black-and-white photographic portrait of a single human face,
filling the entire frame edge to edge — cropped just above the eyebrows and
just below the chin, no background visible, no shoulders, no neck.

Lighting: one large soft source from the upper left at about 45 degrees,
plus a weak fill from the right. Broad, simple modelling: the lit cheek and
forehead as one continuous mass, the shadow side as another. No specular
highlights, no catchlights in the eyes, no rim light.

Tonality: mid-grey overall, low contrast, flat. No pure black anywhere, no
pure white anywhere. Every value between 10% and 90% grey. Soft, even skin
with no visible pores or texture. No fine detail of any kind.

Expression: still, unreadable, neither warm nor hostile. Lips closed and
relaxed, no smile. The two eyes do not focus on the same point — the left
eye looks straight at the viewer, the right eye looks very slightly past it.
The right side of the face is a little softer and less defined than the left.

Age indeterminate, gender ambiguous, no makeup, no jewellery, no glasses,
no facial hair, hair not visible.

Format: vertical 3:4, at least 1800 x 2400 pixels. Sharp focus, no depth of
field blur, no vignetting, no film grain, no border, no text, no watermark.
```

**Negativo** (se il campo esiste, altrimenti è già nel prompt):

```
high contrast, deep blacks, blown highlights, vignette, film grain, skin
texture, pores, wrinkles, eyelashes detail, catchlight, specular highlight,
jewellery, glasses, hair strands, background, shoulders, neck, text,
watermark, border, colour, dramatic lighting, rim light, bokeh
```

---

## 2. Cosa cambia rispetto al segnaposto, e perché

| | segnaposto attuale | immagine richiesta |
|---|---|---|
| inquadratura | testa che galleggia con margini | **viso a pieno campo** |
| punti sul viso | ~55 × 103 | **100 × 133** |
| fondo | campo uniforme al 38,5% | nessuno: è tutto viso |
| dissolvenza | applicata dal retino (sembra polvere) | **dentro l'immagine**, come sfocatura tonale |

Il viso a pieno campo non è una scelta di gusto: **elimina il problema del
fondo e raddoppia i punti che lavorano.** Ogni punto dell'opera porta viso.

La dissolvenza — la metà destra che perde definizione — è meglio che stia
nell'immagine, come modellato più morbido, invece di essere ottenuta togliendo
punti a caso. I punti tolti a caso, visti da 6 m, sembrano sporco.

---

## 3. Il collaudo, prima di ordinare qualsiasi cosa

Non è un giudizio: è un comando che dà un numero.

```bash
python3 viso.py --foto ritratto.png --out prova.png --senza-dissolvenza
```

Stampa tre righe. Quella che decide è la terza:

```
  frazione nella finestra utile del moire': 87%  ->  ok
```

**È la percentuale di immagine che cade dove il moiré esiste** (densità entro
±0,30 dal fondo 0,3848). Sotto il 70% l'immagine si rifà: significa che
troppa superficie è finita nei neri chiusi o nei bianchi bruciati, e su quella
superficie l'opera non si muove.

Se il numero è basso, il rimedio non è ritoccare qui: è chiedere di nuovo
l'immagine **più piatta**. Comprimere in post una foto contrastata lascia
bande di posterizzazione che il retino amplifica.

Poi si guarda l'effetto vero:

```bash
python3 genera_layer.py --foto ritratto.png    # i due file di stampa 1:1
python3 video.py --foto ritratto.png           # il video del movimento
```

---

## 4. Le tre domande da fare all'immagine finita

Guardandola **a occhi socchiusi**, da lontano, o rimpicciolita a 100 px:

1. **Si legge ancora un viso?** Se sparisce, si perde anche nell'opera:
   il retino a 6 mm è più brutale di qualunque miniatura.
2. **Le due metà sono diverse?** Una deve essere ferma e l'altra incerta.
   Non due luminosità diverse: due *gradi di definizione* diversi.
3. **Lo sguardo si chiude?** Non deve. Se i due occhi convergono, il viso
   ha un'identità, e questa è l'unica cosa che l'opera non deve dargli.

---

## 5. Se si preferisce una fotografia vera

La pipeline non distingue. Vincoli identici a quelli sopra, più uno:
il ritratto va scattato con una **sorgente grande e vicina** (softbox o
finestra) e **senza controluce**. In posa: sguardo appena divergente, bocca
rilassata, testa frontale con una rotazione di 2-3 gradi appena.

Se il soggetto è una persona reale e riconoscibile, la sua liberatoria è un
atto dell'autore e non di questo repository — qui si dice solo che serve.
