# Il viso cerca l'identità — opera a due strati

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Vetro stampato · 50 mm d'aria · plexiglas stampato. Area visibile 600 × 800 mm.
Due reticoli di punti neri con lo **stesso passo** (6,00 mm), ruotati fra loro
di **0,86°**. La parallasse fra i due piani sposta il reticolo dietro di pochi
millimetri quando ti muovi; la rotazione moltiplica quello scorrimento **66,6
volte** e lo trasforma in macchie larghe 400 mm che attraversano il quadro.

Dove le macchie sono allineate, il punto del vetro copre quello del viso e
tutti i toni sotto il 38% spariscono: restano occhi, narici, taglio della
bocca. Dove sono disallineate, il viso c'è tutto. **Il viso non appare e
scompare: viene attraversato da una soglia di riconoscibilità.**

Ti muovi in orizzontale, le macchie scorrono in **verticale**. Non è un
effetto collaterale: è la firma della rotazione, e distingue questo montaggio
da uno sbagliato.

---

## I file

| | |
|---|---|
|  `PROGETTO_DEFINITIVO.md` | **quello che va allo stampatore e al montatore.** Materiali, tolleranze, angolo, luce, collaudo |
| `ottica.py` | la fisica: parallasse con rifrazione, moiré da vettore d'onda esatto, Fresnel. Nessun numero del progetto nasce altrove |
| `collaudo.py` | **il filtro sulle immagini candidate.** Le misura tutte, le classifica, dice a che ampiezza tonale reggono e produce il contatto dei due stati |
| `viso.py` | il viso come superficie 3D illuminata, non come disegno. Accetta anche una fotografia |
| `genera_layer.py` | i due file di stampa in SVG 1:1 e il compositore fisico |
| `verifica_ottica.py` | **il falsificatore.** Rende i due strati pixel per pixel e misura il moiré |
| `video.py` | il video dell'effetto + la verifica incrociata fra i due renderer |
| `simulatore.html` | il banco interattivo: muovi il puntatore, o inclina il telefono |
| `uscita/vetro_griglia.svg` | 600 × 800 mm — 13.400 punti Ø 4,20 mm |
| `uscita/plexi_viso.svg` | 636 × 836 mm — 14.840 punti, Ø 0,47–5,92 mm |
| `uscita/p45_*.svg` | la stessa opera a passo 4,50 mm: 23.674 valori di tono invece di 13.300 |
| `uscita/effetto.mp4` | 23 s: la macchia che attraversa il viso, poi i punti da vicino |

## I comandi

```bash
python3 progetto.py                   # rigenera progetto.json e il brief
python3 progetto.py --verifica        # il JSON e' ancora quello del codice?
python3 ottica.py                     # la tavola completa dei numeri
python3 verifica_ottica.py --suite    # i 4 casi, incluso quello di controllo
python3 video.py --verifica           # renderer veloce contro renderer falsificato
python3 genera_layer.py               # i due SVG + le anteprime del movimento
python3 video.py                      # il video dell'effetto
python3 collaudo.py ritratti/ --passo 4.5     # collauda tutte le candidate
python3 collaudo.py ritratti/ --passo 4.5 --stampa   # e genera i file dalla migliore
```

```bash
python3 -m pip install -r requisiti.txt
```

Per il **collaudo delle immagini** bastano `numpy` e `pillow`: `collaudo.py`
importa solo `viso.py`. `imageio-ffmpeg` serve unicamente al video. Il
simulatore non ha dipendenze: è un file solo.

Il viso procedurale di `viso.py` è un **segnaposto verificabile**: serve a
provare l'ottica, non a reggere un'opera. Va sostituito — `BRIEF_GEMINI.md`
dice con cosa, e come accorgersi se l'immagine nuova non va bene.

## Cosa è verificato e cosa no

**RECUPERATO** — eseguito, `verifica_ottica.py --suite`, su campo piatto:

| | previsto | misurato |
|---|---|---|
| periodo della banda | 399,7 mm | 400,1 mm |
| direzione | 89,6° | 89,6° |
| magnificazione | 66,6 × | 67,0 × |
| contrasto Michelson | — | 0,38 |
| **controllo** α=0, ε=0 | nessuna banda | contrasto **0,0000** |

E `video.py --verifica`, renderer veloce contro quello falsificato:
correlazione **0,9996**, scarto d'ampiezza ≤ 1,5%.

L'ultima riga è la più importante: senza scarto fra i due reticoli non compare
nessuna banda. **La banda non la produce il renderer.**

**INFERITO** — le riflettanze vengono da Fresnel con n = 1,52 e 1,49, non da
una misura su questi materiali.

**UNKNOWN** — la resa del nero ceramico sul vetro; se 0,86° sia giusto *per
l'occhio* (il contrasto è misurato, il giudizio no); il comportamento con luce
mista; se l'immagine definitiva regga il retino.

**Prima di ordinare 600 × 800: un provino da 300 × 400 mm**, con la stessa
intercapedine di 50 mm e lo stesso passo. Costa una frazione e risponde a
tutte e quattro le domande.
