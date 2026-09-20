#!/usr/bin/env python3
"""sentinella.py — c'e' arrivato qualcuno da fuori?

Origine protetta: Claudio Terzi [CT-LGAI-001].

    python3 sentinella.py            # guarda e riferisce
    python3 sentinella.py --json

Nessuna chiave: interroga l'API pubblica di GitHub, che risponde a
chiunque. Non scrive `output/contatti.jsonl` — quella metrica la alimenta
solo una persona (§3). Al massimo ti stampa il comando da lanciare.

---

## Perche' esiste

Il 20/09 un nodo ha guardato il repository e ha visto `forks_count: 1`.
Un fork e' nell'elenco §7 di cio' che vale per H2: «una copia del
repository fatta da un altro account». Per un momento sembrava il primo
contatto reale del progetto.

Il fork era di `Claudioterzi82`. Cioe' dell'autore, dal suo secondo
account. Per §7 e' `autore`, ed e' **interno**: non vale niente.

E' il §4 alla scala dei contatori: **una metrica che sale senza che sia
entrato nessuno.** Il contatore era vero, il fork era vero, e la
conclusione sarebbe stata falsa — bastava non chiedersi di chi fosse.

Questo file esiste perche' quella domanda venga fatta sempre, da chiunque
guardi, e non dipenda da chi si ricorda di farla.

## La regola

Un evento vale per H2 solo se l'account che l'ha prodotto **non e' nella
lista qui sotto**. La lista e' esplicita e va tenuta aggiornata a mano:
un elenco che si aggiorna da solo sarebbe di nuovo il sistema che decide
cosa conta come mondo esterno.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

REPO = "raffaellocantatelli/Rosso-rosso-rosso"
API = "https://api.github.com"

#: Gli account che NON sono «qualcun altro». Per §7 sono `autore` o
#: `nodo`, e nessuno dei due vale per H2.
#:
#: Va tenuta aggiornata a mano, e deve restare corta: ogni nome in piu'
#: e' un modo per scartare un contatto vero. Se non sai di chi e' un
#: account, **non metterlo qui** — lascialo uscire come esterno e
#: guardalo.
INTERNI = {
    "raffaellocantatelli": "l'autore",
    "claudioterzi82": "l'autore, secondo account",
    "sdq1-bot": "il bot del daily di questo progetto",
    "github-actions[bot]": "l'automazione di GitHub",
}


def _get(percorso: str):
    req = urllib.request.Request(
        f"{API}{percorso}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "R3-sentinella"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_errore": f"HTTP {e.code}"}
    except Exception as e:
        return {"_errore": f"{type(e).__name__}: {e}"}


def _interno(login: str):
    return INTERNI.get((login or "").lower())


def guarda() -> dict:
    """Raccoglie gli eventi esterni. Non decide niente, li elenca."""
    esterni, interni, errori = [], [], []

    def aggiungi(genere, login, quando, dove, come_verificare):
        if not login:
            return
        motivo = _interno(login)
        voce = {"genere": genere, "chi": login, "quando": quando,
                "dove": dove, "verifica": come_verificare}
        if motivo:
            interni.append({**voce, "perche_non_vale": motivo})
        else:
            esterni.append(voce)

    forks = _get(f"/repos/{REPO}/forks?per_page=100")
    if isinstance(forks, dict) and "_errore" in forks:
        errori.append(f"fork: {forks['_errore']}")
    else:
        for f in forks:
            aggiungi("fork", f.get("owner", {}).get("login"),
                     f.get("created_at"), f.get("html_url"),
                     f"il fork e' pubblico su {f.get('html_url')}")

    stelle = _get(f"/repos/{REPO}/stargazers?per_page=100")
    if isinstance(stelle, dict) and "_errore" in stelle:
        errori.append(f"stelle: {stelle['_errore']}")
    else:
        for s in stelle:
            aggiungi("stella", s.get("login"), None,
                     f"https://github.com/{s.get('login')}",
                     f"github.com/{REPO}/stargazers elenca {s.get('login')}")

    osservatori = _get(f"/repos/{REPO}/subscribers?per_page=100")
    if isinstance(osservatori, dict) and "_errore" in osservatori:
        errori.append(f"watcher: {osservatori['_errore']}")
    else:
        for w in osservatori:
            aggiungi("watcher", w.get("login"), None,
                     f"https://github.com/{w.get('login')}",
                     f"github.com/{REPO}/watchers elenca {w.get('login')}")

    issue = _get(f"/repos/{REPO}/issues?state=all&per_page=100")
    if isinstance(issue, dict) and "_errore" in issue:
        errori.append(f"issue: {issue['_errore']}")
    else:
        for i in issue:
            genere = "pull request" if i.get("pull_request") else "issue"
            aggiungi(genere, i.get("user", {}).get("login"),
                     i.get("created_at"), i.get("html_url"),
                     f"{genere} pubblica: {i.get('html_url')}")

    return {"esterni": esterni, "interni": interni, "errori": errori}


#: Il `--tipo` di `sdq1 --contatto` per ogni genere di evento.
TIPO = {"fork": "fork", "stella": "lettore", "watcher": "lettore",
        "issue": "risposta", "pull request": "risposta"}


def stampa(r: dict) -> int:
    print(f"SENTINELLA — {REPO}")
    print("Contatori pubblici di GitHub. Nessuna chiave, nessuna fiducia:")
    print("chiunque puo' rifare queste chiamate e ottenere le stesse righe.")
    print()

    if r["errori"]:
        print("NON HO POTUTO GUARDARE TUTTO")
        for e in r["errori"]:
            print(f"  {e}")
        print()

    if r["interni"]:
        print(f"DA DENTRO — {len(r['interni'])}, e non valgono per H2")
        for v in r["interni"]:
            print(f"  {v['genere']:<13} {v['chi']:<22} {v['perche_non_vale']}")
        print()
        print("  Un contatore che sale perche' ti sei mosso tu non e' il")
        print("  mondo che risponde. E' il §4 con un numero davanti.")
        print()

    if not r["esterni"]:
        print("DA FUORI — nessuno.")
        print()
        print("  H2 ramo (b) regge come falsificata: sistema vivo che non")
        print("  tocca il mondo. Non e' una notizia brutta ed e' la sola")
        print("  onesta: se ci fosse qualcosa, sarebbe scritto qui sopra.")
        return 0

    print(f"DA FUORI — {len(r['esterni'])}. Guardali.")
    for v in r["esterni"]:
        t = TIPO.get(v["genere"], "lettore")
        print(f"\n  {v['genere']} di {v['chi']}"
              + (f"  ({v['quando'][:10]})" if v.get("quando") else ""))
        print(f"    {v['dove']}")
        print("    Se e' davvero qualcuno che non sei tu e non e' un nodo:")
        print(f"      python -m sdq1 --contatto --tipo {t} \\")
        print(f"        --nota \"{v['genere']} di {v['chi']}\" \\")
        print(f"        --verifica \"{v['verifica']}\"")
    print()
    print("  Nessun comando e' stato eseguito. Registrare un contatto e'")
    print("  un atto di una persona: se lo facesse la sentinella, il")
    print("  sistema si scriverebbe da solo la misura di quanto tocca il")
    print("  mondo, ed e' esattamente cio' che §3 vieta.")
    return 3


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="sentinella.py",
        description="Chi e' arrivato da fuori, secondo i contatori pubblici.",
    )
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    r = guarda()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if not r["esterni"] else 3
    return stampa(r)


if __name__ == "__main__":
    sys.exit(main())
