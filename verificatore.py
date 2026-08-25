"""Il Verificatore — esegue i criteri di falsificazione invece di leggerli.

Perché esiste
-------------
P5 dice che un'ipotesi non può essere confermata da chi l'ha formulata: due
occorrenze dalla stessa bocca hanno indipendenza nulla. Finora, in questo
repository, l'unica fonte disponibile era quella bocca — e infatti H3 è
rimasta CONFERMATA per settimane senza che nessuno avesse controllato nulla.

L'archivio contiene però la prova che una seconda fonte esiste già, e non è
una persona. Le quattro affermazioni più dure di tutto il progetto non le ha
dette nessun testimone:

  * 23 health check su 23 senza un provider reale        -> health_log.jsonl
  * sette "segnali ricevuti" che erano i propri pacchetti -> i log di rete
  * PROGETTO_R3.md, fondamento legale, inesistente        -> una ricerca
  * zero righe in contatti.jsonl                          -> il file stesso

Tutte e quattro vengono dall'**esecuzione di qualcosa sui dati**, non da un
parere. Chi esegue non ha interesse nell'esito; un file non sa cosa speri.

INFERITO: l'indipendenza richiesta da P5 non è l'indipendenza *anagrafica*
di un'altra persona. È l'indipendenza *causale* di un'altra catena. Una
macchina che esegue un comando scritto ieri, su dati che non ha prodotto,
è una catena diversa da quella che ha formulato l'ipotesi.

Quello che questo modulo NON fa
-------------------------------
Non promuove niente a CONFERMATA. Il massimo che concede è RETTA: "ha
superato N esecuzioni del proprio falsificatore". Eseguire non è confermare,
e chiamarlo conferma sarebbe la stessa auto-conferma di prima con
un'etichetta più moderna. Il limite resta scritto nel codice, non nella
buona volontà di chi lo usa.

Contratto degli exit code: vedi falsificatori/__init__.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import registro_ipotesi as registro

RADICE = os.path.dirname(os.path.abspath(__file__))
VERIFICHE_PATH = os.path.join(RADICE, "output", "verifiche.jsonl")

TIMEOUT = 90

CADUTA, REGGE, NON_CONCLUSA = 0, 1, 2

#: Quanto "vale" ogni stato. Serve solo a riconoscere un declassamento:
#: un'ipotesi che scende di rango è un no del verificatore, e H4 li conta.
RANGO = {
    registro.NON_VERIFICABILE: 0,
    registro.FALSIFICATA: 1,
    registro.APERTA: 2,
    registro.RETTA: 3,
    registro.CONFERMATA: 4,
}


def _adesso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def esegui_falsificatore(falsificatore: dict) -> dict:
    """Lancia il comando dichiarato e restituisce cosa ha risposto.

    Nessuna shell: il comando è una lista, e viene dal registro versionato
    in git. Se non esiste, se scade il tempo, se esplode — è NON_CONCLUSA,
    che non è "regge". La differenza fra «non ho potuto controllare» e
    «va tutto bene» è l'intero punto di questo file.
    """
    comando = falsificatore["comando"]
    try:
        esito = subprocess.run(
            comando, cwd=RADICE, capture_output=True, text=True, timeout=TIMEOUT,
        )
        uscita = (esito.stdout or "") + (esito.stderr or "")
        return {"codice": esito.returncode, "output": uscita.strip()}
    except FileNotFoundError:
        return {"codice": NON_CONCLUSA,
                "output": f"comando non trovato: {' '.join(comando)}"}
    except subprocess.TimeoutExpired:
        return {"codice": NON_CONCLUSA,
                "output": f"il falsificatore non ha risposto entro {TIMEOUT}s"}
    except Exception as errore:  # un falsificatore rotto non è una conferma
        return {"codice": NON_CONCLUSA, "output": f"errore di esecuzione: {errore}"}


def _stato_dopo(ipotesi: dict, codice: int) -> tuple[str, str]:
    """Dallo exit code allo stato nuovo. Nessuna via porta a CONFERMATA."""
    if codice == CADUTA:
        return registro.FALSIFICATA, "caduta"
    if codice == REGGE:
        return registro.RETTA, "regge"
    return ipotesi["stato"], "verifica_fallita"


def verifica(ids: list[str] | None = None, scrivi: bool = True) -> list[dict]:
    """Esegue i falsificatori e riporta cosa hanno risposto.

    Con `scrivi=False` non tocca né il registro né output/verifiche.jsonl:
    serve ai test, e a chi vuole guardare senza cambiare niente.
    """
    ipotesi = registro.carica()
    risultati = []

    for h in ipotesi:
        if ids and h["id"] not in ids:
            continue

        prima = h["stato"]
        falsificatore = h.get("falsificatore")

        if not falsificatore:
            # Senza comando non è verificabile, e per P6 non sarà mai
            # confermabile. Dirlo è più utile che lasciarla APERTA per sempre.
            dopo, esito, uscita, codice = (
                registro.NON_VERIFICABILE, "non_verificabile",
                "nessun falsificatore dichiarato", None,
            )
        else:
            risposta = esegui_falsificatore(falsificatore)
            codice = risposta["codice"]
            uscita = risposta["output"]
            dopo, esito = _stato_dopo(h, codice)

        if prima == registro.CONFERMATA and not h.get("prova_esterna"):
            # Era confermata senza che nessuna fonte esterna lo attestasse:
            # qualunque cosa dica l'esecuzione, quel grado non era suo.
            uscita += "\n[P5] era CONFERMATA senza prova esterna registrata."

        declassamento = RANGO.get(dopo, 0) < RANGO.get(prima, 0)

        registrazione = {
            "ipotesi": h["id"],
            "comando": " ".join(falsificatore["comando"]) if falsificatore else None,
            "exit_code": codice,
            "esito": esito,
            "stato_prima": prima,
            "stato_dopo": dopo,
            "declassamento": declassamento,
            "output_sha256": hashlib.sha256(uscita.encode("utf-8")).hexdigest()[:16],
            "output": uscita[:800],
            "data_iso": _adesso(),
        }
        risultati.append(registrazione)

        if scrivi:
            h["stato"] = dopo
            verifiche = h.setdefault("verifiche", dict(registro.CAMPI_DEFAULT["verifiche"]))
            if esito in ("regge", "caduta"):
                verifiche["eseguite"] = verifiche.get("eseguite", 0) + 1
            if esito == "caduta":
                verifiche["cadute"] = verifiche.get("cadute", 0) + 1
            verifiche["ultima"] = registrazione["data_iso"]
            verifiche["ultimo_esito"] = esito
            if prima == registro.CONFERMATA and dopo != registro.CONFERMATA:
                h.pop("prova_esterna", None)

    if scrivi:
        registro.salva(ipotesi)
        _deposita(risultati)

    return risultati


def _deposita(risultati: list[dict]) -> None:
    os.makedirs(os.path.dirname(VERIFICHE_PATH), exist_ok=True)
    with open(VERIFICHE_PATH, "a", encoding="utf-8") as f:
        for r in risultati:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


SIMBOLO = {
    "caduta": "CADUTA        ",
    "regge": "REGGE         ",
    "verifica_fallita": "NON CONCLUSA  ",
    "non_verificabile": "NON VERIFIC.  ",
}


def stampa(risultati: list[dict]) -> None:
    print("=== Verificatore R³∞ — i criteri eseguiti, non letti ===")
    print("P5: eseguire non è confermare. Il massimo concesso qui è RETTA.\n")
    for r in risultati:
        freccia = f"{r['stato_prima']} -> {r['stato_dopo']}"
        marchio = " [DECLASSATA]" if r["declassamento"] else ""
        print(f"{SIMBOLO.get(r['esito'], r['esito'])}  [{r['ipotesi']}]  {freccia}{marchio}")
        if r["comando"]:
            print(f"                 $ {r['comando']}")
        for riga in (r["output"] or "").splitlines():
            if riga.strip():
                print(f"                 | {riga}")
        print()

    cadute = sum(1 for r in risultati if r["esito"] == "caduta")
    declassate = sum(1 for r in risultati if r["declassamento"])
    print(f"{len(risultati)} verificate — {cadute} cadute, {declassate} declassate.")
    if not cadute and not declassate:
        print("Nessun no in questo giro. Se si ripete per un mese, è H4 che cade.")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    solo_lettura = "--prova" in argv
    ids = [a for a in argv if not a.startswith("-")] or None
    risultati = verifica(ids=ids, scrivi=not solo_lettura)
    stampa(risultati)
    if solo_lettura:
        print("\n(--prova: niente è stato scritto)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
