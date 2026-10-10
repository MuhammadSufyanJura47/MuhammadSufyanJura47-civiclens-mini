"""
CivicLens Mini — civic complaint intelligence dashboard.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st
from html import escape

# Load .env (for OPENROUTER_API_KEY) if python-dotenv is installed. Optional.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import ai_client
import duplicates
import report as report_mod
import storage
from samples import SAMPLES

st.set_page_config(page_title="CivicLens Mini", page_icon="🏛️", layout="wide")

# --------------------------- theme (civic newsroom) ---------------------------
INK = "#17232b"
NAVY = "#163c43"
TEAL = "#00665b"
SKY = "#176b70"
GREEN = "#27643e"
CORAL = "#b83d2e"
AMBER = "#8a5200"
MUTED = "#43545b"
BG = "#f7f3ea"
CARD = "#ffffff"
BORDER = "#b8b3a8"

st.markdown(
    f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');
            .stApp {{
                background-color: {BG};
                background-image: linear-gradient(rgba(22,60,67,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(22,60,67,.035) 1px, transparent 1px);
                background-size: 28px 28px;
                color: {INK};
            }}
            .block-container {{ max-width: 1480px; padding-top: 2.5rem; padding-bottom: 4rem; }}
            h1, h2, h3, h4 {{ color: {NAVY}; font-family: 'Fraunces', Georgia, serif; letter-spacing: 0; }}
            h1 {{ font-size: clamp(2.1rem, 4vw, 3.8rem) !important; line-height: .98; margin-bottom: .35rem; }}
            h3 {{ font-size: 1.35rem !important; margin-top: .2rem; }}
            .stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea {{
                font-family: 'DM Sans', 'Trebuchet MS', sans-serif;
            }}
            .cl-kicker {{ color: {CORAL}; font-size: .72rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; margin-bottom: .7rem; }}
            .cl-sub {{ color: {MUTED}; font-size: 1rem; line-height: 1.55; max-width: 780px; margin-top: 0; }}
            .cl-rule {{ height: 3px; width: 72px; background: {CORAL}; margin: 1rem 0 1.4rem; }}
      .cl-card {{
                background: {CARD}; border: 1px solid {BORDER}; border-radius: 4px;
                padding: 1.15rem 1.25rem; margin-bottom: .85rem;
                box-shadow: 0 5px 18px rgba(22,60,67,.045);
      }}
      .cl-badge {{
                display: inline-block; padding: 4px 9px; border-radius: 3px;
                font-size: 0.69rem; letter-spacing: .03em; font-weight: 700; color: #fff;
                text-transform: uppercase;
      }}
      .cl-sample {{ background: {GREEN}; }}
      .cl-ai {{ background: {SKY}; }}
      .cl-navy {{ background: {NAVY}; }}
            .stButton > button, .stFormSubmitButton > button {{
                background: {TEAL}; color: #fff; border: 0; border-radius: 4px;
                font-weight: 700; min-height: 2.6rem; transition: background .15s ease, transform .15s ease;
      }}
            .stButton > button:hover, .stFormSubmitButton > button:hover {{
                background: {NAVY}; color: #fff; transform: translateY(-1px);
            }}
            .stTextArea textarea {{ background: {CARD}; color: {INK}; border: 1px solid {BORDER}; border-radius: 4px; line-height: 1.55; }}
            .stTextArea textarea::placeholder {{ color: {MUTED}; opacity: 1; }}
            .stTextArea textarea:focus {{ border-color: {TEAL}; box-shadow: 0 0 0 1px {TEAL}; }}
            div[data-baseweb="select"] > div {{ background: {CARD}; border-color: {BORDER}; color: {INK}; }}
            div[data-baseweb="select"] [data-testid="stMarkdownContainer"], div[data-baseweb="select"] input {{ color: {INK}; }}
            [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {BORDER}; border-radius: 4px; }}
      .cl-metric {{
                background: {CARD}; border: 1px solid {BORDER}; border-top: 3px solid {TEAL}; border-radius: 4px;
                padding: .95rem 1rem 1rem; min-height: 96px;
      }}
            .cl-metric .v {{ font-family: 'Fraunces', Georgia, serif; font-size: 2rem; line-height: 1; font-weight: 700; color: {NAVY}; }}
            .cl-metric .l {{ font-size: .72rem; color: {MUTED}; text-transform: uppercase; letter-spacing: .08em; margin-top: .45rem; }}
            .cl-warn {{ background: #fff3df; border-left: 4px solid {AMBER}; color: #76501b;
                                 padding: .75rem .9rem; border-radius: 2px; margin: .8rem 0; }}
            .cl-panel-title {{ color: {NAVY}; font-size: .75rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .5rem; }}
            .cl-empty {{ border: 1px dashed {BORDER}; background: {CARD}; color: {MUTED}; padding: 2rem; text-align: center; border-radius: 4px; }}
            [data-testid="stAlert"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 4px; color: {INK}; }}
            [data-testid="stAlert"] p, [data-testid="stAlert"] span {{ color: {INK} !important; }}
            .stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; }}
            @media (max-width: 700px) {{
                .block-container {{ padding-top: 1.5rem; }}
                h1 {{ font-size: 2.5rem !important; }}
                .cl-sub {{ font-size: .92rem; }}
            }}
    </style>
    """,
    unsafe_allow_html=True,
)

PRIORITY_COLORS = {"Low": GREEN, "Medium": SKY, "High": AMBER, "Critical": CORAL}
STATUS_COLORS = {"New": SKY, "In Review": NAVY, "Assigned": "#7665a8", "Resolved": GREEN, "Closed": MUTED}


# --------------------------- header -------------------------------------------
st.markdown('<div class="cl-kicker">Civic operations / Islamabad</div>', unsafe_allow_html=True)
st.markdown("# CivicLens Mini")
st.markdown('<div class="cl-rule"></div>', unsafe_allow_html=True)
st.markdown(
    '<p class="cl-sub">A calmer front door for city issues. Citizens submit '
    "complaints; an open-weight AI model categorises, "
    "summarises and suggests a priority — always for human review, never as an "
    "official decision.</p>",
    unsafe_allow_html=True,
)

ai_ok, ai_msg = ai_client.health_check()
dup_label = duplicates.active_method_label()

cols = st.columns([3, 2])
with cols[0]:
    if ai_ok:
        st.success(f"🤖 {ai_msg}")
    else:
        st.warning(f"🤖 AI analysis unavailable — {ai_msg}")
with cols[1]:
    st.info(f"🔎 Duplicate detection: {dup_label}")


# --------------------------- metrics ------------------------------------------
def render_metrics() -> None:
    s = storage.stats()
    m = st.columns(4)
    labels = [
        ("Total complaints", s["total"]),
        ("Open", s["open"]),
        ("High / Critical", s["by_priority"].get("High", 0) + s["by_priority"].get("Critical", 0)),
        ("Categories seen", len(s["by_category"])),
    ]
    for col, (label, val) in zip(m, labels):
        with col:
            st.markdown(
                f'<div class="cl-metric"><div class="v">{val}</div>'
                f'<div class="l">{label}</div></div>',
                unsafe_allow_html=True,
            )


render_metrics()
st.divider()

left, right = st.columns([5, 6], gap="large")


# --------------------------- submit form --------------------------------------
with left:
    st.markdown('<div class="cl-panel-title">Intake desk</div>', unsafe_allow_html=True)
    st.markdown("### 📝 Submit a complaint")
    with st.form("complaint_form", clear_on_submit=False):
        text = st.text_area(
            "Describe the civic issue",
            height=160,
            placeholder="e.g. The street light outside our house has been off for a week...",
        )
        submitted = st.form_submit_button("Analyse with AI & save")

    if submitted:
        if not text or len(text.strip()) < 10:
            st.error("Please enter at least a sentence describing the issue.")
        elif not ai_ok:
            st.error(
                "Cannot analyse: the AI runtime is not configured. "
                + ai_msg
                + "  Set OPENROUTER_API_KEY and reload."
            )
        else:
            with st.spinner("Analysing with the open-weight model..."):
                try:
                    analysis = ai_client.analyze_complaint(text)
                    existing = storage.load_all()
                    dups = duplicates.find_duplicates(text, existing)
                    record = storage.save_complaint(text, analysis, duplicates=dups)
                    st.session_state["last_record"] = record
                    st.success("Complaint analysed and saved.")
                except ai_client.AIError as exc:
                    st.error(f"AI runtime error: {exc}")
                except ValueError as exc:
                    st.error(f"Could not parse the model's analysis: {exc}")

    # Show last AI result
    rec = st.session_state.get("last_record")
    if rec:
        a = rec["analysis"]
        st.markdown("#### 🤖 AI analysis")
        if rec.get("duplicates"):
            st.markdown(
                '<div class="cl-warn">⚠️ Possible duplicate(s) found — see report below.</div>',
                unsafe_allow_html=True,
            )
        pc = PRIORITY_COLORS.get(a["suggested_priority"], SKY)
        st.markdown(
            f'<div class="cl-card">'
            f'<span class="cl-badge cl-navy">{escape(str(a["category"]))}</span> '
            f'<span class="cl-badge" style="background:{pc}">'
            f'Priority: {escape(str(a["suggested_priority"]))} (AI suggestion)</span><br><br>'
            f'<b>Summary:</b> {escape(str(a["summary"]))}<br>'
            f'<b>Reported duration:</b> {escape(str(a["reported_duration"] or "Not provided"))}<br>'
            f'<b>Location:</b> {escape(str(a["location"] or "Not provided"))}<br>'
            f'<b>Evidence:</b> {escape(", ".join(a["evidence_mentioned"]) or "None mentioned")}<br>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.caption("⚠️ Priority is an AI suggestion requiring human review. This complaint is NOT officially verified.")

        st.markdown("#### 📋 Copyable report")
        st.code(
            report_mod.build_report(rec, dup_method=duplicates.active_method()),
            language="text",
        )

    st.divider()
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("➕ Load 3 sample complaints (demo data)"):
            for sample in SAMPLES:
                storage.save_complaint(
                    sample["text"], sample["analysis"], is_sample=True
                )
            st.success("Loaded 3 demonstration complaints.")
            st.rerun()
    with sc2:
        if st.button("🗑️ Clear all complaints"):
            storage.clear_all()
            st.session_state.pop("last_record", None)
            st.success("Cleared.")
            st.rerun()


# --------------------------- recent complaints --------------------------------
with right:
    st.markdown('<div class="cl-panel-title">Operations queue</div>', unsafe_allow_html=True)
    st.markdown("### 📂 Recent complaints")
    items = storage.load_all()
    if not items:
        st.markdown(
            '<div class="cl-empty">No complaints yet.<br><small>Submit an issue or load the demo data to begin.</small></div>',
            unsafe_allow_html=True,
        )
    for item in items:
        a = item.get("analysis") or {}
        pc = PRIORITY_COLORS.get(a.get("suggested_priority", "Medium"), SKY)
        sc = STATUS_COLORS.get(item.get("status", "New"), SKY)
        sample_badge = (
            '<span class="cl-badge cl-sample">DEMO DATA</span> ' if item.get("is_sample") else ""
        )
        with st.container():
            st.markdown(
                f'<div class="cl-card">'
                f'{sample_badge}'
                f'<span class="cl-badge cl-navy">{escape(str(a.get("category","Other")))}</span> '
                f'<span class="cl-badge" style="background:{pc}">{escape(str(a.get("suggested_priority","Medium")))}</span> '
                f'<span class="cl-badge" style="background:{sc}">{escape(str(item.get("status","New")))}</span>'
                f'<br><br><b>#{escape(str(item.get("id","")))}</b> — {escape(str(a.get("summary","")))}'
                f'<br><span style="color:{MUTED};font-size:0.82rem">'
                f'📍 {escape(str(a.get("location") or "No location"))} · ⏱ {escape(str(a.get("reported_duration") or "n/a"))} · '
                f'{escape(str(item.get("created_at","")))}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([3, 1])
            with c1:
                new_status = st.selectbox(
                    "Status",
                    storage.STATUSES,
                    index=storage.STATUSES.index(item.get("status", "New")),
                    key=f"status_{item['id']}",
                    label_visibility="collapsed",
                )
                if new_status != item.get("status"):
                    storage.update_status(item["id"], new_status)
                    st.rerun()
            with c2:
                if st.button("Delete", key=f"del_{item['id']}"):
                    storage.delete_complaint(item["id"])
                    st.rerun()
