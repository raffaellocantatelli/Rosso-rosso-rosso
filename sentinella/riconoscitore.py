# -*- coding: utf-8 -*-
"""Il riconoscitore: da righe di feed a segnalazioni ordinate.

**Non e' un previsore, ed e' importante che nessuno lo scambi per tale.**
Non calcola orbite, non anticipa terremoti, non indovina brillamenti. Prende
cio' che agenzie pubbliche hanno gia' pubblicato e fa tre cose che quelle
pubblicazioni, sparse su quattro siti diversi, non fanno da sole:

  1. le mette sulla stessa mappa e sulla stessa scala di gravita';
  2. dichiara **quale regola** ha fatto scattare ogni segnalazione, con i
     numeri dentro, cosi' che la si possa contestare invece di crederci;
  3. dichiara **cosa la smentirebbe** — perche' un allarme che non puo'
     essere smentito non e' un allarme, e' una profezia.

Le soglie qui sotto sono scelte, non leggi di natura. Sono scritte in chiaro
perche' chi le trova sbagliate possa cambiarle, non perche' siano giuste.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

INFORMATIVO, ATTENZIONE, ALLERTA = "informativo", "attenzione", "allerta"

AVVISO_DI_FONDO = (
    "Sentinella non prevede: ordina cio' che USGS, NASA/JPL e NOAA hanno gia' "
    "pubblicato. Ogni segnalazione porta la regola che l'ha fatta scattare e "
    "la condizione che la smentirebbe. Per decidere davvero, si va alla fonte."
)

RAGGIO_TERRA_KM = 6371.0
ORBITA_GEOSTAZIONARIA_KM = 42164.0
UA_KM = 149_597_870.7
LD_AU = 0.002569555


def _fascia(punteggio):
    if punteggio >= 70:
        return ALLERTA
    if punteggio >= 40:
        return ATTENZIONE
    return INFORMATIVO


def _limita(x, minimo=0.0, massimo=100.0):
    return max(minimo, min(massimo, x))


def diametro_da_magnitudine(h, albedo=0.14):
    """Diametro in metri stimato dalla magnitudine assoluta H.

    Relazione standard D[km] = 1329 / sqrt(albedo) * 10^(-H/5). L'albedo di un
    oggetto non osservato in infrarosso **non si conosce**: di qui l'intervallo
    0.05-0.25 restituito accanto alla stima centrale. Un numero solo, qui,
    sarebbe una finta precisione.
    """
    if h is None:
        return None
    return 1329.0 / math.sqrt(albedo) * (10 ** (-h / 5.0)) * 1000.0


def _sigma_in_ore(campo):
    """`t_sigma_f` CNEOS: '00:09' = 9 minuti, '9_15:50' = 9 giorni 15 h 50 m."""
    if not campo or not isinstance(campo, str):
        return None
    giorni = 0.0
    resto = campo
    if "_" in campo:
        g, resto = campo.split("_", 1)
        try:
            giorni = float(g)
        except ValueError:
            giorni = 0.0
    pezzi = resto.split(":")
    try:
        ore = float(pezzi[0]) if pezzi else 0.0
        minuti = float(pezzi[1]) if len(pezzi) > 1 else 0.0
    except ValueError:
        return None
    return giorni * 24 + ore + minuti / 60.0


def _quando(testo):
    for formato in ("%Y-%b-%d %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(testo, formato).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _segnalazione(**kw):
    """Il tetto e' la parte importante.

    Un punteggio puo' salire per quanto un fenomeno e' grande o vicino, ma il
    livello dice **cosa fare**, e per la maggior parte di questi fenomeni la
    risposta e' «niente». Un asteroide che manca la Terra di 400.000 km resta
    notevole e non e' un'allerta; e dove un'agenzia ha gia' espresso una
    valutazione propria (il livello PAGER di USGS), quella vince sulla nostra.
    """
    kw.setdefault("dove", None)
    kw.setdefault("tempo", "futuro")
    tetto = kw.pop("tetto", 100)
    grezzo = kw["punteggio"]
    punteggio = min(grezzo, tetto)
    kw["livello"] = _fascia(punteggio)
    kw["punteggio"] = round(punteggio)
    # Il punteggio prima del tetto non si butta: serve a ordinare dentro il tetto.
    # Sei sismi tutti a 45 per lo stesso PAGER verde non sono equivalenti, e un
    # pareggio risolto dall'ordine alfabetico della localita' sarebbe un caso.
    kw["punteggio_grezzo"] = round(grezzo, 1)
    if tetto < 100:
        kw["tetto_applicato"] = tetto
    return kw


# ── 1. passaggi ravvicinati ────────────────────────────────────────────────

def da_passaggi(inv):
    """Un oggetto che passa vicino non e' un oggetto che colpisce.

    La regola guarda tre cose separate: quanto e' grande, quanto passa vicino,
    e quanto e' conosciuta l'orbita. La terza e' quella che di solito manca nei
    titoli di giornale, ed e' la sola che dice se le prime due sono affidabili.
    """
    fuori = []
    for o in inv.get("items") or []:
        ld = o.get("dist_ld")
        if ld is None:
            continue
        d_centrale = diametro_da_magnitudine(o.get("h"))
        d_min = diametro_da_magnitudine(o.get("h"), albedo=0.25)
        d_max = diametro_da_magnitudine(o.get("h"), albedo=0.05)

        # La taglia pesa in proporzione a quanto l'oggetto passa vicino: un corpo
        # di 4 km a dodici distanze lunari e' una curiosita' astronomica, non un
        # fenomeno che riguardi chi guarda questa mappa.
        vicinanza = 60.0 * _limita(1 - math.log10(max(ld, 0.05) / 0.1) / math.log10(200), 0, 1)
        taglia = 40.0 * _limita(math.log10(max(d_centrale or 1.0, 1.0) / 5.0) / math.log10(200), 0, 1)
        peso_taglia = _limita(1 - math.log10(max(ld, 0.05)) / math.log10(20), 0.12, 1.0)
        punteggio = vicinanza + taglia * peso_taglia
        # Un oggetto che passa e va oltre non e' un'allerta, per quanto grande sia:
        # sale sopra "attenzione" solo se l'arco attuale lo porta dentro le orbite usate.
        tetto = 69

        perche = [
            f"passa a {ld:g} distanze lunari ({o['dist_km']:,} km) — soglia di attenzione: 5 LD".replace(",", "."),
            f"diametro stimato {d_centrale:.0f} m da H={o['h']:g} (intervallo {d_min:.0f}–{d_max:.0f} m secondo l'albedo)"
            if d_centrale else "diametro non stimabile: manca la magnitudine assoluta H",
        ]

        dist_min_km = (o.get("dist_min_au") or 0) * UA_KM
        if dist_min_km and dist_min_km < ORBITA_GEOSTAZIONARIA_KM:
            punteggio = max(punteggio, 62)
            tetto = 100
            perche.append(
                f"il minimo dell'arco attuale ({dist_min_km:,.0f} km) scende dentro la fascia "
                f"geostazionaria ({ORBITA_GEOSTAZIONARIA_KM:,.0f} km): riguarda i satelliti".replace(",", ".")
            )
        if dist_min_km and dist_min_km < RAGGIO_TERRA_KM:
            punteggio = 100
            tetto = 100
            perche.append("il minimo dell'arco attuale e' sotto il raggio terrestre: traiettoria d'intersezione")

        sigma = _sigma_in_ore(o.get("sigma_tempo"))
        larghezza = None
        if o.get("dist_min_au") and o.get("dist_max_au") and o["dist_min_au"] > 0:
            larghezza = o["dist_max_au"] / o["dist_min_au"]
        if (sigma is not None and sigma > 24) or (larghezza and larghezza > 3):
            confidenza = "bassa"
            perche.append(
                f"orbita poco vincolata: incertezza sull'istante {o.get('sigma_tempo')}, "
                f"la distanza minima e la massima differiscono di {larghezza:.0f} volte"
                if larghezza else f"orbita poco vincolata: incertezza sull'istante {o.get('sigma_tempo')}"
            )
        elif sigma is not None and sigma > 1:
            confidenza = "media"
        else:
            confidenza = "alta"

        fuori.append(_segnalazione(
            id=f"cad:{o['designazione']}:{o['quando_utc']}",
            tipo="passaggio",
            titolo=f"{o['designazione']} a {ld:g} LD",
            quando=o["quando_utc"],
            punteggio=punteggio,
            tetto=tetto,
            riconosciuto_da=perche,
            confidenza=confidenza,
            smentito_se=(
                "nuove osservazioni accorciano l'incertezza e la distanza minima risale: "
                "la stessa API, rifatta domani, restituisce dist_min piu' grande"
            ),
            effetti=(
                "nessun effetto al suolo per un passaggio a questa distanza; sotto la fascia "
                "geostazionaria conterebbe per i satelliti"
            ) if ld > 0.11 else "passaggio molto ravvicinato: rilevante per gli operatori satellitari",
            fonte=inv["source"],
            dati={"dist_ld": ld, "dist_km": o["dist_km"], "diametro_m": round(d_centrale) if d_centrale else None,
                  "h": o.get("h"), "v_rel_kms": o.get("v_rel_kms")},
        ))
    return fuori


# ── 2. bolidi gia' avvenuti ────────────────────────────────────────────────

def da_bolidi(inv):
    """Cio' che e' gia' caduto. Non anticipa niente: dice con che frequenza accade."""
    fuori = []
    for b in inv.get("items") or []:
        kt = b.get("energia_kt")
        if kt is None:
            continue
        punteggio = _limita(20 + 22 * math.log10(max(kt, 0.05) / 0.05), 0, 95)
        perche = [f"energia d'impatto stimata {kt:g} kt di TNT (Chelyabinsk 2013: ~440 kt)"]
        if b.get("quota_km"):
            perche.append(f"disintegrazione a {b['quota_km']:g} km di quota")
        if b.get("velocita_kms"):
            perche.append(f"velocita' d'ingresso {b['velocita_kms']:g} km/s")
        fuori.append(_segnalazione(
            id=f"fb:{b['quando_utc']}",
            tipo="bolide",
            titolo=f"Bolide da {kt:g} kt",
            quando=b["quando_utc"],
            tempo="passato",
            dove={"lat": b["lat"], "lon": b["lon"]},
            punteggio=punteggio,
            riconosciuto_da=perche,
            confidenza="alta",
            smentito_se="CNEOS rivede l'energia stimata dell'evento, o lo ritira dall'elenco",
            effetti="evento gia' concluso: sopra ~1 kt l'onda d'urto puo' essere avvertita al suolo",
            fonte=inv["source"],
            dati={"energia_kt": kt, "quota_km": b.get("quota_km"), "velocita_kms": b.get("velocita_kms")},
        ))
    return fuori


# ── 3. meteo spaziale ──────────────────────────────────────────────────────

REGOLE_METEO = [
    (re.compile(r"Geomagnetic K-index of (\d+)", re.I), "geomagnetico"),
    (re.compile(r"X-?ray Event exceeded ([MX]\d+(?:\.\d+)?)", re.I), "brillamento"),
    (re.compile(r"Proton Event.*?exceeded (\d+)\s*pfu", re.I | re.S), "protoni"),
    (re.compile(r"Electron 2MeV Integral Flux exceeded ([\d,]+)\s*pfu", re.I), "elettroni"),
    (re.compile(r"10cm Radio Burst.*?(\d+)\s*sfu", re.I | re.S), "radio"),
]

SCALA_G = {5: "G1 (minore)", 6: "G2 (moderata)", 7: "G3 (forte)", 8: "G4 (grave)", 9: "G5 (estrema)"}

EFFETTI = {
    "geomagnetico": "correnti indotte sulle reti elettriche alle alte latitudini, deriva "
                    "dei satelliti in orbita bassa, aurore a latitudini insolite",
    "brillamento": "assorbimento delle onde corte sul lato illuminato della Terra, disturbi "
                   "alla navigazione satellitare",
    "protoni": "rischio radiologico per gli equipaggi sulle rotte polari e per l'elettronica in orbita",
    "elettroni": "accumulo di carica sui satelliti geostazionari: guasti differiti, non immediati",
    "radio": "interferenza sulle bande radio e sui segnali GNSS",
}


def da_meteo_spaziale(inv):
    fuori = []
    for m in inv.get("items") or []:
        testo = m.get("messaggio") or ""
        genere, valore, punteggio = None, None, 0.0
        for espressione, nome in REGOLE_METEO:
            trovato = espressione.search(testo)
            if not trovato:
                continue
            genere, valore = nome, trovato.group(1)
            if nome == "geomagnetico":
                k = int(valore)
                punteggio = 30 + 9 * (k - 4)
            elif nome == "brillamento":
                classe = valore[0].upper()
                numero = float(valore[1:] or 1)
                punteggio = (58 + 12 * math.log10(max(numero, 1))) if classe == "X" else 42
            elif nome == "protoni":
                punteggio = 58
            elif nome == "elettroni":
                punteggio = 38
            else:
                punteggio = 32
            break
        if genere is None:
            continue
        prima_riga = next((r.strip() for r in testo.splitlines()
                           if r.strip() and "Message Code" not in r and "Serial Number" not in r
                           and not r.startswith("Issue Time")), "Avviso NOAA SWPC")
        perche = [f"NOAA SWPC ha emesso {m.get('product_id')}: {prima_riga}"]
        if genere == "geomagnetico":
            perche.append(f"K-index {valore} → tempesta {SCALA_G.get(int(valore), 'sotto scala')}")
        fuori.append(_segnalazione(
            id=f"swpc:{m.get('product_id')}:{m.get('emesso_utc')}",
            tipo="meteo_spaziale",
            sottotipo=genere,
            titolo=prima_riga[:88],
            quando=m.get("emesso_utc"),
            tempo="in_corso",
            punteggio=punteggio,
            riconosciuto_da=perche,
            confidenza="alta",
            smentito_se="il bollettino successivo di NOAA SWPC annulla o declassa l'avviso",
            effetti=EFFETTI.get(genere, ""),
            fonte=inv["source"],
            dati={"genere": genere, "valore": valore},
        ))
    return fuori


def da_geomagnetismo(inv):
    """Lo stato del campo geomagnetico adesso, e fin dove scende l'ovale aurorale."""
    serie = inv.get("items") or []
    if not serie:
        return [], None
    ultimo = serie[-1]
    kp_ora = ultimo["kp"]
    kp_max = max(v["kp"] for v in serie[-8:]) if len(serie) >= 8 else kp_ora
    # Confine aurorale approssimato: una retta empirica, non un modello.
    confine = 67.5 - 2.5 * kp_ora
    stato = {"kp": kp_ora, "kp_max_24h": kp_max, "quando_utc": ultimo["quando_utc"],
             "confine_aurorale_lat": round(confine, 1),
             "nota": "confine aurorale da retta empirica 67.5 - 2.5*Kp: indicativo, non un modello"}
    if kp_max < 5:
        return [], stato
    return [_segnalazione(
        id=f"kp:{ultimo['quando_utc']}",
        tipo="geomagnetismo",
        titolo=f"Kp {kp_max:g} nelle ultime 24 h",
        quando=ultimo["quando_utc"],
        tempo="in_corso",
        punteggio=30 + 9 * (kp_max - 4),
        riconosciuto_da=[f"indice Kp planetario a {kp_max:g}: soglia di tempesta {SCALA_G.get(int(kp_max), '')}",
                         f"aurore possibili fino a {confine:.0f}° di latitudine"],
        confidenza="media",
        smentito_se="la misura definitiva di GFZ Potsdam corregge il Kp stimato di NOAA verso il basso",
        effetti=EFFETTI["geomagnetico"],
        fonte=inv["source"],
        dati=stato,
    )], stato


# ── 4. sismi ───────────────────────────────────────────────────────────────

PAGER = {"green": 45, "yellow": 62, "orange": 80, "red": 95}


def da_sismi(inv, soglia=4.5):
    fuori = []
    for s in inv.get("items") or []:
        mag = s.get("mag")
        if mag is None or mag < soglia:
            continue
        punteggio = _limita(12 * mag - 20)
        perche = [f"magnitudo {mag:g} — soglia di segnalazione {soglia:g}"]
        if s.get("depth_km") is not None:
            perche.append(f"profondita' {s['depth_km']:g} km"
                          + (" (superficiale: scuote di piu' a parita' di magnitudo)" if s["depth_km"] < 70 else ""))
        tetto = 100
        if s.get("tsunami"):
            punteggio += 10
            perche.append(
                "flag tsunami alzato da USGS: significa che l'evento e' in una zona per cui i centri "
                "d'allerta emettono messaggi, non che uno tsunami sia atteso"
            )
        if s.get("alert") in PAGER:
            # PAGER e' la stima di impatto di USGS. Dove c'e', comanda: la nostra
            # formula puo' aggiungere sfumature, non contraddire chi ha i modelli.
            punteggio = max(punteggio, PAGER[s["alert"]])
            tetto = PAGER[s["alert"]]
            perche.append(f"livello PAGER {s['alert']} dichiarato da USGS: e' la loro valutazione d'impatto, "
                          f"e su questa mappa ha l'ultima parola")
        fuori.append(_segnalazione(
            id=f"eq:{s.get('id')}",
            tipo="sisma",
            titolo=f"M{mag:g} — {s.get('place') or 'localita non dichiarata'}",
            quando=datetime.fromtimestamp(s["time"] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")
            if s.get("time") else None,
            tempo="passato",
            dove={"lat": s.get("lat"), "lon": s.get("lon")},
            punteggio=punteggio,
            tetto=tetto,
            riconosciuto_da=perche,
            confidenza="alta",
            smentito_se="USGS rivede la magnitudo nelle ore successive: la revisione e' la norma, non l'eccezione",
            effetti="evento gia' avvenuto; il flag tsunami, quando c'e', riguarda le ore seguenti",
            fonte=inv["source"],
            dati={"mag": mag, "depth_km": s.get("depth_km"), "url": s.get("url"), "pager": s.get("alert")},
        ))
    return fuori


# ── il quadro ──────────────────────────────────────────────────────────────

def quadro(inviluppi):
    """Mette insieme tutto e ordina. L'ordine e' il punteggio, non la spettacolarita'."""
    segnalazioni = []
    degradate = []
    for chiave, inv in inviluppi.items():
        if inv.get("status") != "ok":
            degradate.append({"sorgente": chiave, "status": inv.get("status"), "motivo": inv.get("error")})
            continue
        if inv.get("raffreddata"):
            degradate.append({"sorgente": chiave, "status": "raffreddata",
                              "motivo": inv.get("error"), "eta_secondi": inv.get("eta_secondi")})

    stato_geo = None
    if inviluppi.get("passaggi", {}).get("status") == "ok":
        segnalazioni += da_passaggi(inviluppi["passaggi"])
    if inviluppi.get("bolidi", {}).get("status") == "ok":
        segnalazioni += da_bolidi(inviluppi["bolidi"])
    if inviluppi.get("meteo_spaziale", {}).get("status") == "ok":
        segnalazioni += da_meteo_spaziale(inviluppi["meteo_spaziale"])
    if inviluppi.get("geomagnetismo", {}).get("status") == "ok":
        nuove, stato_geo = da_geomagnetismo(inviluppi["geomagnetismo"])
        segnalazioni += nuove
    if inviluppi.get("sismi", {}).get("status") == "ok":
        segnalazioni += da_sismi(inviluppi["sismi"])

    # Ordinare per solo punteggio metteva un bolide di sei mesi fa sopra un sisma
    # di ieri. Il punteggio dice **quanto e' grave**, e non va toccato; l'ordine
    # deve dire **quanto riguarda adesso**. Sono due cose diverse, quindi due campi
    # diversi: la gravita' resta, l'eta' pesa solo su cio' che e' gia' avvenuto.
    adesso = datetime.now(timezone.utc)
    for s in segnalazioni:
        s["ordine"] = float(s["punteggio"])
        if s["tempo"] != "passato":
            continue
        quando = _quando(s.get("quando"))
        if not quando:
            continue
        giorni = max((adesso - quando).total_seconds() / 86400.0, 0.0)
        s["giorni_fa"] = round(giorni, 1)
        s["ordine"] = round(s["punteggio"] * max(math.exp(-giorni / 30.0), 0.05), 2)
    segnalazioni.sort(key=lambda s: (-s["ordine"], -s["punteggio_grezzo"], str(s.get("quando") or "")))

    attive = [s for s in segnalazioni if s["tempo"] != "passato"]
    conteggi = {liv: sum(1 for s in segnalazioni if s["livello"] == liv)
                for liv in (ALLERTA, ATTENZIONE, INFORMATIVO)}
    if any(s["livello"] == ALLERTA for s in attive):
        sintesi = ALLERTA
    elif any(s["livello"] == ATTENZIONE for s in attive):
        sintesi = ATTENZIONE
    else:
        sintesi = INFORMATIVO

    # Il punto in cui una dashboard mente piu' facilmente: se una sorgente e'
    # caduta, "nessuna allerta" e' una frase che non abbiamo il diritto di dire.
    completo = not degradate
    return {
        "generato": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sintesi": sintesi if completo else None,
        "quadro_completo": completo,
        "sorgenti_degradate": degradate,
        "conteggi": conteggi,
        "geomagnetismo": stato_geo,
        "segnalazioni": segnalazioni,
        "non_e_una_previsione": AVVISO_DI_FONDO,
    }
