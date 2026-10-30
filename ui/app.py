from pathlib import Path
import streamlit as st
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
RESULTS = BASE / "results"

RUNS = {
    "🌸 VSM · Standard": "vsm-standard",
    "🍓 BM25 · Standard": "bm25-standard",
    "🦩 VSM · English stemming": "vsm-english",
    "💗 BM25 · English stemming": "bm25-english",
}

st.set_page_config(
    page_title="Cranfield IR · Search Studio",
    page_icon="🌸",
    layout="wide",
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #fff7fb 0%, #fff0f6 48%, #fff9fc 100%);
    color: #40263a;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffe2ef, #fff0f6);
    border-right: 1px solid #f7c5dc;
}
h1, h2, h3 { color: #a83268 !important; }
p, label, [data-testid="stMarkdownContainer"] { color: #56364b; }
div[data-testid="stMetric"] {
    background: #ffffffcc;
    border: 1px solid #f4c5da;
    padding: 16px;
    border-radius: 18px;
    box-shadow: 0 5px 18px #a8326810;
}
div.stButton > button {
    background: linear-gradient(90deg, #e85d9e, #bd4c91);
    color: white;
    border: 0;
    border-radius: 14px;
}
[data-testid="stDataFrame"] {
    border: 1px solid #f4c5da;
    border-radius: 14px;
    overflow: hidden;
}
.pill {
    display: inline-block;
    background: #ffe0ee;
    color: #a83268;
    border: 1px solid #f4bdd5;
    border-radius: 999px;
    padding: 5px 12px;
    margin: 2px 4px 8px 0;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)


def read_records(path):
    """Read Cranfield .I / .T / .W records; use record order as the ID."""
    records = []
    current = None
    section = ""

    if not path.exists():
        return records

    def save():
        if current is not None:
            current["title"] = " ".join(current["title"]).strip()
            current["text"] = " ".join(current["text"]).strip()
            records.append(current)

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith(".I"):
            save()
            current = {"title": [], "text": []}
            section = ""
        elif line.startswith(".T"):
            section = "title"
        elif line.startswith(".W"):
            section = "text"
        elif line.startswith("."):
            section = ""
        elif current is not None and section in ("title", "text"):
            current[section].append(line)

    save()
    return records


def read_run(path):
    rows = []
    if not path.exists():
        return rows

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            rows.append({
                "query_id": str(int(parts[0])),
                "document_id": str(int(parts[2])),
                "rank": int(parts[3]),
                "score": float(parts[4]),
            })
        except ValueError:
            continue
    return rows


def read_metrics(path):
    values = {}
    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            values[parts[0].lower()] = float(parts[-1])
        except ValueError:
            continue
    return values


def metric_value(metrics, names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return None


documents = read_records(DATA / "cran.all.1400")
queries = read_records(DATA / "cran.qry")

st.title("🌸 Cranfield Search Studio")
st.caption("A little dashboard for exploring Lucene rankings and evaluation results ✨")
st.markdown(
    '<span class="pill">Cranfield collection</span>'
    '<span class="pill">VSM + BM25</span>'
    '<span class="pill">Standard + English analyzer</span>',
    unsafe_allow_html=True,
)

if not documents or not queries:
    st.error("I couldn’t find the Cranfield data files. Check that the data/ folder is beside ui/.")
    st.stop()

tabs = st.tabs(["🔎 Ranked results", "📊 Evaluation", "🌷 About"])

with tabs[0]:
    st.subheader("Explore a search run")
    left, right = st.columns([1, 1])

    with left:
        run_label = st.selectbox("Choose ranking and analyzer", list(RUNS))
    run_key = RUNS[run_label]
    run_path = RESULTS / f"{run_key}.run"
    rows = read_run(run_path)

    if not rows:
        st.warning(f"No results found at {run_path.relative_to(BASE)}")
    else:
        available_ids = sorted(
            {row["query_id"] for row in rows},
            key=lambda value: int(value),
        )
        with right:
            selected_id = st.selectbox(
                "Choose query number",
                available_ids,
                format_func=lambda value: f"Query {value}",
            )

        query_number = int(selected_id)
        query_text = queries[query_number - 1]["text"] if query_number <= len(queries) else ""
        st.markdown(f"**Query {selected_id}:** {query_text or '(query text unavailable)'}")

        selected_rows = [r for r in rows if r["query_id"] == selected_id]
        selected_rows.sort(key=lambda item: item["rank"])

        st.caption(f"Showing {len(selected_rows)} retrieved documents, ordered by rank.")
        display_rows = []
        for row in selected_rows:
            doc_num = int(row["document_id"])
            doc = documents[doc_num - 1] if 0 < doc_num <= len(documents) else {}
            display_rows.append({
                "Rank": row["rank"],
                "Document": row["document_id"],
                "Score": round(row["score"], 5),
                "Title": doc.get("title", ""),
                "Abstract preview": doc.get("text", "")[:260] + ("…" if len(doc.get("text", "")) > 260 else ""),
            })

        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True,
            hide_index=True,
            height=560,
        )

with tabs[1]:
    st.subheader("Evaluation comparison")
    st.write("These values come from the saved TREC Eval summaries.")

    comparison = []
    for label, key in RUNS.items():
        metrics = read_metrics(RESULTS / "evaluation" / f"{key}.txt")
        comparison.append({
            "Run": label,
            "MAP": metric_value(metrics, ["map"]),
            "Recall": metric_value(metrics, ["recall_50", "recall.50", "recall"]),
        })

    table = pd.DataFrame(comparison)
    st.dataframe(table, use_container_width=True, hide_index=True)

    if not table["MAP"].notna().any() and not table["Recall"].notna().any():
        st.warning("Metric values weren’t recognized. Check the text in results/evaluation/*.txt.")

    st.caption(
        "MAP summarizes precision across the ranked results. Recall shows the fraction "
        "of relevant documents retrieved. The scores depend on matching run query IDs "
        "to the query-order IDs in results/qrels.trec."
    )

    with st.expander("Show the saved evaluation files"):
        for label, key in RUNS.items():
            path = RESULTS / "evaluation" / f"{key}.txt"
            st.markdown(f"**{label}**")
            if path.exists():
                st.code(path.read_text(encoding="utf-8", errors="replace"), language="text")
            else:
                st.info(f"Missing: {path.relative_to(BASE)}")

with tabs[2]:
    st.subheader("What you’re looking at")
    st.write(
        "The ranked-results page displays documents retrieved by your existing "
        "VSM and BM25 runs. The evaluation page compares the four saved TREC Eval "
        "summaries. The query numbers shown here use query order, matching the "
        "query IDs used by your evaluation runs."
    )
    st.write(
        f"Loaded **{len(documents):,} documents** and **{len(queries):,} queries** "
        "from the Cranfield collection."
    )
    st.info(
        "This version explores the saved runs. It doesn’t submit a brand-new typed "
        "query to Lucene; that needs a single-query command in the Java program."
    )
