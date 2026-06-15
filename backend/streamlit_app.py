"""
Intelligent Patent Feasibility & Semantic Retrieval Platform
=============================================================
Streamlit demo dashboard — single file, zero configuration.

Run:
    cd patent-kg/backend
    streamlit run streamlit_app.py
"""

# ── Env vars MUST be set before any transformers/ST import ────────────────────
import os
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

import sys
import time
from pathlib import Path

# ── Ensure src/ is importable ─────────────────────────────────────────────────
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# Page config — MUST be first Streamlit call
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Patent Intelligence Platform",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# Global CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Global font & base ───────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Main title ───────────────────────────────────────────────────────────── */
.main-title {
    font-size: 2rem; font-weight: 700; letter-spacing: -0.5px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.15rem;
}
.main-subtitle {
    font-size: 0.95rem; color: #94a3b8; margin-bottom: 1.5rem;
}

/* ── Section headers ──────────────────────────────────────────────────────── */
.section-header {
    font-size: 1.05rem; font-weight: 600; color: #e2e8f0;
    border-left: 3px solid #6366f1; padding-left: 0.65rem;
    margin: 1.5rem 0 0.8rem 0;
}

/* ── Keyword badge ────────────────────────────────────────────────────────── */
.kw-badge {
    display: inline-block; padding: 3px 12px; margin: 3px;
    background: #1e1b4b; color: #a5b4fc;
    border: 1px solid #4338ca; border-radius: 20px;
    font-size: 0.8rem; font-weight: 500;
}
.ent-badge {
    display: inline-block; padding: 3px 12px; margin: 3px;
    background: #0c2a2a; color: #34d399;
    border: 1px solid #059669; border-radius: 20px;
    font-size: 0.8rem; font-weight: 500;
}

/* ── Patent card ──────────────────────────────────────────────────────────── */
.patent-card {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem; position: relative;
    transition: border-color 0.2s;
}
.patent-card:hover { border-color: #4338ca; }
.patent-rank {
    position: absolute; top: 1rem; right: 1.2rem;
    font-size: 1.4rem; font-weight: 700; color: #334155;
}
.patent-title {
    font-size: 0.92rem; font-weight: 600; color: #e2e8f0;
    margin-bottom: 0.3rem; padding-right: 2.5rem;
    text-transform: capitalize;
}
.patent-id { font-size: 0.72rem; color: #475569; font-family: monospace; margin-bottom: 0.5rem; }
.patent-abstract { font-size: 0.82rem; color: #94a3b8; line-height: 1.5; margin-bottom: 0.6rem; }
.domain-chip {
    display: inline-block; padding: 2px 10px;
    background: #0f2027; border: 1px solid #0e7490;
    color: #22d3ee; border-radius: 6px; font-size: 0.72rem; font-weight: 600;
}
.score-label {
    font-size: 0.75rem; color: #64748b; margin-bottom: 2px;
}

/* ── Metric card ──────────────────────────────────────────────────────────── */
.metric-box {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
}
.metric-val { font-size: 1.6rem; font-weight: 700; color: #6366f1; }
.metric-lbl { font-size: 0.78rem; color: #64748b; margin-top: 2px; }

/* ── Pipeline step ────────────────────────────────────────────────────────── */
.pipe-step {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 10px; padding: 0.8rem 0.6rem; text-align: center;
}
.pipe-icon { font-size: 1.5rem; }
.pipe-label { font-size: 0.78rem; font-weight: 600; color: #cbd5e1; margin-top: 4px; }
.pipe-desc { font-size: 0.68rem; color: #475569; margin-top: 2px; }
.pipe-arrow { font-size: 1.1rem; color: #334155; text-align: center; padding-top: 1.3rem; }

/* ── Clean-text box ───────────────────────────────────────────────────────── */
.clean-text-box {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 8px; padding: 0.85rem 1rem;
    font-size: 0.87rem; color: #cbd5e1; line-height: 1.6;
    font-style: italic;
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #080d18; }

/* ── Expansion type badge ─────────────────────────────────────────────────── */
.exp-badge-family {
    display: inline-block; padding: 2px 10px; margin-bottom: 6px;
    background: #1a1040; color: #a78bfa;
    border: 1px solid #7c3aed; border-radius: 6px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
}
.exp-badge-cpc {
    display: inline-block; padding: 2px 10px; margin-bottom: 6px;
    background: #0c2030; color: #38bdf8;
    border: 1px solid #0369a1; border-radius: 6px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
}
.expansion-header {
    font-size: 0.85rem; color: #64748b;
    margin: 0.8rem 0 0.5rem 0;
}

/* ── KG status card ───────────────────────────────────────────────────────── */
.kg-card {
    border-radius: 12px; padding: 1.1rem 1.4rem;
    margin: 0.6rem 0; border: 1px solid;
}
.kg-card.building {
    background: #0f1f2e; border-color: #0e7490;
}
.kg-card.done {
    background: #0a1f14; border-color: #16a34a;
}
.kg-status-title {
    font-size: 0.95rem; font-weight: 600; margin-bottom: 0.5rem;
}
.kg-card.building .kg-status-title { color: #22d3ee; }
.kg-card.done     .kg-status-title { color: #4ade80; }
.kg-stat-row {
    display: flex; gap: 1.2rem; flex-wrap: wrap; margin-top: 0.6rem;
}
.kg-stat {
    background: #0f172a; border-radius: 8px;
    padding: 0.4rem 0.85rem; text-align: center;
    border: 1px solid #1e293b;
}
.kg-stat-val { font-size: 1.1rem; font-weight: 700; color: #6366f1; }
.kg-stat-lbl { font-size: 0.68rem; color: #64748b; }
/* ── GNN Analysis section ───────────────────────────────────────────────── */
.gnn-controls {
    background: #0a0f1e; border: 1px solid #1e293b;
    border-radius: 12px; padding: 1.1rem 1.4rem;
    margin-bottom: 1.2rem;
}
.gnn-mode-badge {
    display: inline-block; padding: 3px 14px; margin-bottom: 0.5rem;
    border-radius: 20px; font-size: 0.75rem; font-weight: 700;
    letter-spacing: 0.05em; text-transform: uppercase;
}
.gnn-mode-badge.novelty  { background: #1a1040; color: #a78bfa; border: 1px solid #7c3aed; }
.gnn-mode-badge.graph_sim { background: #0c2030; color: #38bdf8; border: 1px solid #0369a1; }
.gnn-insight {
    background: linear-gradient(135deg, #0f172a, #1a1040);
    border: 1px solid #4338ca; border-radius: 12px;
    padding: 1.1rem 1.4rem; margin: 1rem 0;
}
.gnn-insight-title { font-size: 0.9rem; font-weight: 700; color: #a5b4fc; margin-bottom: 0.4rem; }
.gnn-insight-body  { font-size: 0.82rem; color: #cbd5e1; line-height: 1.5; }
.rank-up   { color: #4ade80; font-weight: 700; }
.rank-down { color: #f87171; font-weight: 700; }
.rank-same { color: #475569; font-weight: 500; }
.score-chip {
    display: inline-block; padding: 1px 8px; border-radius: 6px;
    font-size: 0.72rem; font-weight: 600; font-family: monospace;
}
.score-chip.semantic { background: #0f2027; color: #22d3ee; border: 1px solid #0e7490; }
.score-chip.novelty  { background: #1a1040; color: #a78bfa; border: 1px solid #7c3aed; }
.score-chip.combined { background: #0a1f14; color: #4ade80; border: 1px solid #16a34a; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Backend loader (cached — loaded once per session)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Loading AI pipeline…")
def load_pipeline():
    """Import and warm-up the integration pipeline once."""
    from integration.pipeline import run_end_to_end
    return run_end_to_end


@st.cache_resource(show_spinner=False)
def load_kg_builder():
    """Import the KG builder once per session."""
    from kg.builder import KGBuilder
    return KGBuilder


def _expand_kg(patent_ids: list, cpc_cap: int = 10) -> dict:
    """Run KG expansion and return family + CPC sibling patent dicts."""
    from kg.expander import expand_via_kg
    return expand_via_kg(patent_ids, cpc_cap=cpc_cap)


def _build_kg(patent_ids: list) -> dict:
    """
    Run the KG builder for the given IDs and return a stats dict.
    Counts are queried back from Neo4j after writing so the UI shows
    real numbers rather than estimates.
    """
    from neo4j import GraphDatabase
    import os
    from dotenv import load_dotenv
    load_dotenv()

    KGBuilderCls = load_kg_builder()
    with KGBuilderCls() as builder:
        builder.build_subgraph(patent_ids)

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    with driver.session() as session:
        counts = session.run(
            """
            MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS cnt
            RETURN lbl, cnt ORDER BY lbl
            """
        ).data()
        edge_counts = session.run(
            """
            MATCH ()-[r]->() WITH type(r) AS t, count(r) AS cnt
            RETURN t, cnt ORDER BY t
            """
        ).data()
    driver.close()

    nodes = {row["lbl"]: row["cnt"] for row in counts}
    edges = {row["t"]:   row["cnt"] for row in edge_counts}
    return {"nodes": nodes, "edges": edges}


# ══════════════════════════════════════════════════════════════════════════════
# Helper renderers
# ══════════════════════════════════════════════════════════════════════════════

def render_badges(items: list, badge_class: str, empty_msg: str):
    if not items:
        st.markdown(f"<span style='color:#475569;font-size:0.82rem'>{empty_msg}</span>",
                    unsafe_allow_html=True)
        return
    html = "".join(f'<span class="{badge_class}">{item}</span>' for item in items)
    st.markdown(html, unsafe_allow_html=True)


def render_score_bar(score: float):
    """Mini score progress bar using st.progress."""
    pct = min(int(score * 100), 100)          # already cosine ~0-1
    # Colour: green for high, amber mid, grey low
    colour = "#22c55e" if pct >= 60 else ("#f59e0b" if pct >= 40 else "#64748b")
    st.markdown(
        f"""<div class="score-label">Similarity Score: <b style="color:{colour}">{score:.4f}</b></div>""",
        unsafe_allow_html=True,
    )
    st.progress(pct)


def render_expanded_card(patent: dict):
    title    = patent.get("title", "Untitled").title()[:120]
    pid      = patent.get("patent_id", "—")
    abstract = patent.get("abstract", "—")
    domain   = patent.get("domain", "—")
    url      = patent.get("url", "#")
    exp_type = patent.get("expansion_type", "")
    cited    = patent.get("cited_by_patent_count", "0")
    year     = patent.get("publication_year", "")

    badge_class = "exp-badge-family" if exp_type == "family" else "exp-badge-cpc"
    badge_label = "FAMILY MEMBER" if exp_type == "family" else "CPC SIBLING"

    st.markdown(f"""
    <div class="patent-card">
        <span class="{badge_class}">{badge_label}</span>
        <div class="patent-title">{title}</div>
        <div class="patent-id">ID: {pid} &nbsp;·&nbsp; {year}</div>
        <div class="patent-abstract">{abstract[:280]}…</div>
        <span class="domain-chip">{domain}</span>
        &nbsp;
        <span style="font-size:0.72rem;color:#475569;">
            Cited by {cited} patents
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"[View on Lens.org]({url})", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:0.4rem'></div>", unsafe_allow_html=True)


def render_patent_card(hit: dict):
    title   = hit.get("title", "Untitled").title()[:120]
    pid     = hit.get("patent_id", "—")
    score   = hit.get("score", 0.0)
    abstract = hit.get("abstract", "—")
    domain  = hit.get("domain", "—")
    url     = hit.get("url", "#")
    rank    = hit.get("rank", 0)

    st.markdown(f"""
    <div class="patent-card">
        <div class="patent-rank">#{rank}</div>
        <div class="patent-title">{title}</div>
        <div class="patent-id">ID: {pid}</div>
        <div class="patent-abstract">{abstract[:280]}…</div>
        <span class="domain-chip">{domain}</span>
    </div>
    """, unsafe_allow_html=True)

    render_score_bar(score)
    st.markdown(f"[View on Lens.org]({url})", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:0.4rem'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("##Patent Intelligence")
    st.markdown("*Graph-Enhanced Semantic Retrieval Platform*")
    st.divider()

    st.markdown("###Project Overview")
    st.markdown("""
    An AI-powered platform that takes a raw innovation idea and:
    - Preprocesses it with Gemini + spaCy NLP
    - Converts it to a semantic embedding
    - Retrieves the most similar existing patents
    - Surfaces knowledge for novelty analysis
    """)

    st.divider()
    st.markdown("###Modules Completed")
    modules = [
        "[DONE] Dataset Ingestion (58k+ patents)",
        "[DONE] NLP Preprocessing (Gemini + spaCy)",
        "[DONE] Embedding Generation (MiniLM)",
        "[DONE] FAISS Vector Index",
        "[DONE] Semantic Patent Retrieval",
        "[DONE] Knowledge Graph (Neo4j)",
        "[WIP]  GNN Re-ranking",
        "[WIP]  Novelty Scoring",
    ]
    for item in modules:
        st.markdown(f"  {item}")

    st.divider()
    st.markdown("### 🛠️ Tech Stack")
    for tech in [
        "🐍 Python 3.13",
        "🤖 Google Gemini 2.5 Flash",
        "🧠 spaCy (en_core_web_sm)",
        "🔢 Sentence Transformers",
        "⚡ FAISS (Facebook AI)",
        "🗄️ Pandas + NumPy",
        "📊 Streamlit",
    ]:
        st.markdown(f"  {tech}")

    st.divider()
    st.caption("Demo build · May 2026")


# ══════════════════════════════════════════════════════════════════════════════
# Main content
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="main-title">Intelligent Patent Feasibility & Semantic Retrieval Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Enter an innovation idea → AI extracts concepts → FAISS finds the closest existing patents in milliseconds</div>', unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — User Idea Input
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Step 1 — Describe Your Innovation Idea</div>', unsafe_allow_html=True)

EXAMPLE_IDEAS = [
    "Select an example…",
    "A wearable EEG device that uses deep learning to detect early signs of epileptic seizures and automatically alerts caregivers via a mobile app.",
    "An autonomous drone navigation system using reinforcement learning and LiDAR sensor fusion for safe flight in urban environments.",
    "A federated learning framework for privacy-preserving medical image analysis across multiple hospitals without sharing raw patient data.",
    "A solid-state lithium battery with a novel electrolyte composition that improves energy density by 40% over conventional lithium-ion cells.",
    "An AI-powered smart grid system that predicts energy demand using historical consumption patterns and weather data to optimize renewable energy distribution.",
]

col_input, col_ex = st.columns([3, 1])
with col_ex:
    example = st.selectbox("Or load an example", EXAMPLE_IDEAS, label_visibility="collapsed")

with col_input:
    default_val = "" if example == EXAMPLE_IDEAS[0] else example
    user_idea = st.text_area(
        "Your innovation idea",
        value=default_val,
        height=110,
        placeholder="Describe your invention idea in plain English…",
        label_visibility="collapsed",
    )

col_btn, col_k, col_gnn, col_spacer = st.columns([1, 1, 2, 2])
with col_btn:
    run_btn = st.button("Analyze Idea", type="primary", use_container_width=True)
with col_k:
    top_k = st.selectbox("Top-K results", [5, 10, 25, 50, 100], index=0, label_visibility="collapsed")
with col_gnn:
    gnn_mode_choice = st.selectbox(
        "GNN Mode",
        ["novelty", "graph_sim"],
        format_func=lambda m: "GNN: Novelty Score" if m == "novelty" else "GNN: Graph Similarity",
        label_visibility="collapsed",
        help="'Novelty Score' uses pre-computed lookup from the Colab notebook. "
             "'Graph Similarity' computes structural uniqueness live from node_embeddings.npy.",
    )

# ─────────────────────────────────────────────────────────────────────────────
# Run pipeline on button click
# ─────────────────────────────────────────────────────────────────────────────
if run_btn:
    if not user_idea.strip():
        st.warning("Please enter an idea before running the analysis.")
        st.stop()

    t_start = time.perf_counter()

    with st.spinner("Running AI pipeline — NLP → Embedding → FAISS retrieval…"):
        try:
            pipeline_fn = load_pipeline()
            result = pipeline_fn(user_idea.strip(), top_k=top_k, gnn_mode=gnn_mode_choice)
        except Exception as e:
            st.error(f"**Pipeline error:** {e}")
            st.stop()

    latency_ms = (time.perf_counter() - t_start) * 1000
    st.session_state["result"]     = result
    st.session_state["latency_ms"] = latency_ms

# ─────────────────────────────────────────────────────────────────────────────
# Display results (persists after button click via session_state)
# ─────────────────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    result     = st.session_state["result"]
    latency_ms = st.session_state.get("latency_ms", 0)
    nlp        = result.get("nlp_result", {})
    hits       = result.get("results", [])

    st.success("Analysis complete!")
    st.divider()

    # ── Section 2: NLP Analysis ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Step 2 — NLP Analysis</div>', unsafe_allow_html=True)

    with st.expander("Preprocessed Text (clean_text)", expanded=True):
        st.markdown(
            f'<div class="clean-text-box">{nlp.get("clean_text", "—")}</div>',
            unsafe_allow_html=True,
        )

    col_kw, col_ent = st.columns(2)
    with col_kw:
        st.markdown("**Extracted Keywords**")
        render_badges(nlp.get("keywords", []), "kw-badge", "No keywords extracted.")

    with col_ent:
        st.markdown("**Named Entities**")
        render_badges(nlp.get("entities", []), "ent-badge", "No named entities found.")

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    # Query text used for FAISS
    with st.expander("Query sent to FAISS"):
        st.code(result.get("query_text", ""), language="text")

    st.divider()

    # ── Section 3: Semantic Retrieval Results ─────────────────────────────────
    st.markdown(f'<div class="section-header">Step 3 — Top-{top_k} Semantically Similar Patents</div>', unsafe_allow_html=True)

    if not hits:
        st.info("No results returned. Try a different query.")
    else:
        for hit in hits:
            render_patent_card(hit)

    st.divider()

    # ── Section 3.5: GNN Intelligence Layer ────────────────────────────────────
    st.markdown('<div class="section-header">🧠 GNN Intelligence Layer — Re-ranking & Novelty Analysis</div>',
                unsafe_allow_html=True)

    if not hits or not any("novelty_score" in h for h in hits):
        st.info("💡 GNN scorer is unavailable — missing `novelty_scores.json` or `node_embeddings.npy` in `backend/data/vector_store/`. Run the Colab training notebook to generate these files.")
    else:
        # ── Controls ──────────────────────────────────────────────────────────
        active_mode = hits[0].get("gnn_mode", "novelty")
        mode_label  = "Novelty Score" if active_mode == "novelty" else "Graph Similarity"
        badge_cls   = active_mode

        st.markdown(
            f'<div class="gnn-controls">'
            f'<span class="gnn-mode-badge {badge_cls}">{mode_label}</span> '
            f'<span style="font-size:0.8rem;color:#64748b;">— Adjust weights below to re-rank results '
            f'without re-running the pipeline</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])
        with ctrl1:
            sem_w = st.slider(
                "🔵 Semantic weight (FAISS)",
                min_value=0.0, max_value=1.0, value=0.6, step=0.05,
                key="gnn_sem_w",
                help="Weight given to FAISS cosine-similarity score.",
            )
        with ctrl2:
            nov_w = st.slider(
                "🟣 GNN weight",
                min_value=0.0, max_value=1.0, value=0.4, step=0.05,
                key="gnn_nov_w",
                help="Weight given to the GNN score (novelty or graph similarity).",
            )
        with ctrl3:
            st.markdown("<br>", unsafe_allow_html=True)
            total_w = sem_w + nov_w
            if abs(total_w - 1.0) > 0.01:
                st.warning(f"⚠️ Weights sum to {total_w:.2f} (not 1.0). Scores are relative.")
            else:
                st.success(f"✅ Weights: {sem_w:.0%} semantic + {nov_w:.0%} GNN")

        # ── Live re-rank with slider weights ──────────────────────────────────
        import copy
        reranked = copy.deepcopy(hits)
        for h in reranked:
            h["combined_score"] = round(
                sem_w * h["score"] + nov_w * h.get("novelty_score", 0.5), 4
            )
        reranked.sort(key=lambda h: h["combined_score"], reverse=True)
        for i, h in enumerate(reranked):
            h["rank"] = i + 1

        # ── Score distribution chart ──────────────────────────────────────────
        st.markdown("**Score Distribution across Retrieved Patents**")
        import pandas as pd
        chart_data = pd.DataFrame([
            {
                "Patent": f"#{h.get('faiss_rank', h['rank'])} " + h.get("patent_id", "")[:20],
                "Semantic (FAISS)": round(h["score"], 4),
                "GNN Score":        round(h.get("novelty_score", 0.0), 4),
                "Combined":         round(h["combined_score"], 4),
            }
            for h in reranked
        ]).set_index("Patent")
        st.bar_chart(chart_data, height=220, color=["#22d3ee", "#a78bfa", "#4ade80"])

        # ── Re-ranked results table ───────────────────────────────────────────
        st.markdown("**Re-ranked Results**")

        gnn_label = "Novelty" if active_mode == "novelty" else "Graph Uniq."
        header_html = (
            f"<div style='display:grid;grid-template-columns:50px 1fr 90px 90px 90px 70px;"
            f"gap:0.5rem;padding:0.4rem 0.8rem;background:#0a0f1e;"
            f"border-radius:8px 8px 0 0;font-size:0.75rem;font-weight:700;color:#475569;'>"
            f"<span>Rank</span><span>Patent</span>"
            f"<span>Semantic</span><span>{gnn_label}</span><span>Combined</span><span>Δ Rank</span>"
            f"</div>"
        )
        st.markdown(header_html, unsafe_allow_html=True)

        for h in reranked:
            new_rank   = h["rank"]
            old_rank   = h.get("faiss_rank", new_rank)
            delta      = old_rank - new_rank   # positive = moved up
            if delta > 0:
                delta_html = f'<span class="rank-up">▲+{delta}</span>'
            elif delta < 0:
                delta_html = f'<span class="rank-down">▼{delta}</span>'
            else:
                delta_html = f'<span class="rank-same">—</span>'

            sem_score = h["score"]
            nov_score = h.get("novelty_score", 0.0)
            comb      = h["combined_score"]

            sem_color  = "#22c55e" if sem_score >= 0.6 else ("#f59e0b" if sem_score >= 0.4 else "#64748b")
            nov_color  = "#22c55e" if nov_score >= 0.7 else ("#f59e0b" if nov_score >= 0.4 else "#64748b")
            comb_color = "#22c55e" if comb >= 0.65    else ("#f59e0b" if comb >= 0.45    else "#64748b")

            pid    = h.get("patent_id", "—")
            title  = h.get("title", "Untitled")[:55] or pid
            url    = h.get("url", "#")

            row_html = (
                f"<div style='display:grid;grid-template-columns:50px 1fr 90px 90px 90px 70px;"
                f"gap:0.5rem;padding:0.45rem 0.8rem;border-bottom:1px solid #1e293b;"
                f"font-size:0.8rem;align-items:center;'>"
                f"<span style='color:#6366f1;font-weight:700;'>#{new_rank}</span>"
                f"<span><a href='{url}' target='_blank' style='color:#e2e8f0;text-decoration:none;'>{title}</a>"
                f"<br><span style='font-size:0.68rem;color:#475569;font-family:monospace;'>{pid}</span></span>"
                f"<span style='color:{sem_color};font-weight:600;'>{sem_score:.4f}</span>"
                f"<span style='color:{nov_color};font-weight:600;'>{nov_score:.4f}</span>"
                f"<span style='color:{comb_color};font-weight:600;'>{comb:.4f}</span>"
                f"<span>{delta_html}</span>"
                f"</div>"
            )
            st.markdown(row_html, unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # ── Insight callout — biggest GNN boost ──────────────────────────────
        biggest_boost = max(reranked, key=lambda h: (h.get("faiss_rank", h["rank"]) - h["rank"]))
        boost_delta   = biggest_boost.get("faiss_rank", biggest_boost["rank"]) - biggest_boost["rank"]

        if boost_delta > 0:
            boost_title = biggest_boost.get("title", "Untitled")[:80] or biggest_boost.get("patent_id","")
            boost_sem   = biggest_boost["score"]
            boost_nov   = biggest_boost.get("novelty_score", 0.0)
            if active_mode == "novelty":
                insight_body = (
                    f"<b style='color:#e2e8f0'>\"{boost_title}\"</b> jumped from FAISS rank "
                    f"<b>#{biggest_boost.get('faiss_rank', '?')}</b> → GNN rank "
                    f"<b style='color:#4ade80'>#{biggest_boost['rank']}</b>. "
                    f"Semantic score <b style='color:#22d3ee'>{boost_sem:.4f}</b> is modest, "
                    f"but its novelty score <b style='color:#a78bfa'>{boost_nov:.4f}</b> is high — "
                    f"this patent sits in an <em>underexplored region</em> of the space, "
                    f"making it a strong candidate for a novel angle on your idea."
                )
            else:
                insight_body = (
                    f"<b style='color:#e2e8f0'>\"{boost_title}\"</b> jumped from FAISS rank "
                    f"<b>#{biggest_boost.get('faiss_rank', '?')}</b> → GNN rank "
                    f"<b style='color:#4ade80'>#{biggest_boost['rank']}</b>. "
                    f"Semantic score <b style='color:#22d3ee'>{boost_sem:.4f}</b> is modest, "
                    f"but its graph uniqueness <b style='color:#38bdf8'>{boost_nov:.4f}</b> is high — "
                    f"this patent is <em>structurally isolated</em> from the other retrieved patents "
                    f"in GNN embedding space, indicating a niche technology cluster."
                )

            st.markdown(
                f'<div class="gnn-insight">'
                f'<div class="gnn-insight-title">🎯 Biggest GNN Boost</div>'
                f'<div class="gnn-insight-body">{insight_body}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Section 4: Knowledge Graph Construction ───────────────────────────────
    st.markdown('<div class="section-header">Step 4 — Knowledge Graph Construction (Neo4j)</div>', unsafe_allow_html=True)

    kg_placeholder = st.empty()

    if "kg_stats" not in st.session_state:
        # Show "under construction" card immediately
        kg_placeholder.markdown("""
        <div class="kg-card building">
            <div class="kg-status-title">⏳ KG Under Construction</div>
            <div style="font-size:0.82rem;color:#94a3b8;">
                Writing patent nodes, company nodes, inventor nodes, CPC codes,
                family edges and citation links into Neo4j…
            </div>
        </div>
        """, unsafe_allow_html=True)

        patent_ids = [h["patent_id"] for h in hits]
        with st.spinner("Building knowledge graph in Neo4j…"):
            try:
                stats = _build_kg(patent_ids)
                st.session_state["kg_stats"] = stats
            except Exception as e:
                st.session_state["kg_stats"] = {"error": str(e)}

        st.rerun()

    kg_stats = st.session_state.get("kg_stats", {})

    if "error" in kg_stats:
        kg_placeholder.error(f"KG build failed: {kg_stats['error']}")
    else:
        nodes = kg_stats.get("nodes", {})
        edges = kg_stats.get("edges", {})
        total_nodes = sum(nodes.values())
        total_edges = sum(edges.values())

        stat_html = "".join(
            f'<div class="kg-stat"><div class="kg-stat-val">{v}</div>'
            f'<div class="kg-stat-lbl">{k}</div></div>'
            for k, v in nodes.items()
        ) + "".join(
            f'<div class="kg-stat"><div class="kg-stat-val">{v}</div>'
            f'<div class="kg-stat-lbl">{k}</div></div>'
            for k, v in edges.items()
        )

        kg_placeholder.markdown(f"""
        <div class="kg-card done">
            <div class="kg-status-title">
                ✅ KG Constructed — {total_nodes} nodes · {total_edges} edges
            </div>
            <div style="font-size:0.8rem;color:#86efac;margin-bottom:0.5rem;">
                Subgraph built for {len(hits)} retrieved patents.
                Open <a href="http://localhost:7474" target="_blank"
                style="color:#4ade80;">Neo4j Browser</a> to explore.
            </div>
            <div class="kg-stat-row">{stat_html}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Section 5: KG Expansion ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Step 5 — KG Expanded Patent Set</div>', unsafe_allow_html=True)

    if "kg_expansion" not in st.session_state and "kg_stats" in st.session_state and "error" not in st.session_state.get("kg_stats", {}):
        with st.spinner("Expanding via knowledge graph — finding family members and CPC siblings…"):
            try:
                expansion = _expand_kg([h["patent_id"] for h in hits])
                st.session_state["kg_expansion"] = expansion
            except Exception as e:
                st.session_state["kg_expansion"] = {"error": str(e)}
        st.rerun()

    expansion = st.session_state.get("kg_expansion", {})

    if "error" in expansion:
        st.error(f"KG expansion failed: {expansion['error']}")
    elif not expansion:
        st.info("KG expansion will run after the knowledge graph is built.")
    else:
        family       = expansion.get("family", [])
        cpc_siblings = expansion.get("cpc_siblings", [])
        total_added  = expansion.get("total_added", 0)

        st.markdown(
            f"<div style='font-size:0.88rem;color:#94a3b8;margin-bottom:1rem;'>"
            f"Found <b style='color:#a78bfa'>{len(family)} family members</b> and "
            f"<b style='color:#38bdf8'>{len(cpc_siblings)} CPC siblings</b> "
            f"not in the original FAISS top-{top_k}. "
            f"<b style='color:#e2e8f0'>{total_added} patents added.</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

        if family:
            with st.expander(f"Family Members ({len(family)})", expanded=True):
                st.markdown(
                    "<div class='expansion-header'>"
                    "Same invention filed in other jurisdictions — "
                    "strongest form of prior art."
                    "</div>",
                    unsafe_allow_html=True,
                )
                for p in family:
                    render_expanded_card(p)

        if cpc_siblings:
            with st.expander(f"CPC Technology Siblings ({len(cpc_siblings)})", expanded=True):
                st.markdown(
                    "<div class='expansion-header'>"
                    "Patents sharing a CPC classification code with your top results — "
                    "structurally related prior art FAISS may have missed."
                    "</div>",
                    unsafe_allow_html=True,
                )
                for p in cpc_siblings:
                    render_expanded_card(p)

    st.divider()

    # ── Section 6: Retrieval Insights ─────────────────────────────────────────
    st.markdown('<div class="section-header">Step 6 — Retrieval Insights</div>', unsafe_allow_html=True)

    top_score = hits[0]["score"] if hits else 0.0
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown('<div class="metric-box"><div class="metric-val">58,428</div><div class="metric-lbl">Patents Indexed</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{latency_ms:.0f} ms</div><div class="metric-lbl">Query Latency</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{top_score:.4f}</div><div class="metric-lbl">Top Match Score</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{top_k}</div><div class="metric-lbl">Results Returned</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("**Embedding Model**")
        st.code("all-MiniLM-L6-v2  (384-dim)", language="text")
        st.markdown("**NLP Engine**")
        st.code("Gemini 2.5 Flash + spaCy fallback", language="text")
    with col_info2:
        st.markdown("**Retrieval Method**")
        st.code("FAISS IndexFlatIP + L2 normalization\n(exact cosine similarity)", language="text")
        st.markdown("**Index Type**")
        st.code("Flat exact search (no ANN approximation)", language="text")

    st.divider()

    # ── Section 6: Architecture Flow ──────────────────────────────────────────
    st.markdown('<div class="section-header">Step 6 — System Architecture</div>', unsafe_allow_html=True)

    steps = [
        ("User Idea",        "Free-text input"),
        ("NLP Processing",   "Gemini + spaCy"),
        ("Embedding",        "all-MiniLM-L6-v2"),
        ("FAISS Search",     "58k patent index"),
        ("Patent Discovery", "Top-K results"),
        ("KG Expansion",     "Neo4j · Coming soon"),
        ("Novelty Score",    "GNN · Coming soon"),
    ]

    cols = st.columns(len(steps) * 2 - 1)
    for i, (label, desc) in enumerate(steps):
        col_idx = i * 2
        with cols[col_idx]:
            st.markdown(f"""
            <div class="pipe-step">
                <div class="pipe-label">{label}</div>
                <div class="pipe-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)
        if i < len(steps) - 1:
            with cols[col_idx + 1]:
                st.markdown('<div class="pipe-arrow">→</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#334155;font-size:0.78rem'>"
    "Graph-Enhanced Patent Intelligence Platform &nbsp;·&nbsp; "
    "Semantic Retrieval Module &nbsp;·&nbsp; Demo Build May 2026"
    "</div>",
    unsafe_allow_html=True,
)
