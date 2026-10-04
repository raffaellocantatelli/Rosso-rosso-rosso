# R³ EXPORT GATE — artefatto Claude

I byte esatti della patch sono in `export/letta_continuity_record.patch`: l'hash si verifica su quel file, non sul blocco qui sotto.

NODE_ID                  claude-code-session_01GiEdri2RDpZFDQoDkYmxoB
SESSION_DATE             2026-10-04T09:55:00Z
ARTIFACT_TYPE            PATCH
CLAIMED_BASE_SHA         81dce982dfbd1d4b5f646b1418efbc24c8be4bf0
LOCAL_HEAD_SHA           81dce982dfbd1d4b5f646b1418efbc24c8be4bf0 (checkout di sola lettura; si applica anche su f848f19, che non tocca app.py)
BRANCH                   NOT_AVAILABLE (nessun push: accesso in sola lettura a claudioterzi/claudio)
CHANGED_FILES            raffaello_crypto_scout/app.py
DIFF_STAT                1 file changed, 33 insertions(+)
PATCH_SHA256             c024bb0788b9f322985f24b7e0300d2b863c76443b25338bcde826e604a70906
PATCH_BYTES              2067
REPRODUCIBILITY          Python 3.11.15, solo libreria standard per il test (le funzioni vengono estratte via ast, senza importare httpx)
TEST_COMMANDS            git apply --check letta_continuity_record.patch
                         test inline: _letta_continuity_record (VERIFIED / NOT_VERIFIED), _append_receipt_ledger (senza variabile → no-op; con variabile → 2 righe appese)
TEST_OUTPUT_RAW          "4 controlli ok" / "patch si applica pulita"
PASS/FAIL/SKIP           PASS 4 · FAIL 0 · SKIP: integrazione con Letta reale (nessun bridge vivo raggiungibile)
SANDBOX_BACKEND          mock (dati finti, nessuna chiamata di rete)
DESIGN_ONLY_DECLARATION  record provider-neutral: IMPLEMENTED · ledger append-only: IMPLEMENTED (opt-in) · scrittura reale su Letta: NON ESEGUITA
KNOWN_ISSUES             1. La scrittura sul ledger non è atomica fra processi concorrenti (append semplice).
                         2. authority è fissa a CANONICAL-CANDIDATE: il valore segue il documento del 04/10, non lo schema EPISODIC|SEMANTIC|CANONICAL del 28/09. Va scelto uno dei due.
                         3. Railway: il progetto r3-typesafe-sister ha 0 servizi (osservato il 04/10), quindi il bridge non è verificabile.

## Risposte alle richieste del gate per Claude

- Correzioni PostgreSQL, PG 16, i 5 failure: NOT_AVAILABLE. Questa sessione non ha
  lavorato su PostgreSQL. Se un'altra sessione Claude l'ha fatto, l'artefatto va
  chiesto a quella: non lo posso esportare né confermare da qui.
- Commit 81dce982…: NON È MIO. RECUPERATO dai metadati git: autore
  «Claudio» (indirizzo email omesso: è nei metadati git del commit), 2026-10-04 11:48:15 +0200. Questa
  sessione l'ha soltanto letto.

## CLAIM_RETRACTIONS

Nessuna.

## PATCH

```diff
diff --git a/raffaello_crypto_scout/app.py b/raffaello_crypto_scout/app.py
index e7046bf..f5a9669 100644
--- a/raffaello_crypto_scout/app.py
+++ b/raffaello_crypto_scout/app.py
@@ -314,6 +314,37 @@ def _sha256_text(value):
     return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
 
 
+def _letta_continuity_record(receipt):
+    """Provider-neutral record for a Letta write (docs/R3_LETTA_PROVIDER_NEUTRAL_CONTINUITY.md).
+
+    Letta holds a provider copy; this record is what R3 owns. A Letta write never
+    self-promotes: promotion_status stays NON_CANONICAL until an explicit R3 gate.
+    """
+    return {
+        "continuity_id": os.getenv("R3_CONTINUITY_ID", "RAFFAELLO"),
+        "memory_id": receipt.get("label"),
+        "authority": "CANONICAL-CANDIDATE",
+        "content_sha256": receipt.get("expected_sha256"),
+        "provenance": [f"letta_canon_write:{receipt.get('ts')}"],
+        "provider_bindings": {"letta": {
+            "agent_id": receipt.get("agent_id"),
+            "block_ids": [receipt["block_id"]] if receipt.get("block_id") else [],
+            "read_after_write": receipt.get("status") == "VERIFIED",
+        }},
+        "promotion_status": "NON_CANONICAL",
+    }
+
+
+def _append_receipt_ledger(entry):
+    """Append-only JSONL ledger; no-op unless R3_RECEIPT_LEDGER_PATH is set."""
+    path = os.getenv("R3_RECEIPT_LEDGER_PATH", "").strip()
+    if not path:
+        return False
+    with open(path, "a", encoding="utf-8") as f:
+        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
+    return True
+
+
 def classify_letta_answer(answer, canary):
     text = (answer or "").strip()
     if text == canary:
@@ -472,6 +503,8 @@ def run_letta_canon_write():
         and receipt["listed_on_agent"]
     )
     receipt["status"] = "VERIFIED" if receipt["match"] else "NOT_VERIFIED"
+    receipt["continuity_record"] = _letta_continuity_record(receipt)
+    receipt["ledger_appended"] = _append_receipt_ledger(receipt)
     return receipt
 
 def diagnose_arm(binding, answer_class):
```
