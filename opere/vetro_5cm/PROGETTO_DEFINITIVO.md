# Il viso cerca l'identità — progetto definitivo

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
Vetro stampato · 50 mm d'aria · plexiglas retinato. Area visibile 600 × 800 mm.

Questo file sostituisce `SPECIFICA_TECNICA.md`: un concetto, un file (CLAUDE.md
§6 regola 2). Ogni numero esce da `ottica.py` ed è stato messo alla prova da
`verifica_ottica.py`, che rende i due strati pixel per pixel e **misura** il
moiré invece di descriverlo.

```bash
python3 progetto.py                   # rigenera progetto.json + il brief
python3 progetto.py --verifica        # il JSON e' ancora quello del codice?
python3 ottica.py                     # la tavola completa
python3 verifica_ottica.py --suite    # 4 casi, incluso quello di controllo
python3 video.py --verifica           # renderer veloce contro renderer lento
python3 genera_layer.py               # i due file di stampa
python3 video.py                      # il video dell'effetto
```

**`progetto.json` è il progetto in forma leggibile da una macchina** — ogni
numero, il brief dell'immagine, e gli esiti di verifica misurati. Non è scritto
a mano: lo genera `progetto.py` calcolando dall'ottica, leggendo i file di
stampa veri ed eseguendo i falsificatori. Un JSON con i numeri trascritti
sarebbe una seconda verità che invecchia in silenzio.

---

## 1. Il meccanismo, in tre righe

Due reticoli di punti neri con lo **stesso passo** (6,00 mm), uno sul vetro e
uno sul plexi, ruotati fra loro di **0,86°**. Quando ti sposti, la parallasse
fra i due piani fa scorrere il reticolo dietro di pochi millimetri; la
rotazione moltiplica quello scorrimento **66,6 volte** e lo trasforma in
macchie larghe 400 mm che attraversano il quadro.

Il viso sta sul plexi, retinato allo stesso passo. Dove le macchie sono
allineate il punto del vetro copre quello del viso e **tutti i toni sotto il
38% rientrano nel fondo**: restano occhi, narici, taglio della bocca. Dove
sono disallineate, il viso c'è tutto.

**Non appare e scompare: viene attraversato da una soglia di riconoscibilità.**

---

## 2. Le cinque decisioni, e perché sono quelle

**1. Il fondo non è bianco — è al 38,5%, come il reticolo del vetro.**
Il moiré nasce dal punto davanti che copre quello dietro: su bianco non c'è
niente da coprire, su nero pieno il punto sparisce dentro. L'effetto è massimo
dove i due punti hanno **lo stesso diametro**. Perciò il campo è stampato alla
copertura del reticolo e il viso modula intorno a quel valore: nelle bande
allineate il viso **rientra nel campo** invece di bucarlo. È letteralmente la
perdita di identità, non una metafora.

**2. L'angolo si dà ruotando il plexi al montaggio, non stampandolo.**
Il plexi sta dietro ed è sovradimensionato: la sua rotazione non si vede, e si
regola a spessori in cinque minuti davanti all'opera con la luce definitiva.
Un angolo impresso nella stampa non si corregge più.

**3. Il margine del plexi è 18 mm: tre passi esatti.**
Non è un numero tondo scelto a caso. Il reticolo della lastra dietro sta a
`(i+0,5)·passo − margine`; se il margine non è multiplo intero del passo, quel
reticolo cade sfasato rispetto a quello del vetro. Con 15 mm lo sfasamento
valeva **mezza cella**, e mezza cella **inverte** il moiré: dove dovrebbe
esserci allineamento c'è disallineamento. Trovato confrontando due renderer
(correlazione −0,96: stessa ampiezza, stessa periodicità, fase opposta).
*Un'ampiezza giusta non dimostra niente.*

**4. Il viso a pieno campo, e il soggetto è Raffaello Cantarelli.**
Il pieno campo raddoppia i punti che lavorano (100 × 133 invece di ~55 × 103)
ed elimina il problema del fondo. Il volto non è inventato: i tratti canonici
stanno in `RAFFAELLO_BODY_V1.1` su Drive — entità **progettata** da Claudio
Terzi, non una persona esistente. Il brief completo è in `BRIEF_GEMINI.md`,
generato da `progetto.json`.

**Il passo è una decisione aperta.** A 6,00 mm l'opera ha 13.300 valori di
tono e il viso si compone oltre 5,2 m. A **4,50 mm** ne ha 23.674 e si compone
a 3,9 m — cioè dentro una stanza normale — al prezzo di un movimento più
sensibile (un ciclo ogni 225 mm invece di 300) e di 23.852 punti da stampare
sul vetro invece di 13.400. **Se il viso deve avvicinarsi al ritratto, è 4,50.**
I file di entrambe le configurazioni sono in `uscita/` (`p45_*` per la seconda);
il margine da 18 mm è commensurabile con tutti e due i passi.

**5. La stampa sul plexi è in prima superficie e matt.**
Il lucido aggiunge una quarta superficie speculare che riflette la griglia del
vetro. In prima superficie la distanza efficace è **50,00 mm esatti**; in
seconda diventa 53,36 (il PMMA rifrange) e compare un fantasma della griglia
100 mm dietro il piano, allo 0,16%.

---

## 3. Distinta

| | |
|---|---|
| **Vetro** | float extra-chiaro (basso ferro), **6 mm**, ricotto, bordi lucidati a filo piatto. Non temprato: distorsione a onda e iridescenze competono con l'effetto. Se serve vetro di sicurezza: stratificato 3+3 extra-chiaro, PVB trasparente (+0,76 mm, ininfluente) |
| **Stampa sul vetro** | **faccia 2** (interna). Smalto ceramico nero cotto, o UV con primer. Densità ottica ≥ 2,0, doppia passata se serve. Nessun bianco: il vetro resta trasparente fra i punti |
| **Plexiglas** | PMMA **colato** (non estruso), 5 mm, **bianco opaco**, **636 × 836 mm** |
| **Stampa sul plexi** | **prima superficie**, verso l'intercapedine. Nero UV opaco e **matt** (gloss ≤ 15 GU) |
| **Distanziali** | 4 colonne tornite, **50,0 mm ± 0,2**, forate sul plexi (non sul vetro) |
| **Peso** | vetro 7,2 + plexi 3,3 + ferramenta ≈ **11 kg**. Fissaggi per 60 kg |

## 4. I due file di stampa

| File | Formato 1:1 | Contenuto |
|---|---|---|
| `uscita/vetro_griglia.svg` | 600 × 800 mm | 13.400 punti Ø 4,20 mm, passo 6,00, copertura 38,5% |
| `uscita/plexi_viso.svg` | 636 × 836 mm | 14.840 punti, Ø 0,47–5,92 mm, stesso passo |

I 18 mm di margine per lato servono alla rotazione e restano coperti. Il viso
nel file è **pre-ruotato di −0,86°**: dopo il montaggio torna dritto mentre il
suo reticolo è ruotato. Il moiré nasce dai punti, non dal viso.

Punti sotto 0,30 mm non sono stampati: sotto quel diametro il getto UV non è
ripetibile, e un'opera che dipende dalla giornata dello stampatore non è
riproducibile.

---

## 5. Montaggio — l'unica operazione critica

Il vetro va **a squadro**. L'angolo si dà ruotando il plexi:

```
alpha = 0,86°  ->  12,55 mm di sfalsamento fra i due angoli del lato lungo
                    9,55 mm sul lato corto
```

Si monta il plexi su asole, si porta lo sfalsamento a 12,55 mm con spessori
calibrati, si guarda da 2,5 m e **si regola a vista**:

| alpha | periodo | macchie sull'altezza |
|---|---|---|
| 0,60° | 573 mm | 1,4 |
| **0,86°** | **400 mm** | **2,0** |
| 1,20° | 286 mm | 2,8 |
| 1,72° | 200 mm | 4,0 |

Sotto ~0,4° le macchie diventano più grandi del quadro e l'opera sembra solo
cambiare luminosità.

---

## 6. Tolleranze, e perché ciascuna vale quel numero

| Grandezza | Tolleranza | Cosa succede se sfora |
|---|---|---|
| Intercapedine | ± 0,5 mm | cambia la sensibilità dell'1%: irrilevante |
| Planarità del plexi | ± 1,5 mm | 1 mm di imbarcamento sposta la macchia di 12 mm su 400 (3%), e solo agli angoli obliqui |
| Angolo alpha | ± 0,05° | ±6% sul periodo. Si regola a vista: è la tolleranza meno impegnativa |
| **Scala fra le due stampe** | **± 0,15%** | **è la tolleranza dura** |
| Registro fra i due strati | **nessuno** | i due file non vanno allineati fra loro. Il moiré è un battimento globale: spostare uno strato sposta le macchie, non le rompe. **Non pagare un registro che non serve** |

**La tolleranza di scala.** Uno scarto non voluto `eps` si somma
vettorialmente alla rotazione: la direzione delle macchie ruota di
`atan(eps/alpha)`. Con alpha = 0,015 rad: 0,1% → 3,8° (impercettibile);
0,5% → 18° (si vede); 1,5% → 45° (le macchie vanno in diagonale).

Perciò: **stessa macchina, stessa giornata, stesso lotto di supporto**, e
farsi dare il rapporto dimensionale.

**Il collaudo è l'opera stessa.** Ci si sposta lateralmente e si guarda dove
vanno le macchie:

- **verticale** → le due scale coincidono: è giusto
- **diagonale** → una stampa è fuori scala, e l'inclinazione dice di quanto
- **orizzontale** → la rotazione non c'è: il plexi è a squadro

Non serve strumentazione. **La direzione del movimento *è* la misura.**

---

## 7. Luce e riflessi

**Velo speculare** — tre interfacce aria/materiale, in cascata:

| angolo | velo | con antiriflesso su faccia 1 |
|---|---|---|
| 0–15° | 11,9% | 8,9% |
| 30° | 12,3% | 9,2% |
| 45° | 14,7% | 11,1% |
| 60° | 24,8% | 19,0% |
| 70° | 43,4% | 34,2% |

Fino a 45° il velo è sotto il 15% e il moiré (contrasto misurato 0,38) resta
leggibile. **Oltre i 60° l'opera si spegne**: è il velo, non il moiré, a
decidere dove si può stare. Zona di lavoro **± 25°**, cioè ±1,2 m di traverso
a 2,5 m.

**Il cono specchio.** Chi guarda da +θ vede riflesso ciò che sta a −θ: una
fascia larga ±1,2 m sulla parete di fronte, che **deve essere scura e senza
sorgenti**.

**La luce, e il terzo reticolo.** I reticoli sono tre, non due: la griglia del
vetro, il retino del viso, e **l'ombra della griglia proiettata sul viso dalla
lampada**. L'ombra genera un moiré proprio che non si muove quando ti muovi tu
— si muove se sposti la lampada. Per farla sparire serve una penombra più
larga del passo:

```
penombra = larghezza_sorgente × 50 / distanza_sorgente
```

Per 12 mm di penombra serve una **sorgente larga almeno 360 mm a 1,5 m**:
barra LED diffusa o softbox, incidenza 35–45° dall'alto, fuori dal cono ±30°.
Con un faretto puntiforme (< 50 mm) la penombra è 1,7 mm e il secondo moiré
resta. Entrambe le condizioni sono difendibili: **va scelta, non subita.**
Confronto reso: `uscita/luce_diffusa.png` e `uscita/luce_faretto35.png`.

---

## 8. Le due distanze di lettura

| distanza | cosa si vede |
|---|---|
| 1,0–1,5 m | i punti, uno per uno. Nessun viso. Una griglia che respira |
| **2,5 m** | il punto sottende 8,3′ (l'acuità è ~1′): il viso è **sulla soglia** |
| oltre 5,2 m | i punti fondono, il viso si compone, resta la macchia che lo attraversa |

**Sala: profondità utile ≥ 4 m, traverso libero ≥ 2,5 m.** L'opera ha bisogno
che ci si cammini davanti: senza traverso non esiste.

---

## 9. Cosa è verificato e cosa no

**RECUPERATO** — eseguito.

`verifica_ottica.py --suite`, su campo piatto, due strati resi pixel per pixel:

| | previsto | misurato |
|---|---|---|
| periodo della banda | 399,7 mm | 400,1 mm |
| direzione | 89,6° | 89,6° |
| magnificazione | 66,6 × | 67,0 × |
| contrasto Michelson | — | 0,38 |
| **controllo** α=0, ε=0 | nessuna banda | **0,0000** |

`video.py --verifica`, renderer veloce contro quello falsificato: correlazione
**0,9996**, scarto d'ampiezza ≤ 1,5% su quattro angoli.

**INFERITO** — le riflettanze vengono da Fresnel con n = 1,52 e 1,49, non da
una misura su questi materiali.

**UNKNOWN — da chiudere sul prototipo, non da qui:**

- la resa reale del nero ceramico sul vetro;
- se 0,86° sia giusto **per l'occhio**: il contrasto è misurato, il giudizio no;
- il comportamento con luce mista ambiente + artificiale;
- se l'immagine definitiva regga il retino (criterio eseguibile in `BRIEF_GEMINI.md` §3).

---

## 10. Sequenza operativa

1. **L'immagine.** `BRIEF_GEMINI.md`, poi il collaudo:
   `python3 viso.py --foto ritratto.png --senza-dissolvenza` → frazione utile ≥ 70%
2. **I file.** `python3 genera_layer.py --foto ritratto.png`
3. **Il controllo a video.** `python3 video.py --foto ritratto.png`, e il
   simulatore interattivo
4. **Il provino 300 × 400 mm.** Stessa intercapedine da 50 mm, stesso passo da
   6 mm. Costa una frazione e chiude tutti e quattro gli UNKNOWN
5. **Solo dopo**, il 600 × 800

**Il passo e l'intercapedine devono restare quelli definitivi anche nel
provino** — sono loro a fissare l'effetto, non le dimensioni del quadro.
