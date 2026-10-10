# 🏛️ CivicLens Mini

An open-source **civic complaint intelligence** app. Citizens submit municipal
complaints in plain language; an **open-weight AI model** categorises them,
writes a short summary, extracts the reported duration / location / evidence,
and suggests a priority — **always as a suggestion for a human officer to
review, never as an official decision.**

Built for **Hacktoberfest Islamabad 2026**.

---

## Problem

City complaint desks drown in free-text messages. Triage is slow and
inconsistent: the same pothole gets reported ten times, urgent water outages sit
behind trivial tickets, and officers spend hours reading and sorting instead of
fixing. There is no quick, structured view of what citizens are actually
reporting.

## Solution

CivicLens Mini turns each free-text complaint into a **structured, reviewable
record** in seconds:

- **AI triage** — category, summary, reported duration, location (only if the
  citizen stated it), evidence mentioned, and a **suggested** priority with
  reasons.
- **Duplicate detection** — flags complaints that look like ones already filed,
  so the same issue is not actioned twice.
- **A clean dashboard** — metrics, a submission form, live AI results, and a
  recent-complaints list with editable status.
- **A copyable report** per complaint (complaint + analysis + recommended next
  step) that an officer can paste into their workflow.

Everything is stored in a local JSON file — **no database setup required**.

---

## AI architecture

```
Citizen text
     │
    ▼
  ┌─────────────────────────────┐     Open-weight model (Qwen2.5-7B-Instruct)
│  ai_client.analyze_complaint │ ──► served via OpenRouter HTTPS API
└─────────────────────────────┘     response_format = json_object
     │
     ▼
┌─────────────────────────────┐
│  validate_analysis()         │  closed category + priority sets,
│  + malformed-JSON repair     │  list/None coercion, no invented data
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐     sentence-transformers (all-MiniLM-L6-v2)
│  duplicates.find_duplicates  │ ──► SEMANTIC if installed,
└─────────────────────────────┘     else LEXICAL fallback (clearly labelled)
     │
     ▼
   storage (JSON file)  ──►  dashboard + copyable report
```

**Model:** [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen) — an Apache-2.0
**open-weight 7B-parameter** model, within the challenge's 8B maximum. We call it through the
[OpenRouter](https://openrouter.ai) API so the app needs no local GPU/RAM. Point
`CIVICLENS_MODEL` at another eligible OpenRouter model id if you prefer, but
keep the selected model at or below 8B parameters.

**Why OpenRouter and not a local Ollama install?** This build targets a 2-hour
hackathon on a memory-constrained Windows machine. OpenRouter gives the same
open-weight model with zero local install. The code is a thin HTTPS client
(`ai_client.py`), so swapping in a local Ollama endpoint is a one-function
change.

**Duplicate detection** prefers semantic embeddings
(`sentence-transformers`, Apache-2.0). If that package is not installed, it
falls back to a transparent token-overlap + sequence-ratio matcher. The active
method is shown in the UI so a lexical result is never mistaken for semantic.

### Guardrails (enforced in code + prompt)

- The model is instructed to **never invent a location or evidence** — if the
  citizen did not state it, the field is `null` / empty.
- Priority is labelled **"AI suggestion — requires human review"** everywhere.
- Reports state the complaint is **NOT officially verified**.
- Model output is **validated**: unknown categories/priorities are coerced to
  safe defaults, and non-JSON replies raise an honest error instead of a guess.

---

## Setup

Requires **Python 3.10+** (tested on 3.12, Windows).

```powershell
# 1. From the project folder
cd civiclens-mini

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your OpenRouter key (needed only for live AI analysis)
copy .env.example .env            # Windows
# cp .env.example .env            # macOS / Linux
# then edit .env and paste your key from https://openrouter.ai/keys

# 5. Run
streamlit run app.py
```

The app opens at <http://localhost:8501>.

> **Optional — semantic duplicate detection:** uncomment
> `sentence-transformers` in `requirements.txt` and `pip install -r
> requirements.txt` again. Without it, the app uses the labelled lexical
> fallback.

> **No API key yet?** The dashboard still runs. You can load the **3 sample
> complaints** (pre-written demo analyses) and explore the UI, duplicate
> detection, status workflow and copyable reports. Live submission needs the
> key.

---

## Testing

Offline, network-free unit/smoke tests cover validation, malformed-JSON
handling, duplicate detection, storage round-trip and report rendering:

```powershell
python test_core.py
```

Expected: `RESULT: 19 passed, 0 failed` (exit code 0).

**Manual end-to-end:**
1. `streamlit run app.py`
2. Click **"Load 3 sample complaints (demo data)"** — they appear in *Recent
   complaints* badged **DEMO DATA**.
3. With a key configured, type a complaint and click **"Analyse with AI &
   save"** — a structured AI result and a copyable report appear.
4. Submit a complaint similar to an existing one — a **possible duplicate**
   warning is shown.
5. Change a complaint's **status** and confirm it persists after reload.

---

## Project layout

```
civiclens-mini/
├── app.py            # Streamlit dashboard (UI + wiring)
├── ai_client.py      # OpenRouter / open-weight model client + JSON validation
├── duplicates.py     # semantic (embeddings) with lexical fallback
├── storage.py        # atomic JSON-file store
├── report.py         # copyable report builder
├── samples.py        # 3 demonstration complaints
├── test_core.py      # offline smoke tests
├── requirements.txt
├── .env.example      # template — real .env is git-ignored
├── .gitignore
└── LICENSE           # MIT
```

Complaint data is written to `data/complaints.json` (git-ignored — citizen data
is never committed).

---

## Limitations

- **Not an official system.** All AI output is advisory and must be reviewed by
  a human. Nothing here verifies or adjudicates a complaint.
- **No authentication / multi-user support** — it is a single-desk MVP.
- **JSON-file storage** suits a demo, not production scale or concurrent
  writers.
- **AI quality depends on the model and the input.** The model can still
  mis-categorise; the validation layer only guarantees a *safe shape*, not a
  *correct judgement*.
- **Lexical duplicate fallback** catches wording overlap, not meaning — install
  `sentence-transformers` for semantic matching.
- Priority thresholds and categories are opinionated defaults; tune them for
  your city.

---

## Acknowledgements

- **[Qwen2.5](https://github.com/QwenLM/Qwen2.5)** (Alibaba) — the open-weight
  instruct model, Apache-2.0.
- **[OpenRouter](https://openrouter.ai)** — unified API access to open-weight
  models.
- **[sentence-transformers](https://www.sbert.net/)** /
  `all-MiniLM-L6-v2` — open-source embeddings for semantic duplicate detection.
- **[Streamlit](https://streamlit.io)** — the UI framework.
- Built for **Hacktoberfest Islamabad 2026**. 🎃

---

## License

[MIT](LICENSE). The MIT license is compatible with all dependencies used
(Streamlit — Apache-2.0; sentence-transformers — Apache-2.0) and with Qwen2.5's
Apache-2.0 open-weight license.
