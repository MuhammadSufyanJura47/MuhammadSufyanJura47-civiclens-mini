"""
Offline smoke tests for CivicLens Mini.

These test the deterministic, network-free logic:
  * AI output validation + malformed-JSON repair/handling
  * duplicate detection (lexical fallback path)
  * JSON-file storage round-trip
  * report rendering + disclaimers

Run:  python test_core.py
Exit code 0 = all passed.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import ai_client
import duplicates
import report as report_mod
import storage

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


print("== AI output validation ==")
# Well-formed but out-of-range values get coerced to safe defaults.
raw = {
    "category": "Teleportation",  # invalid -> Other
    "summary": "x" * 10,
    "reported_duration": "null",  # -> None
    "location": "not provided",   # -> None
    "evidence_mentioned": "a photo",  # str -> list
    "suggested_priority": "super-urgent",  # invalid -> Medium
    "priority_reasons": None,  # -> []
}
v = ai_client.validate_analysis(raw)
check("invalid category -> Other", v["category"] == "Other")
check("invalid priority -> Medium", v["suggested_priority"] == "Medium")
check("'null' duration -> None", v["reported_duration"] is None)
check("'not provided' location -> None", v["location"] is None)
check("string evidence -> list", v["evidence_mentioned"] == ["a photo"])
check("None reasons -> []", v["priority_reasons"] == [])

print("== Malformed JSON handling ==")
# _extract_json should recover JSON wrapped in prose / code fences.
wrapped = 'Here is the result:\n```json\n{"category":"Electricity","summary":"s"}\n```\nthanks'
try:
    obj = ai_client._extract_json(wrapped)
    check("recovers fenced JSON", obj.get("category") == "Electricity")
except Exception as exc:  # noqa: BLE001
    check("recovers fenced JSON", False, str(exc))

# Totally non-JSON must raise (caller surfaces an honest error, not a guess).
raised = False
try:
    ai_client._extract_json("the model refused and wrote only prose")
except json.JSONDecodeError:
    raised = True
check("non-JSON raises JSONDecodeError", raised)

print("== Duplicate detection (lexical fallback) ==")
# Force lexical path regardless of environment for a deterministic test.
a = "No water supply in G-9 for five days, families affected"
b = "Water supply has been off in G-9 for 5 days, many families affected"
c = "Pothole on the main road near the market"
sim_ab = duplicates._lexical_similarity(a, b)
sim_ac = duplicates._lexical_similarity(a, c)
check("similar texts score high", sim_ab > 0.5, f"score={sim_ab}")
check("dissimilar texts score low", sim_ac < sim_ab, f"ab={sim_ab} ac={sim_ac}")
existing = [{"id": "x1", "text": b, "analysis": {"summary": "water G-9"}}]
dups = duplicates.find_duplicates(a, existing, threshold=0.5)
check("find_duplicates flags the match", len(dups) == 1 and dups[0]["id"] == "x1")

print("== Storage round-trip (isolated temp dir) ==")
# Redirect storage to a temp dir so we never touch real data.
tmpdir = Path(tempfile.mkdtemp())
storage.DATA_DIR = tmpdir
storage.STORE_PATH = tmpdir / "complaints.json"
rec = storage.save_complaint("Test complaint text", v, duplicates=[])
all_items = storage.load_all()
check("saved record persists", len(all_items) == 1 and all_items[0]["id"] == rec["id"])
check("default status is New", all_items[0]["status"] == "New")
ok = storage.update_status(rec["id"], "Resolved")
check("status update works", ok and storage.load_all()[0]["status"] == "Resolved")
s = storage.stats()
check("stats total counts record", s["total"] == 1)
check("delete removes record", storage.delete_complaint(rec["id"]) and storage.load_all() == [])

print("== Report rendering ==")
rec2 = {
    "id": "abc123",
    "created_at": "2026-10-10T07:00:00+00:00",
    "status": "New",
    "is_sample": False,
    "text": "Street light off for a week",
    "analysis": v,
    "duplicates": [],
}
txt = report_mod.build_report(rec2, dup_method="lexical")
check("report includes 'NOT officially verified'", "NOT been officially verified" in txt)
check("report marks priority as AI suggestion", "AI SUGGESTION" in txt)
check("report includes a next step", "RECOMMENDED NEXT STEP" in txt)

print()
print(f"RESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
