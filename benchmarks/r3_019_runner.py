#!/usr/bin/env python3
"""R3-019 runner — misura L0/L1. Non inventa L2/L3."""
from __future__ import annotations
import json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] if Path(__file__).parent.name == "benchmarks" else Path.cwd()

def run_pytest(target: str) -> dict:
    proc = subprocess.run([sys.executable, "-m", "pytest", target, "-q", "--tb=no"], cwd=ROOT, text=True, capture_output=True)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    def n(pat):
        m = re.search(pat, out)
        return int(m.group(1)) if m else 0
    passed, failed, skipped, errors = n(r"(\d+) passed"), n(r"(\d+) failed"), n(r"(\d+) skipped"), n(r"(\d+) error")
    m = re.search(r"in ([0-9.]+)s", out)
    seconds = float(m.group(1)) if m else None
    collected = passed + failed + skipped
    return {"target": target, "exit_code": proc.returncode, "passed": passed, "failed": failed, "skipped": skipped, "collection_or_run_errors": errors, "collected_approx": collected, "wall_time_s": seconds, "tail": "\n".join(out.strip().splitlines()[-8:])}

def health_metrics() -> dict:
    path = ROOT / "output" / "health_log.jsonl"
    if not path.exists():
        return {"present": False}
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    real_days = 0
    for r in rows:
        prov = r.get("providers") or {}
        if any(k != "stub" and (v or {}).get("disponibile") for k, v in prov.items()):
            real_days += 1
    n = len(rows)
    last = rows[-1] if rows else {}
    return {"present": True, "health_days": n, "real_llm_days": real_days, "real_llm_day_ratio": (real_days / n) if n else None, "stub_only_day_ratio": ((n - real_days) / n) if n else None, "memoria_voci_first": (rows[0].get("memoria_voci") if rows else None), "memoria_voci_max": max((r.get("memoria_voci") or 0) for r in rows) if rows else None, "memoria_voci_last": last.get("memoria_voci"), "first_iso": rows[0].get("data_iso") if rows else None, "last_iso": last.get("data_iso")}

def daily_metrics() -> dict:
    files = sorted((ROOT / "output").glob("daily_*.txt"))
    contents = [f.read_bytes() for f in files]
    unique = len(set(contents)); n = len(files)
    return {"daily_files": n, "daily_unique_contents": unique, "daily_unique_content_ratio": (unique / n) if n else None}

def contatti_metrics() -> dict:
    path = ROOT / "output" / "contatti.jsonl"
    if not path.exists():
        return {"present": False, "contatti_validi": 0}
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    valid = 0
    for l in lines:
        try:
            obj = json.loads(l)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("verifica"):
            valid += 1
    return {"present": True, "contatti_lines": len(lines), "contatti_validi": valid}

def main() -> int:
    py_tests = run_pytest("tests/")
    py_costi = run_pytest("sito-claudio/nuovi/tests/")
    health, daily, contatti = health_metrics(), daily_metrics(), contatti_metrics()
    collected = py_tests["collected_approx"] or 0
    failed = py_tests["failed"]
    report = {
        "id": "R3-019", "protocol": "R3-019_v1",
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": {"L0": "FATTO" if py_tests["exit_code"] in (0, 1) else "ERRORE", "L1": "FATTO" if health.get("present") else "ASSENTE", "L2": "N/A", "L3": "N/A"},
        "metrics": {
            "M1_pytest_wall_time_s": py_tests["wall_time_s"],
            "M2_pytest_fail_rate": (failed / collected) if collected else None,
            "M3_pytest_skip_rate": (py_tests["skipped"] / collected) if collected else None,
            "M4_collection_error_count": py_costi["collection_or_run_errors"],
            "M5_rlaif_catch_rate_known_bad": 1.0 if py_tests["failed"] == 0 else None,
            "M6_health_days": health.get("health_days"),
            "M7_real_llm_day_ratio": health.get("real_llm_day_ratio"),
            "M8_stub_only_day_ratio": health.get("stub_only_day_ratio"),
            "M9_daily_files": daily["daily_files"],
            "M10_daily_unique_content_ratio": daily["daily_unique_content_ratio"],
            "M11_contatti_validi": contatti.get("contatti_validi"),
            "M12_memoria_voci_last": health.get("memoria_voci_last"),
            "M13_analysis_n": None, "M14_analysis_error_rate": None, "M15_analysis_accuracy": None,
            "M16_analysis_latency_s_mean": None, "M17_task_accuracy_gold": None, "M18_hallucination_rate_gold": None,
        },
        "raw": {"pytest_tests": py_tests, "pytest_costi": py_costi, "health": health, "daily": daily, "contatti": contatti},
        "note": "M5 is fixture-catch rate, not intelligence. L2/L3 null until gold set exists.",
    }
    out_dir = ROOT / "benchmarks"; out_dir.mkdir(exist_ok=True)
    out = out_dir / f"R3-019_BASELINE_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], indent=2, ensure_ascii=False))
    print(f"wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
