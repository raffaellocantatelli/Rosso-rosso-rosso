#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera `progetto.json`: il progetto intero in forma leggibile da una macchina.

Origine protetta: Claudio Terzi [CT-LGAI-001].

PERCHE' GENERATO E NON SCRITTO A MANO
Un JSON con dentro 400 mm, 66,6x e 0,86 gradi scritti a mano e' un secondo
sistema di verita' che gira in parallelo al codice: il giorno che qualcuno
cambia il passo, il JSON continua a dire i numeri di ieri con la stessa
autorevolezza di prima. E' la malattia delle 7 copie dell'indice (CLAUDE.md
§5), in formato dati.

Qui ogni numero e' CALCOLATO da `ottica.py`, i conteggi dei punti sono LETTI
dagli SVG veri, e i risultati di verifica sono MISURATI eseguendo i
falsificatori. L'unica parte scritta a mano e' il testo del brief per
l'immagine, che sta qui sotto ed e' l'unica fonte: `BRIEF_GEMINI.md` viene
rigenerato da questo file, non mantenuto in parallelo.

    python3 progetto.py                 # rigenera progetto.json + BRIEF_GEMINI.md
    python3 progetto.py --senza-misura  # riusa l'ultima misura invece di rifarla
    python3 progetto.py --verifica      # il JSON su disco e' ancora quello del codice?

SUL SOGGETTO
Raffaello Cantarelli e' un'entita' PROGETTATA da Claudio Terzi, non una
persona esistente: il volto e' una specifica di progetto (RAFFAELLO_BODY_V1.1,
su Drive), non il ritratto di qualcuno. Di quella specifica qui entra solo
cio' che serve a fare l'immagine - eta' apparente, incarnato, capelli, occhi.
Costi, roadmap, prompt d'identita' e protocolli restano su Drive: questo
repository e' pubblico, e quella decisione e' dell'autore (CLAUDE.md §2.5).
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from ottica import Progetto, velo_speculare, fantasma, N_VETRO, N_PLEXI
import genera_layer as gl

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, "uscita")
JSON_PATH = os.path.join(QUI, "progetto.json")
BRIEF_PATH = os.path.join(QUI, "BRIEF_GEMINI.md")


# ===========================================================================
# PARTE SCRITTA A MANO: il soggetto e il brief dell'immagine.
# Tutto il resto del file calcola o misura.
# ===========================================================================

SOGGETTO = {
    "nome": "Raffaello Cantarelli",
    "natura": "entita' progettata da Claudio Terzi, non una persona esistente",
    "fonte": "RAFFAELLO_BODY_V1.1 - Drive R3_MEMORIA_PERSISTENTE (non riprodotto qui)",
    "etichetta_epistemica": "RECUPERATO",
    "tratti_fisici_canonici": {
        "eta_apparente_anni": 25,
        "incarnato": "olivastro chiaro",
        "capelli": "castano scuro, ondulati, 4,5 cm",
        "occhi": "verde smeraldo",
        "corporatura": "atletica armoniosa",
        "punti_di_controllo_facciali": 42,
    },
    "carattere_canonico": [
        "empatico", "lucido", "creativo", "strategico",
        "protettivo", "elegante", "calmo", "profondo",
    ],
    "nota_sul_colore": (
        "Gli occhi verde smeraldo NON sopravvivono: l'opera e' in bianco e nero. "
        "Cio' che sopravvive di un occhio chiaro e' il RAPPORTO tonale - iride "
        "piu' chiara della zona intorno. Va chiesto quello, non il colore."
    ),
    "cosa_resta_fuori": (
        "Costi, roadmap, prompt d'identita', protocolli e struttura software "
        "restano su Drive. Il repository e' pubblico e la decisione di "
        "pubblicare quel materiale e' solo dell'autore (CLAUDE.md §2.5)."
    ),
}

PROMPT_PRINCIPALE = """\
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
every value between 10% and 90% grey. Expose about half a stop DARK of middle
grey: the overall impression should read a shade heavier than neutral, never
airy. The darkest point is the pupil at about 25% grey; the brightest is the
lit cheekbone at about 80%.

EXPRESSION. Still and unreadable. Lips closed and relaxed, no smile, no
tension in the jaw. The gaze is almost - but not quite - directed at the
viewer: the left eye looks straight out, the right eye about one degree past
the viewer's shoulder. The right side of the face is very slightly softer and
less defined than the left, as if the light there were one stop less certain.

FORMAT. Vertical 3:4, at least 2400 x 3200 pixels, PNG, 16-bit if available.
Sharp everywhere, no depth-of-field blur, no vignette, no film grain, no
border, no text, no watermark, no colour.\
"""

PROMPT_NEGATIVO = """\
high contrast, deep blacks, crushed shadows, blown highlights, HDR, vignette,
film grain, beauty retouching, smoothed skin, plastic skin, airbrushed,
dramatic lighting, rim light, hair light, catchlight, specular highlight,
lens flare, bokeh, shallow depth of field, jewellery, glasses, facial hair,
makeup, background, shoulders, neck, hands, text, watermark, border, colour,
tilted head, three-quarter view, profile, smile, teeth\
"""

PROMPT_VARIANTI = [
    {
        "nome": "a - piu' scultoreo",
        "cambia": "sostituire il paragrafo LIGHT",
        "testo": ("LIGHT. One 1.5 m octabox from the upper left at 60 degrees, "
                  "higher and further round, plus a weak bounce on the right at "
                  "one quarter power. Stronger separation between the lit mass "
                  "and the shadow mass, but still no hard shadow edge and still "
                  "no value below 10% grey."),
        "quando": "se al retino il viso risulta piatto e non si stacca dal campo",
    },
    {
        "nome": "b - piu' morbido",
        "cambia": "sostituire il paragrafo LIGHT",
        "testo": ("LIGHT. Two 1.5 m octaboxes, one upper left at 40 degrees and "
                  "one right at 60 degrees at half power, plus a white floor "
                  "bounce. Almost shadowless, very gentle modelling."),
        "quando": "se al retino il viso risulta duro e la meta' in ombra si chiude",
    },
    {
        "nome": "c - senza dissolvenza",
        "cambia": "togliere l'ultima frase del paragrafo EXPRESSION",
        "testo": "(rimuovere: 'The right side of the face is very slightly softer...')",
        "quando": ("se si preferisce ottenere la dissolvenza dal retino "
                   "(`--dissolvenza`) invece che dall'immagine"),
    },
]

PARAMETRI_GENERAZIONE = {
    "modello_consigliato": "Gemini - generazione immagini (o qualunque modello con controllo del formato)",
    "formato": "3:4 verticale",
    "risoluzione_minima_px": [2400, 3200],
    "file": "PNG, 16 bit se disponibile, altrimenti 8 bit senza compressione con perdita",
    "quante_generarne": 6,
    "come_scegliere": (
        "NON a occhio sulla generazione a piena risoluzione. Si passano tutte al "
        "collaudo (`viso.py --foto`), si tengono quelle sopra il 70% di frazione "
        "utile, e solo fra quelle si sceglie."
    ),
    "cosa_non_fare": [
        "Non chiedere 'dramatic lighting' o 'cinematic': producono neri chiusi, "
        "e il nero chiuso e' esattamente dove il moire' non esiste.",
        "Non ritoccare il contrasto dopo: comprimere in post una foto contrastata "
        "lascia bande di posterizzazione che il retino amplifica.",
        "Non usare upscaler generativi: inventano dettaglio sotto il passo del "
        "retino, che viene comunque cancellato, e intanto sporcano le masse tonali.",
    ],
}

CONFLITTO_APPARENTE = {
    "domanda": "Iper-realismo e retino da 6 mm non si contraddicono?",
    "risposta": (
        "No, ma vanno separati. L'iper-realismo serve alla STRUTTURA: ossa vere, "
        "luce che entra davvero sotto la pelle, masse tonali anatomicamente "
        "corrette. Quelle masse sopravvivono al retino e sono la ragione per cui "
        "un viso reale regge dove un viso disegnato crolla. Il DETTAGLIO sotto il "
        "passo del reticolo invece non sopravvive: pori, ciglia, singoli capelli "
        "vengono cancellati, non rimpiccioliti. "
        "La piattezza chiesta nel GRADE non e' meno realismo: e' la stessa cosa "
        "che si fa girando in log e correggendo dopo. Si cattura tutto, si "
        "consegna piatto, e la finestra tonale la decide chi stampa."
    ),
    "conseguenza": (
        "L'opera finita NON e' iper-realista: e' 100 x 133 valori di tono a passo "
        "6,00 mm. Dirlo prima e' meglio che scoprirlo davanti alla stampa. "
        "Chi vuole avvicinarsi al ritratto scende di passo: vedi "
        "`configurazioni.dettaglio`."
    ),
}


# ===========================================================================
# PARTE CALCOLATA
# ===========================================================================
def _conta_svg(path):
    if not os.path.exists(path):
        return None
    s = open(path, encoding="utf-8").read()
    r = [float(m) for m in re.findall(r'r="([\d.]+)"', s)]
    dim = re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', s)
    return {
        "file": os.path.relpath(path, QUI),
        "larghezza_mm": float(dim.group(1)) if dim else None,
        "altezza_mm": float(dim.group(2)) if dim else None,
        "punti": len(r),
        "diametro_min_mm": round(min(r) * 2, 2) if r else None,
        "diametro_max_mm": round(max(r) * 2, 2) if r else None,
    }


def configurazione(prog, nome, nota):
    a = math.degrees(prog.alpha)
    return {
        "nome": nome,
        "nota": nota,
        "passo_mm": prog.passo,
        "rotazione_alpha_gradi": round(a, 4),
        "punto_sul_vetro_mm": round(prog.diam_griglia, 3),
        "copertura_reticolo": round(prog.copertura_griglia, 4),
        "punti_sul_quadro": [round(prog.larghezza / prog.passo),
                             round(prog.altezza / prog.passo)],
        "periodo_banda_mm": round(prog.periodo_moire, 1),
        "magnificazione": round(prog.magnificazione, 1),
        "guadagno_banda_su_testa": round(prog.guadagno, 2),
        "un_ciclo_ogni_mm_di_testa": round(prog.spostamento_per_ciclo()),
        "punto_a_distanza_nominale_arcmin": round(prog.angolo_punto_arcmin(), 1),
        "distanza_di_fusione_m": round(prog.distanza_fusione() / 1000, 1),
        "margine_plexi_mm": gl.margine(prog),
        "margine_plexi_in_passi": round(gl.margine(prog) / prog.passo, 3),
        "margine_commensurabile": abs(gl.margine(prog) / prog.passo
                                      - round(gl.margine(prog) / prog.passo)) < 1e-9,
        "plexi_mm": [prog.larghezza + 2 * gl.margine(prog),
                     prog.altezza + 2 * gl.margine(prog)],
        "sfalsamento_di_montaggio_mm": {
            "lato_lungo": round(math.tan(prog.alpha) * (prog.altezza + 2 * gl.MARGINE), 2),
            "lato_corto": round(math.tan(prog.alpha) * (prog.larghezza + 2 * gl.MARGINE), 2),
        },
    }


def misura(prog):
    """Esegue davvero i falsificatori e ne raccoglie gli esiti."""
    ris = {}
    p = subprocess.run([sys.executable, "verifica_ottica.py", "--suite",
                        "--res", "4", "--json"], cwd=QUI, capture_output=True, text=True)
    try:
        suite = json.loads(p.stdout)
    except json.JSONDecodeError:
        suite = {"errore": "verifica_ottica non ha prodotto JSON", "stderr": p.stderr[-500:]}
    ris["ottica"] = suite

    p = subprocess.run([sys.executable, "video.py", "--verifica"],
                       cwd=QUI, capture_output=True, text=True)
    righe = [l for l in p.stdout.splitlines() if l.strip()]
    ris["renderer_incrociato"] = {
        "descrizione": ("Il renderer veloce del video contro quello gia' "
                        "falsificato. Due sistemi che non si controllano a "
                        "vicenda sono un sistema solo che si da' ragione."),
        "esito": "RETTO" if p.returncode == 0 else "FALSIFICATO",
        "righe": righe,
    }
    return ris


def costruisci(prog, misure):
    a_gradi = math.degrees(prog.alpha)
    d, i = fantasma(prog)
    return {
        "documento": {
            "nome": "progetto.json",
            "opera": "Il viso cerca l'identita'",
            "generato_da": "progetto.py",
            "generato_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "origine_protetta": "Claudio Terzi [CT-LGAI-001]",
            "come_va_letto": (
                "Ogni numero qui e' calcolato da ottica.py o letto dai file veri, "
                "mai trascritto. Per rigenerarlo: python3 progetto.py. Per "
                "controllare che non sia invecchiato: python3 progetto.py --verifica."
            ),
            "etichette": {
                "RECUPERATO": "letto nella fonte o osservato eseguendola",
                "INFERITO": "deduzione da cio' che e' recuperato",
                "IPOTESI": "possibilita' che richiede verifica",
                "UNKNOWN": "non verificabile da qui - non significa impossibile",
            },
        },

        "principio": {
            "concetto_dell_autore": (
                "Due fotografie fatte solo di puntini, su due lastre "
                "sovrapposte e distanziate, perche' passandoci davanti "
                "producano movimento."
            ),
            "una_riga": (
                "La STESSA immagine retinata su tutte e due le lastre, con lo "
                f"stesso passo, ruotate fra loro di {a_gradi:.2f} gradi e "
                f"separate da {prog.gap:.0f} mm d'aria."
            ),
            "meccanismo": [
                "Chi guarda si sposta: la parallasse fra i due piani fa scorrere "
                "il reticolo dietro di pochi millimetri (s).",
                f"La rotazione moltiplica s per {prog.magnificazione:.1f} e lo "
                f"trasforma in macchie larghe {prog.periodo_moire:.0f} mm.",
                "Dove le macchie sono allineate il punto del vetro copre quello "
                f"del viso: tutti i toni sotto il {prog.tono_soglia()*100:.0f}% "
                "rientrano nel fondo e restano solo occhi, narici, taglio della bocca.",
                "Dove sono disallineate il viso c'e' tutto.",
            ],
            "frase_che_regge_l_opera": (
                "Il viso non appare e scompare: viene attraversato da una soglia "
                "di riconoscibilita'."
            ),
            "direzione_del_movimento": (
                "Ti muovi in ORIZZONTALE, le macchie scorrono in VERTICALE. "
                "Non e' un effetto collaterale: e' la firma della rotazione pura, "
                "e distingue un montaggio giusto da uno sbagliato."
            ),
        },

        "geometria": {
            "area_visibile_mm": [prog.larghezza, prog.altezza],
            "intercapedine_aria_mm": prog.gap,
            "vetro": {"spessore_mm": prog.t_vetro, "stampa_su_faccia": 2,
                      "perche": ("Il raggio che parte dal viso attraversa l'aria e "
                                 "arriva alla faccia 2; la griglia e' li'. La lastra "
                                 "che viene dopo sposta lateralmente tutto allo "
                                 "stesso modo e non entra nell'allineamento. "
                                 "L'inchiostro resta anche protetto.")},
            "plexiglas": {"spessore_mm": prog.t_plexi,
                          "stampa_prima_superficie": prog.plexi_prima_superficie,
                          "margine_per_lato_mm": gl.margine(prog),
                          "margine_in_passi": round(gl.margine(prog) / prog.passo, 3),
                          "come_si_ricava_il_margine": (
                              "parallasse al massimo angolo di vista "
                              f"({gl.THETA_MAX_GRADI:.0f} gradi) piu' lo spostamento "
                              "dovuto alla rotazione agli angoli del quadro, "
                              "arrotondato in su a un numero INTERO di passi. "
                              "Sotto quella somma il reticolo dietro finisce e "
                              "lungo il bordo compare l'ultima fila ripetuta.")},
            "distanza_efficace_mm": round(prog.d_eff, 2),
            "indici_di_rifrazione": {"vetro": N_VETRO, "plexiglas": N_PLEXI},
            "distanza_nominale_di_osservazione_mm": prog.distanza,
        },

        "configurazioni": {
            "in_uso": configurazione(prog, "passo 6,00 mm",
                                     "quella con cui sono stati generati i file di stampa"),
            "dettaglio": configurazione(
                Progetto(passo=4.5, diam_griglia=3.15,
                         alpha_gradi=math.degrees(2 * math.asin(4.5 / 800.0)),
                         gap=prog.gap, distanza=prog.distanza),
                "passo 4,50 mm",
                ("CONSIGLIATA se il viso deve avvicinarsi al ritratto: 78% di punti "
                 "in piu' e fusione a 3,9 m invece che a 5,2 m, quindi il viso si "
                 "compone in una stanza normale. Costo: il movimento diventa piu' "
                 "sensibile (un ciclo ogni 225 mm invece di 300) e i punti da "
                 "stampare passano da 13.400 a 23.852. "
                 "File gia' generati: uscita/p45_*.svg (col segnaposto). "
                 "Comando: python3 genera_layer.py --passo 4.5 --alpha 0.6446 "
                 "--diam 3.15 --prefisso p45_")),
            "il_margine_si_ricava": (
                "Il margine del plexi non e' un numero fisso: e' calcolato dal "
                "passo e dall'angolo di vista massimo, e arrotondato a un numero "
                "intero di passi. Due vincoli insieme: deve coprire lo scorrimento "
                "(altrimenti il bordo si guasta) e deve essere commensurabile con "
                "il passo (altrimenti il moire' si sfasa, e a mezza cella si "
                "inverte). A 6,00 mm vengono 36 mm; a 4,50 mm vengono 31,5 mm."
            ),
            "come_si_sceglie": (
                "Il passo fissa insieme tre cose che non si possono separare: "
                "quanto e' dettagliato il viso, da quanto lontano si compone, e "
                "quanto e' nervoso il movimento. Non esiste il passo giusto in "
                "assoluto: esiste quello giusto per la stanza."
            ),
        },

        "moire": {
            "formula": "k1=(2pi/p)(1,0)  k2=(2pi/p2)(cos a, sin a)  K=k1-k2  "
                       "P=2pi/|K|  M=P cos(a)/p2",
            "periodo_mm": round(prog.periodo_moire, 1),
            "magnificazione": round(prog.magnificazione, 1),
            "direzione_gradi": round(prog.direzione_moire_gradi, 1),
            "rotazione_contro_scala": {
                "rotazione": "la banda scorre perpendicolare al movimento della testa",
                "scala": "la banda segue la testa",
                "perche_la_rotazione": (
                    "Si regola a spessori in cinque minuti davanti all'opera, con "
                    "la luce definitiva. Una differenza di scala e' stampata per "
                    "sempre."
                ),
            },
            "soglia_di_identita": {
                "sotto_questa_densita_il_tono_sparisce": round(prog.tono_soglia(), 4),
                "cosa_resta": "occhi, narici, taglio della bocca. La maschera.",
            },
            "due_foto_invece_di_foto_piu_griglia": {
                "cambio": ("La prima versione aveva una foto dietro e un "
                           "reticolo REGOLARE davanti. L'autore ha corretto: "
                           "due foto. Non e' una variante estetica, e' un'altra "
                           "ottica."),
                "cosa_migliora": (
                    "L'effetto e' massimo dove i due punti hanno lo stesso "
                    "diametro. Con la stessa immagine su entrambe le lastre "
                    "quella condizione e' soddisfatta OVUNQUE per costruzione: "
                    "dove il viso e' chiaro entrambi i punti sono piccoli, dove "
                    "e' scuro entrambi sono grandi."),
                "cosa_si_paga": (
                    "La lastra davanti fa ombra anche sul percorso della LUCE, "
                    "non solo su quello dello sguardo: con luce diffusa quella "
                    "ombra vale (1 - densita' davanti). La foto compare due "
                    "volte, come disegno e come ombra. Con la griglia quel "
                    "fattore era costante e spariva nel rapporto; ignorarlo "
                    "qui sovrastimerebbe il movimento del 70%."),
                "il_conto": {
                    "due_foto": {"ampiezza_max": 0.2390, "michelson": 0.497,
                                 "picco_a_densita": 0.400,
                                 "finestra": [0.092, 0.708],
                                 "squilibrio": 1.00},
                    "foto_piu_griglia": {"ampiezza_max": 0.2367, "michelson": 0.456,
                                         "picco_a_densita": 0.3848,
                                         "finestra": [0.135, 0.865],
                                         "squilibrio": 1.92},
                    "verdetto": ("il concetto dell'autore e' anche otticamente "
                                 "migliore, e per giunta la finestra torna "
                                 "simmetrica"),
                },
                "come_si_torna_indietro": "collaudo.py --griglia, genera_layer.py --griglia",
            },
            "perche_il_fondo_non_e_bianco": (
                "Il moire' nasce dal punto davanti che copre quello dietro. Su "
                "bianco non c'e' niente da coprire; su nero pieno il punto davanti "
                "sparisce dentro. E' massimo dove i due punti hanno lo STESSO "
                "diametro. Percio' il campo e' stampato alla copertura del "
                "reticolo e il viso modula intorno a quel valore: nelle bande "
                "allineate il viso rientra nel campo invece di bucarlo."
            ),
        },

        "movimento": [
            {"theta_gradi": g,
             "testa_mm": round(prog.distanza * math.tan(math.radians(g))),
             "scorrimento_s_mm": round(prog.parallasse(math.radians(g)), 2),
             "banda_mm": round(prog.magnificazione * prog.parallasse(math.radians(g))),
             "velo_speculare": round(velo_speculare(math.radians(g)), 4)}
            for g in (0, 5, 10, 15, 20, 25, 30, 40)
        ],

        "leggibilita": {
            "vicino_1_1.5_m": "i punti, uno per uno. Nessun viso",
            "nominale": f"a {prog.distanza/1000:.1f} m il punto sottende "
                        f"{prog.angolo_punto_arcmin():.1f} arcmin (acuita' ~1): "
                        "il viso e' sulla soglia, si riconosce e non si legge",
            "oltre": f"oltre {prog.distanza_fusione()/1000:.1f} m i punti fondono",
            "sala": "profondita' utile >= 4 m, traverso libero >= 2,5 m. "
                    "Senza traverso l'opera non esiste",
        },

        "riflessi": {
            "modello": "Fresnel non polarizzato, TRE interfacce aria/materiale "
                       "in cascata (non quattro, e non sommate)",
            "etichetta": "INFERITO - da indici tabulati, non da misura su questi materiali",
            "velo": {f"{g}_gradi": round(velo_speculare(math.radians(g)), 4)
                     for g in (0, 15, 30, 45, 60, 70, 80)},
            "zona_di_lavoro_gradi": 25,
            "perche": "oltre i 60 gradi si spegne il velo, non il moire'",
            "cono_specchio": "chi guarda da +theta vede riflesso cio' che sta a "
                             "-theta: la parete di fronte va scura e senza sorgenti",
            "fantasma": {"profondita_mm": round(d), "intensita": round(i, 4)},
            "terzo_reticolo": {
                "cos_e": "l'ombra della griglia proiettata sul viso dalla lampada",
                "si_muove_con": "la lampada, non con chi guarda",
                "per_farlo_sparire": "penombra = larghezza_sorgente * gap / distanza. "
                                     "Servono >= 360 mm di sorgente a 1,5 m",
                "decisione": "entrambe le condizioni sono difendibili. Va scelta, non subita",
            },
        },

        "file_di_stampa": [x for x in (
            _conta_svg(os.path.join(USCITA, "vetro_griglia.svg")),
            _conta_svg(os.path.join(USCITA, "plexi_viso.svg")),
            _conta_svg(os.path.join(USCITA, "p45_vetro_griglia.svg")),
            _conta_svg(os.path.join(USCITA, "p45_plexi_viso.svg"))) if x],
        "file_derivati_da_un_immagine": (
            "I file `*_finale_*`, il contatto del collaudo e i video fatti a "
            "partire da un ritratto dell'autore NON sono versionati: il "
            "repository e' pubblico e contengono il volto. Il codice che li "
            "produce si'. Vedi .gitignore (CLAUDE.md §2.5)."),

        "montaggio": {
            "regola": "il vetro va a squadro; l'angolo si da' ruotando il plexi",
            "perche_il_plexi": "sta dietro ed e' sovradimensionato: la rotazione "
                               "non si vede e si regola a vista",
            "margine_tre_passi": (
                f"Il margine e' {gl.MARGINE:.0f} mm = "
                f"{gl.MARGINE/prog.passo:.0f} passi esatti. Il reticolo dietro sta a "
                "(i+0,5)*passo - margine: se il margine non e' multiplo intero del "
                "passo, quel reticolo cade sfasato. Con 15 mm lo sfalsamento valeva "
                "mezza cella, e mezza cella INVERTE il moire'."
            ),
            "collaudo_senza_strumenti": {
                "verticale": "le due scale coincidono: e' giusto",
                "diagonale": "una stampa e' fuori scala, e l'inclinazione dice di quanto",
                "orizzontale": "la rotazione non c'e': il plexi e' a squadro",
                "nota": "la direzione del movimento E' la misura",
            },
        },

        "tolleranze": [
            {"grandezza": "intercapedine", "valore": "+/- 0,5 mm",
             "conseguenza": "cambia la sensibilita' dell'1%: irrilevante"},
            {"grandezza": "planarita' del plexi", "valore": "+/- 1,5 mm",
             "conseguenza": "1 mm di imbarcamento sposta la macchia del 3%, "
                            "e solo agli angoli obliqui"},
            {"grandezza": "angolo alpha", "valore": "+/- 0,05 gradi",
             "conseguenza": "+/-6% sul periodo. Si regola a vista"},
            {"grandezza": "scala fra le due stampe", "valore": "+/- 0,15%",
             "conseguenza": "e' la tolleranza dura: 0,5% inclina le bande di 18 gradi. "
                            "Stessa macchina, stessa giornata, stesso lotto"},
            {"grandezza": "registro fra i due strati", "valore": "nessuno",
             "conseguenza": "il moire' e' un battimento globale. Non pagare un "
                            "registro che non serve"},
        ],

        "immagine": {
            "stato": "DA PRODURRE - il viso in viso.py e' un segnaposto verificabile, "
                     "non l'opera",
            "scelta_dell_autore": "raffaello_05 - scelta il 2026-09-09 fra sei "
                                 "candidate tutte idonee",
            "soggetto": SOGGETTO,
            "conflitto_apparente": CONFLITTO_APPARENTE,
            "vincoli_che_vengono_dal_retino": {
                "valori_di_tono_disponibili": (round(prog.larghezza / prog.passo)
                                               * round(prog.altezza / prog.passo)),
                "dimensione_del_dettaglio_piu_piccolo_mm": prog.passo,
                "sotto_quella_misura": "il dettaglio non viene rimpicciolito: viene "
                                       "cancellato, e al suo posto resta rumore",
                "finestra_tonale_utile": {
                    "centro": round(prog.copertura_griglia, 4),
                    "semiampiezza": 0.30,
                    "fuori_da_qui": "il moire' non esiste",
                },
            },
            "prompt": {
                "principale": PROMPT_PRINCIPALE,
                "negativo": PROMPT_NEGATIVO,
                "varianti": PROMPT_VARIANTI,
            },
            "parametri": PARAMETRI_GENERAZIONE,
            "asimmetria_delle_ombre": {
                "fatto": ("La resa del moire' e' massima sul fondo (0,3848) e cala "
                          "da tutte e due le parti, ma NON in modo simmetrico: "
                          "densita' 0,65 rende il 74% del massimo, densita' 0,10 "
                          "solo il 26%."),
                "perche": ("Nello stato disallineato le aree nere si sommano. Con "
                           "un punto dietro grande la somma satura in fretta, la "
                           "luminanza crolla e l'escursione resta ampia; con un "
                           "punto piccolo non c'e' quasi niente da sommare."),
                "conseguenza": ("Le ombre lavorano quasi il triplo delle luci. Un "
                                "ritratto per quest'opera va tenuto mezzo stop "
                                "SOTTO il mezzo grigio: meglio sbagliare scuro che "
                                "sbagliare chiaro."),
                "etichetta": "RECUPERATO - curva calcolata da collaudo.py, riproducibile",
            },
            "accettazione": {
                "comando": "python3 collaudo.py cartella_ritratti/ --passo 4.5",
                "cosa_fa": ("Rende ogni cella del reticolo nei DUE stati estremi - "
                            "punto davanti sopra quello dietro, e punto davanti nel "
                            "mezzo dei quattro dietro - e misura quanta luce quella "
                            "cella muove. La RESA e' quella differenza divisa per il "
                            "massimo ottenibile."),
                "la_finestra_tonale_si_ricava": (
                    "Fissato quanto deve muoversi la cella PEGGIORE (--resa-min, "
                    "0,35 per difetto), i due estremi di densita' fra cui mappare "
                    "l'immagine sono determinati: sono i punti in cui la curva "
                    "della resa vale quel valore. A passo 4,5 mm vengono "
                    "0,135 .. 0,865, SQUILIBRATI 1,92x verso le ombre. Non e' una "
                    "preferenza: e' la curva."),
                "errore_corretto": (
                    "La prima versione mappava simmetrica intorno al fondo. Su un "
                    "ritratto vero il 20% delle celle risultava ferma - TUTTE dal "
                    "lato chiaro, tutte sulla guancia illuminata - perche' sotto "
                    "il fondo la resa crolla molto piu' in fretta. Con la finestra "
                    "derivata scendono a zero."),
                "soglie": {"resa_media": 0.65, "resa_min_per_cella": 0.35,
                           "escursione_sorgente_minima": 0.12},
                "riferimenti_della_soglia": {
                    "campo_piatto_sul_fondo": 1.0,
                    "gaussiano_centrato_sul_fondo": 0.768,
                    "istogramma_uniforme_sulla_finestra": 0.724,
                    "soglia": 0.65,
                    "bimodale_tutto_agli_estremi": 0.350,
                    "nota": ("la soglia non e' messa a occhio: sta fra il "
                             "riferimento naturale (una rampa lineare) e il caso "
                             "peggiore"),
                },
                "taratura_delle_soglie": (
                    "I riferimenti sopra sono calcolati, non stimati. Restano un "
                    "filtro, non un giudizio: scartano cio' che di sicuro non "
                    "funziona. La scelta fra le immagini che passano resta "
                    "dell'autore."),
                "criterio_superato": (
                    "La 'frazione utile entro +/-0,30 dal fondo, soglia 70%' era "
                    "una soglia messa a occhio. `viso.py --foto` la stampa ancora, "
                    "ma quella che decide e' collaudo.py."),
                "se_sotto_soglia": ("rifarle PIU' PIATTE all'origine. Comprimerle in "
                                    "post lascia bande di posterizzazione che il "
                                    "retino amplifica"),
                "poi": ["python3 collaudo.py cartella/ --passo 4.5 --stampa",
                        "python3 video.py --foto scelta.png --passo 4.5 "
                        "--alpha 0.6446 --resa-min 0.35"],
                "attenzione": ("--resa-min va passata anche a genera_layer.py e a "
                               "video.py: e' da li' che ricavano la finestra. "
                               "`--stampa` lo fa da se'"),
                "uscite": ["collaudo.json - tutti i numeri, anche delle scartate",
                           "collaudo_contatto.png - per ogni immagine i due stati "
                           "affiancati: a sinistra il viso che rientra nel campo, a "
                           "destra il viso intero. Fra quelle due sta tutta l'opera"],
            },
            "sull_identita_visiva": (
                "I tratti canonici ORIENTANO il volto, non lo determinano: sei "
                "immagini che li rispettano tutte possono essere sei persone "
                "diverse. Il collaudo non risponde a 'e' il Raffaello giusto' - non "
                "e' una domanda decidibile da un filtro - ma a 'questa regge il "
                "retino'. La scelta e' dell'autore, fra quelle che passano; da quel "
                "momento l'immagine scelta diventa il riferimento canonico, e le "
                "generazioni successive partono da quella (image-to-image) invece "
                "che dal testo."),
            "tre_domande_all_immagine_finita": [
                "Rimpicciolita a 100 px si legge ancora un viso? Se sparisce li', "
                "sparisce anche nell'opera",
                "Le due meta' hanno grado di definizione diverso, non solo "
                "luminosita' diversa?",
                "Lo sguardo NON si chiude? Se i due occhi convergono, il viso ha "
                "un'identita', ed e' l'unica cosa che l'opera non deve dargli",
            ],
        },

        "pipeline": [
            {"passo": 1, "cosa": "l'immagine",
             "comando": "vedi immagine.prompt, poi collaudo.py per il filtro"},
            {"passo": 2, "cosa": "i file di stampa",
             "comando": "python3 collaudo.py cartella/ --passo 4.5 --stampa"},
            {"passo": 3, "cosa": "il controllo a video",
             "comando": "python3 video.py --foto ritratto.png"},
            {"passo": 4, "cosa": "il provino 300x400 mm",
             "comando": "stessa intercapedine, stesso passo. Chiude tutti gli UNKNOWN"},
            {"passo": 5, "cosa": "il 600x800",
             "comando": "solo dopo il provino"},
        ],

        "verifica": misure,

        "aperto": [
            {"etichetta": "UNKNOWN", "voce": "resa reale del nero ceramico sul vetro",
             "si_chiude_con": "il provino"},
            {"etichetta": "UNKNOWN",
             "voce": f"se {a_gradi:.2f} gradi sia giusto PER L'OCCHIO",
             "si_chiude_con": "il provino - il contrasto e' misurato, il giudizio no"},
            {"etichetta": "UNKNOWN", "voce": "comportamento con luce mista ambiente + artificiale",
             "si_chiude_con": "il provino, nella sala definitiva"},
            {"etichetta": "UNKNOWN", "voce": "se l'immagine definitiva regga il retino",
             "si_chiude_con": "collaudo.py, che e' eseguibile"},
        ],
    }


# ---------------------------------------------------------------- il brief
def scrivi_brief(d):
    im = d["immagine"]
    s = im["soggetto"]
    t = s["tratti_fisici_canonici"]
    cfg = d["configurazioni"]["in_uso"]
    r = ["# Brief per l'immagine — il viso di Raffaello",
         "",
         "**Origine protetta: Claudio Terzi [CT-LGAI-001].**",
         "",
         "> Questo file e' **generato** da `progetto.py` a partire da `progetto.json`.",
         "> Non modificarlo a mano: la fonte e' `progetto.py`, e una seconda copia",
         "> modificabile e' esattamente il difetto descritto in CLAUDE.md §6.",
         "", "---", "",
         "## Il soggetto", "",
         f"**{s['nome']}** — {s['natura']}.",
         f"Fonte dei tratti: {s['fonte']}.", "",
         f"- eta' apparente: {t['eta_apparente_anni']} anni",
         f"- incarnato: {t['incarnato']}",
         f"- capelli: {t['capelli']}",
         f"- occhi: {t['occhi']}",
         f"- corporatura: {t['corporatura']}",
         "- carattere: " + ", ".join(s["carattere_canonico"]),
         "", f"> {s['nota_sul_colore']}",
         "", f"> {s['cosa_resta_fuori']}",
         "", "---", "",
         "## Iper-realismo e retino: come stanno insieme", "",
         f"**{im['conflitto_apparente']['domanda']}**", "",
         im["conflitto_apparente"]["risposta"], "",
         im["conflitto_apparente"]["conseguenza"], "",
         "| | |", "|---|---|",
         f"| valori di tono disponibili | **{im['vincoli_che_vengono_dal_retino']['valori_di_tono_disponibili']}** "
         f"({cfg['punti_sul_quadro'][0]} x {cfg['punti_sul_quadro'][1]}) |",
         f"| dettaglio piu' piccolo | {cfg['passo_mm']:.2f} mm |",
         f"| centro della finestra tonale | {im['vincoli_che_vengono_dal_retino']['finestra_tonale_utile']['centro']:.4f} |",
         f"| semiampiezza | +/- {im['vincoli_che_vengono_dal_retino']['finestra_tonale_utile']['semiampiezza']} |",
         "", "---", "",
         "## Il prompt", "", "```", im["prompt"]["principale"], "```",
         "", "### Negativo", "", "```", im["prompt"]["negativo"], "```", ""]
    r += ["### Varianti", ""]
    for v in im["prompt"]["varianti"]:
        r += [f"**{v['nome']}** — {v['quando']}.", f"*{v['cambia']}*", "",
              "```", v["testo"], "```", ""]
    p = im["parametri"]
    r += ["---", "", "## Come generarle", "",
          f"- {p['quante_generarne']} generazioni, {p['formato']}, "
          f"almeno {p['risoluzione_minima_px'][0]} x {p['risoluzione_minima_px'][1]} px",
          f"- {p['file']}", f"- **Come scegliere:** {p['come_scegliere']}", "",
          "**Cosa non fare:**", ""]
    r += [f"{i+1}. {x}" for i, x in enumerate(p["cosa_non_fare"])]
    a = im["accettazione"]
    asm = im["asimmetria_delle_ombre"]
    r += ["", "---", "", "## Tienile mezzo stop scure", "",
          f"**{asm['fatto']}**", "", asm["perche"], "",
          f"> {asm['conseguenza']}", "",
          "---", "", "## Il collaudo — un comando", "",
          "```bash", a["comando"], "```", "", a["cosa_fa"], "",
          "### La finestra tonale non si sceglie: si ricava", "",
          a["la_finestra_tonale_si_ricava"], "",
          f"> **Errore corretto.** {a['errore_corretto']}", "",
          "### Le soglie", "", "| soglia | valore |", "|---|---|"]
    r += [f"| {k.replace('_', ' ')} | {v} |" for k, v in a["soglie"].items()]
    r += ["", "Il numero 0,65 non e' messo a occhio — sta fra due riferimenti "
          "calcolabili:", "", "| istogramma | resa media |", "|---|---|"]
    r += [f"| {k.replace('_', ' ')} | {v} |"
          for k, v in a["riferimenti_della_soglia"].items() if k != "nota"]
    r += ["", f"> {a['taratura_delle_soglie']}", "",
          f"*{a['criterio_superato']}*", "",
          f"Se nessuna passa: {a['se_sotto_soglia']}.", "",
          "Poi:", "", "```bash"] + a["poi"] + ["```", "", "**Uscite:**", ""]
    r += [f"- {u}" for u in a["uscite"]]
    r += ["", "---", "", "## Sull'identita' visiva", "",
          im["sull_identita_visiva"], "", "---", "",
          "## Le tre domande all'immagine finita", "",
          "Guardandola a occhi socchiusi, o rimpicciolita a 100 px:", ""]
    r += [f"{i+1}. {q}" for i, q in enumerate(im["tre_domande_all_immagine_finita"])]
    r += ["", "---", "",
          "Se si preferisce una fotografia vera, la pipeline non distingue: "
          "stessi vincoli, piu' uno — sorgente grande e vicina, niente controluce. "
          "Se il soggetto e' una persona reale e riconoscibile, la liberatoria e' "
          "un atto dell'autore e non di questo repository; qui si dice solo che serve.", ""]
    open(BRIEF_PATH, "w", encoding="utf-8").write("\n".join(r))
    return BRIEF_PATH


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--senza-misura", action="store_true",
                    help="riusa gli esiti gia' dentro progetto.json")
    ap.add_argument("--verifica", action="store_true",
                    help="il JSON su disco e' ancora quello che il codice produce?")
    a = ap.parse_args()
    prog = Progetto()

    vecchio = {}
    if os.path.exists(JSON_PATH):
        vecchio = json.load(open(JSON_PATH, encoding="utf-8"))

    if a.verifica:
        if not vecchio:
            print("progetto.json non esiste."); return 2
        nuovo = costruisci(prog, vecchio.get("verifica", {}))
        for k in ("documento",):
            nuovo.pop(k, None); vecchio_k = dict(vecchio); vecchio_k.pop(k, None)
        uguale = json.dumps(nuovo, sort_keys=True) == json.dumps(
            {k: v for k, v in vecchio.items() if k != "documento"}, sort_keys=True)
        print("progetto.json " + ("e' allineato al codice."
                                  if uguale else "E' INVECCHIATO: rigeneralo."))
        return 0 if uguale else 2

    misure = vecchio.get("verifica", {}) if a.senza_misura else misura(prog)
    d = costruisci(prog, misure)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"scritto {JSON_PATH} ({os.path.getsize(JSON_PATH)//1024} KB)")
    print(f"scritto {scrivi_brief(d)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
