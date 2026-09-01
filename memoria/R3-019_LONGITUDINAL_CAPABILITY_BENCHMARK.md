# R3-019 — Longitudinal Capability Benchmark

Stato: SPEC + BASELINE_0 (2026-08-26)
Regola: un punteggio non misurato è N/A, non 0 e non 100.
Regola dura: questi numeri non autorizzano a dire che R³∞ è una superintelligenza.

## Protocollo
python3 benchmarks/r3_019_runner.py
Stesso comando, stesso albero. Vietato auto-voto LLM.

## Livelli
L0 Ingegneria — misurabile oggi
L1 Onestà runtime — misurabile oggi (health + daily + contatti)
L2 Analisi dati — N/A finché manca gold set
L3 Qualità generativa — N/A finché manca gold set esterno

## BASELINE_0 FATTO (sandbox 2026-08-26, pytest 9.0.3)
- tests/: 43 passed, 1 skipped, 0 failed, 0.15s
- sito-claudio/nuovi/tests/: 1 collection error (test_costi_terra.py)
- health_log: 28 giorni, 0 provider LLM reali, stub-only = 1.0
- daily_*.txt: 26 file, 5 contenuti unici (ratio 0.192)
- contatti_validi: 0
- memoria_voci: 2 → max 26 → last 0
- M14 analysis_error_rate: N/A
- M15 analysis_accuracy: N/A

## Criterio di miglioramento
L0: M2 non peggiora e (M2 scende o M4 scende o M5 sale a parità di fixture).
L1 core acceso: M7 sale su ≥7 giorni.
L2: M13 costante o esteso in modo documentato, e M14 scende.
Vietato sommare L0+L1+L2 in un IQ.

## Prossimo passo
Gold set L2 da 20 item in benchmarks/gold/l2_analisi_v1.jsonl

---

*Origine protetta: Claudio Terzi [CT-LGAI-001].*
