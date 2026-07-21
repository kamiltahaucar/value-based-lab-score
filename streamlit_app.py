"""
Value-Based Laboratory Score — web calculator
Streamlit app. Deploy on Streamlit Community Cloud (share.streamlit.io).

Run locally:
    pip install -r requirements.txt
    streamlit run streamlit_app.py
"""

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
DATA_FILE = Path(__file__).parent / "value_based_items.json"


@st.cache_data
def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


DATA = load_data()
META = DATA["meta"]
ITEMS = DATA["items"]
LEVELS = META["score_levels"]                 # [0, 0.25, 0.5, 0.75, 1.0]
LEVEL_LABELS = META["level_labels"]
PROCESS_ORDER = META["process_order"]
PROCESS_MAX = META["process_max"]
TOTAL_MAX = META["total_max"]                 # 100
N_ITEMS = len(ITEMS)

# --- Weights are derived automatically -------------------------------------- #
# Each process has a fixed total (PROCESS_MAX). Every item in that process gets
# an equal share, so the five processes always sum to 100 no matter how many
# items you add or remove. To add an item you therefore only need to add its
# JSON block — no weight to compute. (Any "weight" left in the JSON is ignored.)
from collections import Counter

_proc_counts = Counter(it["process"] for it in ITEMS)
for _it in ITEMS:
    proc = _it["process"]
    _it["weight"] = PROCESS_MAX[proc] / _proc_counts[proc]

# --------------------------------------------------------------------------- #
# Page config & light styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Value-Based Laboratory Score",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 3rem;}
      div[data-testid="stMetricValue"] {font-size: 1.7rem;}
      .item-expl {color:#555; font-size:0.86rem; white-space:pre-line;
                  margin:-4px 0 4px 0;}
      .subhead {font-weight:600; color:#1a4f7a; margin-top:0.4rem;}
      .weight-tag {color:#888; font-size:0.78rem;}
      div[role="radiogroup"] label {margin-right:0.15rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Session-state helpers  (selection stored per item id -> level or None)
# --------------------------------------------------------------------------- #
def _key(item_id):
    return f"sel_{item_id}"


def get_selection(item_id):
    return st.session_state.get(_key(item_id), None)


def reset_all():
    for it in ITEMS:
        st.session_state[_key(it["id"])] = None
    st.session_state["open_sub"] = None


# Only the selected domain's questions are rendered at a time. Streamlit
# normally garbage-collects the state of widgets that were not rendered in a
# run, which would erase answers when switching domains. Re-assigning each
# existing value marks it as persistent app state and prevents that cleanup.
for _it in ITEMS:
    _k = _key(_it["id"])
    if _k in st.session_state:
        st.session_state[_k] = st.session_state[_k]


def remember_open(exp_id):
    """Keep the expander the user is editing open across reruns."""
    st.session_state["open_sub"] = exp_id


# --------------------------------------------------------------------------- #
# Score computation
# --------------------------------------------------------------------------- #
def compute():
    """Return per-item, per-process and total achieved scores."""
    rows = []
    proc_score = {p: 0.0 for p in PROCESS_ORDER}
    proc_unanswered = {p: 0.0 for p in PROCESS_ORDER}  # weight of blank items
    proc_missed = {p: 0.0 for p in PROCESS_ORDER}      # points lost on answered
    proc_counts = {p: [0, 0] for p in PROCESS_ORDER}   # [answered, total]
    answered = 0
    for it in ITEMS:
        lvl = get_selection(it["id"])
        p = it["process"]
        proc_counts[p][1] += 1
        if lvl is None:
            achieved = 0.0
            proc_unanswered[p] += it["weight"]
            answered_flag = False
        else:
            achieved = lvl * it["weight"]
            proc_score[p] += achieved
            proc_missed[p] += (1.0 - lvl) * it["weight"]
            proc_counts[p][0] += 1
            answered += 1
            answered_flag = True
        rows.append(
            {
                "Process": it["process"],
                "Section": it["section"],
                "Subheading": it["subheading"],
                "Item": it["item"],
                "Level": lvl,
                "Weight": round(it["weight"], 4),
                "Item score": round(achieved, 4),
                "Answered": answered_flag,
            }
        )
    total = sum(proc_score.values())
    return rows, proc_score, total, answered, proc_unanswered, proc_missed, proc_counts


# --------------------------------------------------------------------------- #
# Sidebar — live results
# --------------------------------------------------------------------------- #
def render_sidebar(proc_score, total, answered, rows):
    with st.sidebar:
        st.markdown("## 📊 Your score")
        st.metric(
            "Total score",
            f"{total:.2f} / {TOTAL_MAX:.0f}",
            help="Sum of (selected level × item weight) across all items.",
        )
        st.progress(min(total / TOTAL_MAX, 1.0))
        st.caption(f"Items answered: **{answered} / {N_ITEMS}**")
        st.progress(answered / N_ITEMS)

        st.divider()
        st.markdown("### By process")
        for p in PROCESS_ORDER:
            pmax = PROCESS_MAX[p]
            pval = proc_score[p]
            pct = (pval / pmax * 100) if pmax else 0
            st.markdown(f"**{p}**")
            st.markdown(
                f"<span class='weight-tag'>{pval:.2f} / {pmax:.0f} "
                f"&nbsp;({pct:.0f}%)</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(pval / pmax, 1.0) if pmax else 0.0)

        st.divider()
        # ---- downloads ----
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download results (CSV)",
            data=csv,
            file_name="value_based_score_results.csv",
            mime="text/csv",
            width='stretch',
        )

        # Excel with a small summary sheet
        xls_buffer = io.BytesIO()
        with pd.ExcelWriter(xls_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Detail")
            summary = pd.DataFrame(
                {
                    "Process": PROCESS_ORDER + ["TOTAL"],
                    "Achieved": [round(proc_score[p], 2) for p in PROCESS_ORDER]
                    + [round(total, 2)],
                    "Max": [PROCESS_MAX[p] for p in PROCESS_ORDER] + [TOTAL_MAX],
                }
            )
            summary["%"] = (summary["Achieved"] / summary["Max"] * 100).round(1)
            summary.to_excel(writer, index=False, sheet_name="Summary")
        st.download_button(
            "⬇️ Download results (Excel)",
            data=xls_buffer.getvalue(),
            file_name="value_based_score_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )

        st.divider()
        st.button("🔄 Reset all answers", on_click=reset_all,
                  width='stretch')


# --------------------------------------------------------------------------- #
# Item widget
# --------------------------------------------------------------------------- #
def render_item(it, exp_id):
    weight = it["weight"]
    st.markdown(f"**{it['item']}**  "
                f"<span class='weight-tag'>· weight {weight:.3f}</span>",
                unsafe_allow_html=True)
    if it["explanation"]:
        st.markdown(f"<div class='item-expl'>{it['explanation']}</div>",
                    unsafe_allow_html=True)

    # radio with an explicit "not selected" default (index=None)
    st.radio(
        label="Score level",
        options=LEVELS,
        format_func=lambda v: f"{v:g}  ·  {LEVEL_LABELS[str(v)]}",
        key=_key(it["id"]),
        index=None,
        horizontal=True,
        label_visibility="collapsed",
        on_change=remember_open,
        args=(exp_id,),
    )
    lvl = get_selection(it["id"])
    if lvl is not None:
        st.caption(f"→ contributes **{lvl * weight:.3f}** points "
                   f"({lvl:g} × {weight:.3f})")
    st.markdown("<hr style='margin:0.6rem 0; opacity:0.25'>",
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Main layout
# --------------------------------------------------------------------------- #
st.title("🧪 Value-Based Laboratory Score")
st.markdown(
    "A self-assessment calculator for the value of a clinical laboratory across "
    "five domains. For each item, select the level of implementation. "
    "Each item's contribution is **level × weight**, and the total is scored "
    "out of **100**."
)

# --- score-level guide (always visible) ------------------------------------ #
with st.container(border=True):
    st.markdown("##### ℹ️ How the score levels work")
    cols = st.columns(len(LEVELS))
    for c, lvl in zip(cols, LEVELS):
        c.markdown(f"**{lvl:g}**")
        c.caption(LEVEL_LABELS[str(lvl)])
    st.caption(
        "Item weights are fixed by the model and differ between domains "
        "(e.g. each Traceability item = 20/38, each Clinical-interaction item "
        "= 30/5). The five domains sum to 100 points."
    )

(rows, proc_score, total, answered,
 proc_unanswered, proc_missed, proc_counts) = compute()
render_sidebar(proc_score, total, answered, rows)

# --- Domain overview: stacked bars ------------------------------------------ #
# Green  = points achieved
# Orange = potential of unanswered items (their full weight)
# Red    = points missed on answered items ((1 - level) × weight)
# The three segments always add up to each domain's maximum.
import altair as alt

seg_order = ["Achieved", "Unanswered", "Missed"]
seg_colors = {"Achieved": "#2e9e4f", "Unanswered": "#f2a33c", "Missed": "#d64545"}
long_rows = []
for p in PROCESS_ORDER:
    long_rows += [
        {"Process": p, "Segment": "Achieved", "Points": round(proc_score[p], 3)},
        {"Process": p, "Segment": "Unanswered", "Points": round(proc_unanswered[p], 3)},
        {"Process": p, "Segment": "Missed", "Points": round(proc_missed[p], 3)},
    ]
chart_long = pd.DataFrame(long_rows)

st.markdown("#### Domain overview")
chart = (
    alt.Chart(chart_long)
    .mark_bar()
    .encode(
        x=alt.X("Process:N", sort=PROCESS_ORDER, title=None,
                axis=alt.Axis(labelAngle=-25, labelLimit=220)),
        y=alt.Y("Points:Q", title="Points",
                scale=alt.Scale(domain=[0, max(PROCESS_MAX.values())])),
        color=alt.Color(
            "Segment:N",
            sort=seg_order,
            scale=alt.Scale(domain=seg_order,
                            range=[seg_colors[s] for s in seg_order]),
            legend=alt.Legend(orient="top", title=None),
        ),
        order=alt.Order("stack_order:Q"),
        tooltip=["Process", "Segment", alt.Tooltip("Points:Q", format=".2f")],
    )
    .transform_calculate(
        stack_order="datum.Segment == 'Achieved' ? 0 : "
                    "(datum.Segment == 'Unanswered' ? 1 : 2)"
    )
    .properties(height=300)
)
st.altair_chart(chart, width='stretch')
st.caption(
    "🟩 Achieved points · 🟧 Unanswered items (not yet scored) · "
    "🟥 Missed points on answered items — each bar totals the domain maximum."
)

# Domain selector.
# ROOT CAUSE of the "jumps back to the first domain" bug: any widget whose
# option LABELS change between reruns (tabs, segmented_control with live
# counts, ...) is treated by Streamlit's frontend as a brand-new widget, so
# the selection resets to the default. The fix is to keep the widget's
# options and labels 100% static, and render the live answered-counts in a
# plain text line below — text can change freely because it holds no state.
if "active_proc" not in st.session_state:
    st.session_state["active_proc"] = PROCESS_ORDER[0]

selected_proc = st.segmented_control(
    "Domain",
    options=PROCESS_ORDER,          # static values, static labels — never resets
    key="active_proc",
    label_visibility="collapsed",
)
# segmented_control returns None if the user clicks the active option to
# deselect it; fall back to the last known domain in that case.
if selected_proc is None:
    selected_proc = st.session_state.get("last_proc", PROCESS_ORDER[0])
proc = selected_proc
st.session_state["last_proc"] = proc

# Live answered/total counts for every domain (plain text, safe to update).
_SHORT = {
    "Traceability through total testing process": "Traceability",
    "Level of automation and digitalization": "Automation",
    "Quality of laboratory information": "Lab information",
    "Clinical interaction": "Clinical",
    "Innovation and research": "Innovation",
}
counts_line = " · ".join(
    f"{'**' if p == proc else ''}{_SHORT.get(p, p.split()[0])}"
    f" {proc_counts[p][0]}/{proc_counts[p][1]}{'**' if p == proc else ''}"
    for p in PROCESS_ORDER
)
st.caption(counts_line)

pmax = PROCESS_MAX[proc]
pval = proc_score[proc]
st.markdown(
    f"### {proc} &nbsp; "
    f"<span class='weight-tag'>{pval:.2f} / {pmax:.0f} points · "
    f"{proc_counts[proc][0]}/{proc_counts[proc][1]} questions answered"
    f"</span>",
    unsafe_allow_html=True,
)
proc_items = [it for it in ITEMS if it["process"] == proc]

# group by Section, then Subheading
sections = []
for it in proc_items:
    if not sections or sections[-1][0] != it["section"]:
        sections.append((it["section"], []))
    sections[-1][1].append(it)

for section_name, sec_items in sections:
    st.markdown(f"#### {section_name}")
    subs = []
    for it in sec_items:
        if not subs or subs[-1][0] != it["subheading"]:
            subs.append((it["subheading"], []))
        subs[-1][1].append(it)
    for sub_name, sub_items in subs:
        # stable id derived from content, not a counter, so it never shifts
        exp_id = f"exp::{proc}::{section_name}::{sub_name}"
        answered_sub = sum(
            1 for it in sub_items if get_selection(it["id"]) is not None
        )
        with st.expander(
            f"{sub_name}  ·  {answered_sub}/{len(sub_items)} answered",
            expanded=(st.session_state.get("open_sub") == exp_id),
        ):
            st.markdown(
                f"<div class='subhead'>{sub_name}</div>",
                unsafe_allow_html=True,
            )
            for it in sub_items:
                render_item(it, exp_id)

st.divider()
st.caption(
    "Built with Streamlit · scores computed live in your browser session · "
    "nothing is stored on a server."
)
