#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dove siamo, in questo secondo, detto con la precisione che abbiamo davvero.

Solo matematica della libreria standard, nessuna effemeride esterna. Ogni
funzione dichiara la propria precisione: un numero senza il suo errore non e'
una misura, e' una cifra.

Quello che si puo' dire davvero della "posizione nell'universo":

  1. Dove sta la Terra rispetto al Sole.  Calcolabile qui, a circa 0,01 gradi
     e 1e-4 UA, con le formule a bassa precisione dell'Astronomical Almanac.
  2. Dove sta il Sole nella Galassia.  NON e' calcolabile da qui: e' una
     costante misurata da altri (R0 = 8,122 +/- 0,031 kpc, GRAVITY 2018).
     La riportiamo come costante altrui, non come nostro risultato.
  3. Come ci muoviamo rispetto al fondo cosmico a microonde.  Questo e' il
     punto piu' vicino a un "sistema di riferimento assoluto" che la fisica
     conosca: il CMB ha un dipolo, e da quel dipolo si misura la nostra
     velocita' propria — 369,82 +/- 0,11 km/s verso (l, b) = (264,021;
     48,253) in coordinate galattiche (Planck 2018).

Il punto 3 e' la risposta seria alla domanda "dove siamo, davvero": non un
punto in una mappa, ma una direzione e una velocita' rispetto alla luce piu'
antica che esista. Ed e' calcolabile per il tuo balcone, adesso.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import math

# --- costanti misurate da altri, riportate con la loro incertezza ---
CMB_V_KMS = 369.82            # +/- 0.11 km/s   (Planck 2018)
CMB_V_ERR = 0.11
CMB_APICE_L = 264.021         # gradi, coordinate galattiche
CMB_APICE_B = 48.253
R0_KPC = 8.122                # +/- 0.031 kpc   (GRAVITY Collaboration 2018)
R0_ERR = 0.031
V_CIRC_KMS = 229.0            # +/- 7 km/s, velocita' circolare del Sole
UA_KM = 149597870.7
GM_SOLE = 1.32712440018e20    # m^3/s^2

# matrice galattico -> equatoriale ICRS (Hipparcos, ESA SP-1200 vol.1 sez.1.5.3)
_A_G = (
    (-0.0548755604, +0.4941094279, -0.8676661490),
    (-0.8734370902, -0.4448296300, -0.1980763734),
    (-0.4838350155, +0.7469822445, +0.4559837762),
)


def giorno_giuliano(t_unix: float) -> float:
    """JD da tempo unix. Usiamo UTC al posto di UT1: l'errore e' < 0,9 s,
    cioe' < 0,004 gradi di rotazione terrestre. Irrilevante qui, ma va detto."""
    return t_unix / 86400.0 + 2440587.5


def _secoli(jd: float) -> float:
    return (jd - 2451545.0) / 36525.0


def sole(jd: float) -> dict:
    """Longitudine eclittica vera e distanza del Sole.
    Precisione ~0,01 gradi in longitudine, ~1e-4 UA in distanza."""
    t = _secoli(jd)
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t
    mr = math.radians(m % 360.0)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(mr)
         + (0.019993 - 0.000101 * t) * math.sin(2 * mr)
         + 0.000289 * math.sin(3 * mr))
    lon_vera = (l0 + c) % 360.0
    v = math.radians((m + c) % 360.0)
    r = 1.000001018 * (1 - e * e) / (1 + e * math.cos(v))
    return {"longitudine_deg": lon_vera, "distanza_ua": r,
            "anomalia_media_deg": m % 360.0, "eccentricita": e}


def terra_eliocentrica(jd: float) -> dict:
    """Posizione della Terra vista dal Sole: e' quella del Sole vista dalla
    Terra, ruotata di 180 gradi. La latitudine eclittica della Terra e' zero
    per definizione del piano dell'eclittica."""
    s = sole(jd)
    lon = (s["longitudine_deg"] + 180.0) % 360.0
    r = s["distanza_ua"]
    lr = math.radians(lon)
    return {"longitudine_eclittica_deg": lon, "latitudine_eclittica_deg": 0.0,
            "distanza_ua": r, "distanza_km": r * UA_KM,
            "x_ua": r * math.cos(lr), "y_ua": r * math.sin(lr), "z_ua": 0.0}


def velocita_orbitale_kms(r_ua: float) -> float:
    """Velocita' della Terra sull'orbita, dalla vis-viva. Semiasse a = 1 UA."""
    r_m = r_ua * UA_KM * 1000.0
    a_m = UA_KM * 1000.0
    return math.sqrt(GM_SOLE * (2.0 / r_m - 1.0 / a_m)) / 1000.0


def galattico_a_equatoriale(l_deg: float, b_deg: float) -> tuple:
    """(l, b) galattiche -> (AR, Dec) ICRS, in gradi."""
    l, b = math.radians(l_deg), math.radians(b_deg)
    v = (math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b))
    # le COLONNE di _A_G sono gli assi galattici espressi in ICRS: la
    # colonna 2 e' il polo nord galattico. Quindi _A_G porta galattico -> ICRS.
    x, y, z = (sum(_A_G[i][j] * v[j] for j in range(3)) for i in range(3))
    ar = math.degrees(math.atan2(y, x)) % 360.0
    dec = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    return ar, dec


def tsg_deg(jd: float) -> float:
    """Tempo siderale medio di Greenwich, in gradi."""
    t = _secoli(jd)
    g = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
         + 0.000387933 * t * t - t * t * t / 38710000.0)
    return g % 360.0


def alt_az(ar_deg: float, dec_deg: float, lat_deg: float, lon_deg: float,
           jd: float) -> dict:
    """Altezza e azimut (dal Nord, verso Est) di un punto fisso del cielo,
    per un osservatore a lat/lon. Senza rifrazione: sotto i 5 gradi di altezza
    l'atmosfera sposta l'immagine e questo numero non e' piu' quello che vedi."""
    ha = math.radians((tsg_deg(jd) + lon_deg - ar_deg) % 360.0)
    dec, lat = math.radians(dec_deg), math.radians(lat_deg)
    sin_alt = math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(ha)
    alt = math.asin(max(-1.0, min(1.0, sin_alt)))
    den = math.cos(alt) * math.cos(lat)
    if abs(den) < 1e-12:
        az = 0.0
    else:
        cos_a = (math.sin(dec) - math.sin(alt) * math.sin(lat)) / den
        az = math.degrees(math.acos(max(-1.0, min(1.0, cos_a))))
        if math.sin(ha) > 0:
            az = 360.0 - az
    return {"altezza_deg": math.degrees(alt), "azimut_deg": az,
            "sopra_orizzonte": alt > 0}


def dove_siamo(t_unix: float, lat_deg: float = None, lon_deg: float = None) -> dict:
    """Il blocco completo: dove sta la Terra, quanto corriamo, e in che
    direzione — con l'incertezza accanto a ogni numero che non e' nostro."""
    jd = giorno_giuliano(t_unix)
    terra = terra_eliocentrica(jd)
    v_orb = velocita_orbitale_kms(terra["distanza_ua"])
    ar, dec = galattico_a_equatoriale(CMB_APICE_L, CMB_APICE_B)

    fuori = {
        "t_unix": t_unix,
        "giorno_giuliano": jd,
        "nota_tempo": "JD da UTC; lo scarto UT1-UTC (< 0,9 s) non e' applicato",
        "terra_eliocentrica": terra,
        "velocita_orbitale_kms": v_orb,
        "apice_cmb": {
            "galattiche_lb_deg": [CMB_APICE_L, CMB_APICE_B],
            "equatoriali_ardec_deg": [ar, dec],
            "velocita_kms": CMB_V_KMS,
            "errore_kms": CMB_V_ERR,
            "fonte": "Planck 2018; costante misurata da altri, non calcolata qui",
        },
        "sole_nella_galassia": {
            "distanza_centro_kpc": R0_KPC, "errore_kpc": R0_ERR,
            "velocita_circolare_kms": V_CIRC_KMS,
            "fonte": "GRAVITY Collaboration 2018; costante misurata da altri",
            "nota": "questa non e' calcolata dal programma: e' riportata",
        },
        "precisione": {
            "longitudine_solare_deg": 0.01,
            "distanza_terra_sole_ua": 1e-4,
            "posizione_galattica": "NON calcolata: solo costanti riportate",
        },
    }
    if lat_deg is not None and lon_deg is not None:
        fuori["osservatore"] = {"lat_deg": lat_deg, "lon_deg": lon_deg}
        fuori["apice_cmb"]["visto_da_qui"] = alt_az(ar, dec, lat_deg, lon_deg, jd)
    return fuori


def strada_fatta_km(dt_s: float) -> dict:
    """Quanta strada abbiamo fatto rispetto al fondo cosmico in dt secondi.
    E' l'unico 'spostamento assoluto' che la fisica sappia misurare."""
    return {"secondi": dt_s, "km": CMB_V_KMS * dt_s,
            "km_errore": CMB_V_ERR * dt_s,
            "riferimento": "fondo cosmico a microonde (CMB)"}
