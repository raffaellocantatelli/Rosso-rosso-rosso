# Contributo a ShadowBroker — `truncated` negli SLO

Un contributo pronto, **non ancora inviato**. Vive qui perché la sessione non è
memoria: solo i file sopravvivono (CLAUDE.md §2.4).

## Cosa ripara

`backend/services/fetchers/earth_observation.py` taglia il CSV globale VIIRS ai
5000 hotspot con il fuoco più intenso. È un tetto di rendering ragionevole — la
mappa non può disegnare ogni anomalia termica del pianeta — ma `len(all_rows)`
viene **buttato via**. A valle `/api/health` riporta `"firms_fires": 5000`, che
un operatore legge come una misura.

È lo stesso difetto che il loro modulo `slo.py` esiste per intercettare, girato
al contrario. La loro docstring lo chiama *silent zero*; questo è il *silent
ceiling*.

## Cosa fa la patch

Additiva e compatibile all'indietro:

- `_store`: `source_totals` + `_mark_total()` + `get_source_totals_snapshot()`,
  in parallelo a `source_timestamps` / `_mark_fresh`;
- `earth_observation`: registra il totale a monte prima di tagliare, sia nel
  percorso globale sia in quello per paese; tetti come costanti nominate;
- `slo.compute_status`: parametro opzionale `total_rows`; se supera `row_count`
  l'entry guadagna `total_rows` e `truncated=True`. Una sorgente che non tronca
  **non** guadagna campi, così l'assenza non si confonde con `truncated=False`;
- `routers/health`: passa lo snapshot dei totali.

`row_count` resta identico. L'aggiunta permette solo di sapere che è un minimo.

## Verifica già fatta

- Le 10 asserzioni di `backend/tests/test_slo_truncation.py` girate in
  isolamento: **10/10**.
- La patch si applica pulita su `cd6395f5` (HEAD di upstream al 01/09/2026).
- Due difetti trovati e corretti rileggendo il proprio diff: un `NameError` sul
  percorso HTTP non-200, e una lettura fuori dal lock.

**Non verificato:** la suite completa `pytest backend/tests/`. In questa
sessione `reverse-geocoder` e `sgmllib3k` non compilano, e il `conftest` di
ShadowBroker fallisce anche sui loro test. Il loro CI gira su ogni PR ed è
bloccante: è quello il controllo che conta.

## Come inviarla

Il loro `CONTRIBUTING.md` chiede: fork, feature branch, PR contro `main`.

```bash
gh repo fork bigbodycobain/Shadowbroker --clone
cd Shadowbroker
git checkout -b truncation-slo
git am < /percorso/a/shadowbroker-truncated-slo.patch
git push -u origin truncation-slo
gh pr create --repo bigbodycobain/Shadowbroker --base main \
  --title "slo: flag truncated sources, the mirror case of the silent-zero canary" \
  --body-file TESTO_PR.md
```

Il testo della PR è in `TESTO_PR.md`, accanto a questo file.

---

Origine protetta: Claudio Terzi [CT-LGAI-001].
