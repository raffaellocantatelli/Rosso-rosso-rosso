# Opera a due strati — specifica di produzione

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Titolo di lavoro: *Il viso cerca l'identità*. Vetro stampato, 50 mm d'aria,
plexiglas stampato. Area visibile 600 × 800 mm.

Ogni numero di questo documento esce da `ottica.py` ed è stato messo alla
prova da `verifica_ottica.py`, che rende i due strati pixel per pixel e
**misura** il moiré invece di descriverlo. Chi vuole rifare i conti:

```bash
python3 ottica.py              # la tavola completa
python3 verifica_ottica.py --suite   # i quattro casi, incluso quello di controllo
python3 genera_layer.py        # i due file di stampa e le anteprime
```

---

## 1. Come funziona, in tre righe

Due reticoli di punti neri con lo **stesso passo** (6,00 mm), uno sul vetro e
uno sul plexi, ruotati fra loro di **0,86°**. Quando ti sposti, la parallasse
fra i due piani fa scorrere il reticolo dietro di pochi millimetri; la
rotazione moltiplica quello scorrimento **66,6 volte** e lo trasforma in una
struttura di macchie chiare e scure larga 400 mm che attraversa il quadro.

Il viso sta sul plexi, retinato allo stesso passo. Dove le macchie sono
allineate il punto del vetro copre quello del viso e **tutti i toni sotto il
38% spariscono**: restano occhi, narici, taglio della bocca — una maschera.
Dove sono disallineate il viso c'è tutto. Il confine fra le due condizioni
scorre sul viso mentre cammini.

**Non appare e scompare: viene attraversato da una soglia di riconoscibilità.**

---

## 2. Distinta

| | |
|---|---|
| **Vetro** | float extra-chiaro (basso tenore di ferro), **6 mm**, ricotto, bordi lucidati a filo piatto. Non temprato: la tempra introduce distorsione a onda e iridescenze che qui competono con l'effetto. Se la norma impone il vetro di sicurezza: stratificato 3+3 extra-chiaro con PVB trasparente (+0,76 mm, ininfluente). |
| **Stampa sul vetro** | **faccia 2** (interna, verso l'intercapedine). Smalto ceramico nero cotto, oppure UV con primer. Densità ottica ≥ 2,0 — doppia passata se serve. Nessun bianco, nessun fondo: il vetro resta trasparente fra i punti. |
| **Plexiglas** | PMMA **colato** (non estruso: l'estruso ha disomogeneità di spessore), 5 mm, **bianco opaco**, 630 × 830 mm. |
| **Stampa sul plexi** | **prima superficie**, quella rivolta all'intercapedine. Nero UV **opaco e matt** (gloss ≤ 15 GU). Matt non è un gusto: il lucido aggiunge una quarta superficie speculare che riflette la griglia del vetro. |
| **Distanziali** | 4 colonne tornite, **50,0 mm ± 0,2**, acciaio o alluminio anodizzato nero, agli angoli, forate sul plexi (non sul vetro). |
| **Peso** | vetro 7,2 kg + plexi 3,1 kg + ferramenta ≈ **11 kg**. Fissaggi a parete per 60 kg (coefficiente 4 + peso proprio). |

**Alternativa possibile:** viso in seconda superficie su PMMA trasparente con
fondo bianco coprente. Neri più profondi e più profondità, ma la distanza
efficace passa da 50,00 a 53,36 mm (il PMMA rifrange) e compare un fantasma
della griglia 100 mm dietro il piano, allo 0,16%. `ottica.py` calcola
entrambe: `Progetto(plexi_prima_superficie=False)`.

---

## 3. I due file

| File | Formato | Contenuto |
|---|---|---|
| `uscita/vetro_griglia.svg` | 600 × 800 mm, 1:1 | 13.400 punti neri Ø 4,20 mm, passo 6,00 mm, copertura 38,5% |
| `uscita/plexi_viso.svg` | 630 × 830 mm, 1:1 | 14.595 punti, Ø da 0,47 a 5,91 mm, stesso passo 6,00 mm |

I 15 mm di margine per lato sul plexi **servono alla rotazione** e restano
coperti. Il viso nel file è pre-ruotato di −0,86°, così dopo il montaggio
torna dritto mentre il suo reticolo è ruotato: il moiré nasce dai punti, non
dal viso.

Punti sotto 0,30 mm non sono stampati. Non è una scelta estetica: sotto quel
diametro il getto UV non è ripetibile, e un'opera che dipende dalla giornata
dello stampatore non è riproducibile.

---

## 4. Montaggio — l'unica operazione critica

Il vetro va **a squadro**. L'angolo si dà **ruotando il plexi**, che sta
dietro ed è sovradimensionato: la sua rotazione non si vede.

```
alpha = 0,86°  ->  sfalsamento di 12,5 mm fra i due angoli del lato lungo
                   (830 mm × tan 0,86°),  9,5 mm sul lato corto
```

Procedura: si monta il plexi su asole, si porta lo sfalsamento a 12,5 mm con
spessori calibrati, si guarda l'opera da 2,5 m e **si regola a vista**. Il
periodo delle macchie cambia con l'inverso dell'angolo:

| alpha | periodo | macchie sull'altezza |
|---|---|---|
| 0,60° | 573 mm | 1,4 |
| **0,86°** | **400 mm** | **2,0** |
| 1,20° | 286 mm | 2,8 |
| 1,72° | 200 mm | 4,0 |

Stringere l'angolo fa macchie più piccole e più numerose; allargarlo le fa
grandi e rade. Sotto ~0,4° le macchie diventano più grandi del quadro e
l'opera sembra solo cambiare luminosità.

**Perché così e non stampando la rotazione nel file:** un angolo impresso
nella stampa non si corregge più. Questo si regola in cinque minuti, davanti
all'opera, con l'illuminazione definitiva.

---

## 5. Tolleranze, e perché ciascuna vale quel numero

| Grandezza | Tolleranza | Cosa succede se sfora |
|---|---|---|
| Intercapedine | **± 0,5 mm** | cambia la sensibilità dell'1%: irrilevante |
| Planarità del plexi | **± 1,5 mm** | 1 mm di imbarcamento sposta la macchia di 12 mm su 400 (3%) e solo agli angoli obliqui: a 0° non fa niente |
| Angolo alpha | **± 0,05°** | ±6% sul periodo. Si regola a vista, quindi è la tolleranza meno impegnativa |
| **Scala fra le due stampe** | **± 0,15%** | **è la tolleranza dura.** Vedi sotto |
| Registro fra i due strati | **nessuno** | i due file non vanno allineati fra loro. Il moiré è un battimento globale: spostare uno strato sposta le macchie, non le rompe. Non pagare un registro che non serve |

**La tolleranza di scala.** Uno scarto di scala non voluto `eps` si somma
vettorialmente alla rotazione: la direzione delle macchie ruota di
`atan(eps/alpha)`. Con alpha = 0,015 rad:

- eps = 0,1% → le macchie corrono inclinate di 3,8°: impercettibile
- eps = 0,5% → inclinate di 18°: si vede
- eps = 1,5% → 45°: le macchie scorrono in diagonale invece che in verticale

Quindi: **stampare i due file sulla stessa macchina, nella stessa giornata,
sullo stesso lotto di supporto**, e chiedere il rapporto dimensionale.

**Il collaudo è l'opera stessa.** Ci si sposta lateralmente e si guarda dove
vanno le macchie:

- **scorrono in verticale** → le due scale coincidono, è giusto
- **scorrono in diagonale** → una delle due stampe è fuori scala, e
  l'inclinazione dice di quanto
- **scorrono in orizzontale** → la rotazione non c'è: il plexi è a squadro

Non serve strumentazione: la direzione del movimento *è* la misura.

---

## 6. Luce e riflessi

**Il velo speculare.** Tre interfacce aria/materiale (faccia 1 e 2 del vetro,
faccia del plexi). Cascata, non somma:

| angolo | velo | con antiriflesso su faccia 1 |
|---|---|---|
| 0–15° | 11,9% | 8,9% |
| 30° | 12,3% | 9,2% |
| 45° | 14,7% | 11,1% |
| 60° | 24,8% | 19,0% |
| 70° | 43,4% | 34,2% |

Fino a 45° il velo è sotto il 15% e il moiré (contrasto misurato 0,38) resta
largamente leggibile. **Oltre i 60° l'opera si spegne**: è il velo, non il
moiré, a definire dove si può stare. Zona di lavoro: **± 25°**, cioè ±1,2 m
di traverso a 2,5 m di distanza.

**Il cono specchio.** Chi guarda da +θ vede riflesso ciò che sta a −θ. Su
±25° a 2,5 m questo significa una fascia larga ±1,2 m sulla parete di fronte:
**deve essere scura e senza sorgenti**.

**La luce, e il terzo reticolo.** I reticoli in gioco sono tre, non due: la
griglia del vetro come la vedi, il **retino del viso**, e **l'ombra della
griglia proiettata sul viso dalla lampada**. L'ombra genera un moiré proprio
che non si muove quando ti muovi tu — si muove se sposti la lampada.

Per farla sparire serve una penombra più larga del passo. Con
un'intercapedine di 50 mm e una lampada a 1,5 m:

```
penombra = larghezza_sorgente × 50 / 1500 = larghezza / 30
```

Per una penombra di 12 mm (due passi) serve una **sorgente larga almeno
360 mm a 1,5 m**: barra LED diffusa o softbox, incidenza 35–45° dall'alto,
fuori dal cono ±30°. Con un faretto puntiforme (< 50 mm) la penombra è
1,7 mm, l'ombra resta netta e il secondo moiré compare.

Le due condizioni sono entrambe difendibili — la seconda aggiunge una
struttura fissa che il visitatore non controlla. **Va scelta, non subita.**
Confronto reso: `uscita/luce_diffusa.png` e `uscita/luce_faretto35.png`.

---

## 7. Le due distanze di lettura

| distanza | cosa si vede |
|---|---|
| 1,0–1,5 m | i punti, uno per uno. Nessun viso. Una griglia che respira |
| **2,5 m** | il punto sottende 8,3′ (l'acuità è ~1′): il viso è **sulla soglia**, si riconosce e non si legge |
| oltre 5,2 m | i punti fondono, il viso si compone, e resta solo la macchia che lo attraversa |

La soglia di fusione (5,2 m) è una conseguenza del passo di 6 mm, non una
scelta a parte. Passo più fine = viso leggibile più da vicino, ma movimento
più nervoso: un ciclo ogni `p × D / 50` mm di spostamento — 300 mm con
p = 6 mm a 2,5 m, 200 mm con p = 4 mm.

**Sala consigliata: profondità utile ≥ 4 m**, traverso libero ≥ 2,5 m.
L'opera ha bisogno che ci si cammini davanti: senza traverso non esiste.

---

## 8. Cosa è stato verificato, e cosa no

**RECUPERATO** (eseguito, `verifica_ottica.py --suite`): su campo piatto, i
due strati resi pixel per pixel danno periodo 400,1 mm contro i 399,7 previsti,
direzione 89,6° contro 89,6°, magnificazione 67,0× contro 66,6× (errore 0,5%),
contrasto Michelson 0,38. Il caso di controllo (nessuna rotazione, nessuno
scarto di scala) dà contrasto 0,0000: la banda non la produce il renderer.
Anche i casi di sola scala e misto tornano entro l'1,5%.

**INFERITO**: i valori di riflettanza vengono da Fresnel con n = 1,52 e 1,49,
non da una misura su questi materiali. Lo scostamento atteso è di frazioni di
punto, ma è un calcolo, non una lettura.

**UNKNOWN — da verificare sul prototipo, non da qui:**

- la resa reale del nero ceramico sul vetro (l'opacità dichiarata è un obiettivo);
- se a 0,86° l'effetto sia troppo forte o troppo debole **per l'occhio**: il
  contrasto è misurato, il giudizio no;
- il comportamento con luce mista ambiente + artificiale;
- se il viso procedurale regga come opera o serva una fotografia.

**Prima di ordinare 600 × 800: fare un provino da 300 × 400 mm** con la stessa
intercapedine di 50 mm e lo stesso passo. Costa una frazione e risponde a
tutte e quattro le domande qui sopra. Il passo e l'intercapedine devono
restare quelli definitivi — sono loro a fissare l'effetto, non le dimensioni.
