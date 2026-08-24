import re
from io import StringIO

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Self-Healing Materials Discovery", page_icon="🧪", layout="wide")

SHEET_ID = "1bc3GNT1deeJgbiZyU-uCnf1vyPOpBmgoQHG_s24lKiU"
SHEET_GID = "1184237847"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# The spreadsheet is the source of truth. These aliases map the research dataset's
# exact column names into shorter UI/internal names.
ALIASES = {
    "id": "ID", "material/polymer name": "Material", "material name": "Material", "material": "Material",
    "polymer family": "Polymer family", "healing mechanism": "Mechanism", "mechanism": "Mechanism",
    "external stimulus required": "Stimulus", "stimulus": "Stimulus",
    "healing temp (°c)": "Healing temperature", "healing temperature": "Healing temperature", "temperature": "Healing temperature",
    "healing temp notes": "Healing temperature notes", "healing time (hrs)": "Healing time", "healing time": "Healing time",
    "healing efficiency (%)": "Healing efficiency", "healing efficiency": "Healing efficiency", "efficiency": "Healing efficiency",
    "efficiency measured property": "Efficiency property", "tensile strength (mpa)": "Tensile strength", "elongation at break (%)": "Elongation",
    "flexibility category": "Flexibility", "application area": "Application", "main advantages": "Advantages",
    "main limitations/trade-offs": "Limitations", "supporting evidence": "Evidence", "paper title": "Paper title",
    "authors": "Authors", "year": "Year", "journal": "Journal", "doi/link": "DOI", "data collector": "Data collector",
    "date collected": "Date collected", "verification status": "Verification status", "notes/uncertainty flags": "Notes",
}

CORE_COLUMNS = ["ID", "Material", "Polymer family", "Mechanism", "Stimulus", "Healing temperature", "Healing temperature notes",
                "Healing time", "Healing efficiency", "Efficiency property", "Tensile strength", "Elongation", "Flexibility",
                "Application", "Advantages", "Limitations", "Evidence", "Paper title", "Authors", "Year", "Journal", "DOI",
                "Data collector", "Date collected", "Verification status", "Notes"]


def clean_col(c):
    return re.sub(r"\s+", " ", str(c).strip().lower())


def numeric(v):
    if pd.isna(v):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(v).replace(",", ""))
    return float(m.group()) if m else None


def normalize_dataset(raw):
    df = raw.copy()
    df.columns = [ALIASES.get(clean_col(c), str(c).strip()) for c in df.columns]
    for col in CORE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[CORE_COLUMNS].copy()
    df = df.fillna("")
    df["Material"] = df["Material"].astype(str).str.strip()
    df = df[df["Material"] != ""].copy()
    df["Efficiency value"] = df["Healing efficiency"].map(numeric)
    df["Temperature value"] = df["Healing temperature"].map(numeric)
    df["Time value"] = df["Healing time"].map(numeric)
    return df.reset_index(drop=True)


def load_dataset(force=False):
    if not force and "materials_df" in st.session_state:
        return st.session_state.materials_df, st.session_state.dataset_source
    try:
        import requests
        r = requests.get(SHEET_CSV_URL, timeout=12)
        r.raise_for_status()
        df = normalize_dataset(pd.read_csv(StringIO(r.text)))
        if df.empty:
            raise ValueError("The research spreadsheet contains no material records.")
        st.session_state.materials_df = df
        st.session_state.dataset_source = "Research spreadsheet"
    except Exception as exc:
        st.session_state.materials_df = pd.DataFrame(columns=CORE_COLUMNS + ["Efficiency value", "Temperature value", "Time value"])
        st.session_state.dataset_source = f"Spreadsheet unavailable: {exc}"
    return st.session_state.materials_df, st.session_state.dataset_source


def extract_requirements(query):
    q = query.lower()
    req = {"max_temp": None, "min_eff": None, "max_time": None, "flexible": False,
           "stimulus": None, "application": None, "terms": []}
    m = re.search(r"(?:below|under|less than|at most|max(?:imum)?(?: of)?)\s*(\d+(?:\.\d+)?)\s*°?\s*c", q)
    if m: req["max_temp"] = float(m.group(1))
    m = re.search(r"(?:at least|minimum of|min|over|above|greater than)\s*(\d+(?:\.\d+)?)\s*%", q)
    if m: req["min_eff"] = float(m.group(1))
    m = re.search(r"(?:within|under|less than|in)\s*(\d+(?:\.\d+)?)\s*(hour|hours|h|day|days)", q)
    if m: req["max_time"] = float(m.group(1)) * (24 if m.group(2).startswith("day") else 1)
    req["flexible"] = any(x in q for x in ["flexible", "stretchable", "elastic", "high flexibility"])
    for s in ["room temperature", "autonomous", "light", "uv", "water", "pressure", "heat", "thermal"]:
        if s in q:
            req["stimulus"] = "Autonomous" if s == "room temperature" else s
            break
    for a in ["wearable electronics", "wearable sensors", "electronics", "soft robotics", "coatings", "biomedical", "sensors", "robotics", "energy", "adhesives"]:
        if a in q:
            req["application"] = a
            break
    stop = {"need", "want", "looking", "material", "polymer", "self", "healing", "that", "with", "and", "the", "for", "from", "below", "under", "least"}
    req["terms"] = [w for w in re.findall(r"[a-z]{4,}", q) if w not in stop]
    return req


def rank_materials(df, req):
    ranked = []
    for _, row in df.iterrows():
        score, reasons = 0.0, []
        temp = row["Temperature value"]
        eff = row["Efficiency value"]
        time = row["Time value"]
        text = " ".join(str(v) for v in row.values).lower()
        if req["max_temp"] is not None and temp is not None:
            if temp <= req["max_temp"]:
                score += 35; reasons.append(f"healing temperature is {row['Healing temperature']}°C, within your target")
            else:
                score -= 15; reasons.append(f"healing temperature ({row['Healing temperature']}°C) is above your target")
        if req["min_eff"] is not None and eff is not None:
            if eff >= req["min_eff"]:
                score += 30; reasons.append(f"reported recovery is {eff:g}%, meeting your target")
            else:
                score -= 15
        if req["max_time"] is not None and time is not None:
            if time <= req["max_time"]:
                score += 15; reasons.append(f"reported healing time is {row['Healing time']} h")
            else:
                score -= 5
        if req["flexible"] and any(x in str(row["Flexibility"]).lower() for x in ["high", "flex", "elastic", "stretch"]):
            score += 10; reasons.append("recorded as flexible/stretchable")
        if req["stimulus"] and req["stimulus"].lower() in str(row["Stimulus"]).lower():
            score += 7; reasons.append(f"stimulus matches: {row['Stimulus']}")
        if req["application"] and req["application"].lower() in text:
            score += 8; reasons.append(f"application matches: {row['Application']}")
        hits = [t for t in req["terms"] if t in text]
        score += min(10, len(hits) * 2)
        if hits: reasons.append("keyword matches: " + ", ".join(hits[:4]))
        if not reasons: reasons.append("general relevance from the curated research record")
        ranked.append((max(0, min(100, score)), reasons))
    result = df.copy()
    result["Match score"] = [x[0] for x in ranked]
    result["Match reasons"] = [x[1] for x in ranked]
    return result.sort_values("Match score", ascending=False).reset_index(drop=True)

materials, dataset_source = load_dataset()

st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:2rem}.hero{padding:1.5rem;border:1px solid rgba(128,128,128,.22);border-radius:20px;margin-bottom:1.2rem;background:linear-gradient(135deg,rgba(64,120,180,.10),rgba(110,80,180,.06))}.eyebrow{font-size:.78rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.7}.score{font-size:1.8rem;font-weight:800}.muted{opacity:.7;font-size:.9rem}.pill{display:inline-block;padding:.28rem .6rem;border-radius:999px;border:1px solid rgba(128,128,128,.25);margin:.15rem;font-size:.8rem}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🧪 Materials Lab")
    page = st.radio("Workspace", ["Discover", "Compare", "Dataset", "About"], label_visibility="collapsed")
    st.divider()
    st.caption("Connected research dataset")
    st.metric("Material systems", len(materials))
    st.caption(f"Source: {dataset_source}")
    if st.button("↻ Refresh dataset", use_container_width=True):
        load_dataset(True); st.rerun()
    st.divider()
    st.caption("Evidence-first")
    st.caption("The app ranks only values present in the research dataset. Missing values are shown as Not reported.")

if page == "Discover":
    st.markdown('<div class="hero"><div class="eyebrow">AI-assisted literature discovery</div><h1>Find self-healing materials for your requirements</h1><p>Describe the material you need in natural language. The app extracts constraints and ranks the paper-backed records in your research dataset.</p></div>', unsafe_allow_html=True)
    query = st.text_area("What material are you looking for?", placeholder="Example: I need a flexible self-healing polymer that heals below 60°C and recovers at least 80% of its strength.", height=120)
    examples = ["Flexible self-healing polymer that heals below 60°C and recovers at least 80% of strength", "Room-temperature self-healing material for wearable sensors", "Self-healing material for soft robotics with high recovery"]
    example = st.selectbox("Example searches", ["Choose an example…"] + examples)
    if example != "Choose an example…" and not query: query = example
    if st.button("🔍 Find best matches", type="primary", use_container_width=True):
        if not query.strip(): st.warning("Enter a material requirement first.")
        elif materials.empty: st.error("The research dataset could not be loaded. Check that the Google Sheet is published and accessible.")
        else:
            req = extract_requirements(query)
            st.session_state.results = rank_materials(materials, req)
            st.session_state.req = req
    if "results" in st.session_state:
        req, results = st.session_state.req, st.session_state.results
        st.markdown("### Interpreted requirements")
        chips=[]
        if req["max_temp"] is not None: chips.append(f"Healing ≤ {req['max_temp']:g}°C")
        if req["min_eff"] is not None: chips.append(f"Recovery ≥ {req['min_eff']:g}%")
        if req["max_time"] is not None: chips.append(f"Healing ≤ {req['max_time']:g} h")
        if req["flexible"]: chips.append("Flexible")
        if req["stimulus"]: chips.append(f"Stimulus: {req['stimulus']}")
        if req["application"]: chips.append(f"Application: {req['application']}")
        if not chips: chips.append("Keyword-based relevance")
        st.markdown(" ".join(f'<span class="pill">{c}</span>' for c in chips), unsafe_allow_html=True)
        st.markdown("### Ranked candidates")
        for _, m in results.iterrows():
            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(f"#### {m['Material']}")
                    st.caption(f"{m['Polymer family']} · {m['Mechanism']} · {m['ID']}")
                with right:
                    st.markdown(f'<div class="score">{m["Match score"]:.0f}<span class="muted">/100</span></div><div class="muted">match score</div>', unsafe_allow_html=True)
                a,b,c,d = st.columns(4)
                a.metric("Healing", str(m["Healing temperature"]) if m["Healing temperature"] != "" else "Not reported")
                b.metric("Recovery", f"{m['Healing efficiency']}%" if m["Healing efficiency"] != "" else "Not reported")
                c.metric("Healing time", str(m["Healing time"]) + " h" if m["Healing time"] != "" else "Not reported")
                d.metric("Tensile strength", f"{m['Tensile strength']} MPa" if m["Tensile strength"] != "" else "Not reported")
                st.write(f"**Stimulus:** {m['Stimulus'] or 'Not reported'} · **Application:** {m['Application'] or 'Not reported'} · **Flexibility:** {m['Flexibility'] or 'Not reported'}")
                st.markdown("**Why this matches**")
                for reason in m["Match reasons"][:4]: st.write("✓ " + reason)
                st.markdown(f"**Trade-off:** {m['Limitations'] or 'Not reported'}")
                with st.expander("📚 Paper evidence & provenance"):
                    st.write(f"**Paper:** {m['Paper title'] or 'Not reported'}")
                    st.write(f"**Authors:** {m['Authors'] or 'Not reported'} · **Year:** {m['Year'] or 'Not reported'} · **Journal:** {m['Journal'] or 'Not reported'}")
                    st.write(f"**Efficiency measured:** {m['Efficiency property'] or 'Not reported'}")
                    st.write(f"**Evidence:** {m['Evidence'] or 'Not reported'}")
                    st.write(f"**Verification:** {m['Verification status'] or 'Not reported'}")
                    if m["DOI"]:
                        doi = str(m["DOI"]).strip(); url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                        st.markdown(f"[Open paper / DOI]({url})")
                    if m["Notes"]: st.caption("Uncertainty note: " + str(m["Notes"]))

elif page == "Compare":
    st.markdown('<div class="hero"><div class="eyebrow">Research workspace</div><h1>Compare material systems</h1><p>Compare up to four records using the actual fields from the research dataset.</p></div>', unsafe_allow_html=True)
    options = materials["Material"].tolist() if not materials.empty else []
    selected = st.multiselect("Select materials", options, max_selections=4)
    if selected:
        fields = ["ID","Polymer family","Mechanism","Stimulus","Healing temperature","Healing time","Healing efficiency","Efficiency property","Tensile strength","Elongation","Flexibility","Application","Advantages","Limitations","Paper title","Year","Journal","Verification status"]
        comp = materials[materials["Material"].isin(selected)].set_index("Material").T
        st.dataframe(comp.loc[[f for f in fields if f in comp.index]], use_container_width=True, height=650)

elif page == "Dataset":
    st.markdown('<div class="hero"><div class="eyebrow">Curated literature database</div><h1>Explore the full material dataset</h1><p>This view exposes the research fields used by the discovery and comparison workflows.</p></div>', unsafe_allow_html=True)
    if materials.empty:
        st.error("No records loaded from the research spreadsheet.")
    else:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Records", len(materials)); c2.metric("Polymer families", materials["Polymer family"].replace("", pd.NA).nunique()); c3.metric("Applications", materials["Application"].replace("", pd.NA).nunique()); c4.metric("Paper sources", materials["Paper title"].replace("", pd.NA).nunique())
        search = st.text_input("Search all dataset fields", placeholder="PDMS, disulfide, 60°C, wearable, polyurethane...")
        view = materials.copy()
        if search:
            mask = view.apply(lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1)
            view = view[mask]
        st.dataframe(view[CORE_COLUMNS], use_container_width=True, height=680)
        st.caption("Source of truth: the connected research spreadsheet. Scientific claims should be checked against the original publication before experimental use.")

else:
    st.markdown('<div class="hero"><div class="eyebrow">Project methodology</div><h1>About the platform</h1><p>An evidence-first interface for discovering and comparing self-healing polymer systems from published research.</p></div>', unsafe_allow_html=True)
    st.markdown("""
    ### Data pipeline
    **Research spreadsheet → normalization → requirement extraction → transparent ranking → evidence-backed result cards.**

    ### Hallucination controls
    - Material properties are read from the curated dataset rather than generated by the model.
    - Missing values remain **Not reported**.
    - Every candidate exposes paper title, authors, year, journal, DOI/link, supporting evidence and verification status when available.
    - Match score is a **relevance score**, not a prediction of experimental success.

    ### Dataset fields used
    Material/polymer name, polymer family, healing mechanism, stimulus, healing temperature/time, healing efficiency and measured property, tensile strength, elongation, flexibility, application, advantages, limitations, supporting evidence, paper metadata, DOI/link, verification status and uncertainty notes.
    """)

st.divider()
st.caption("Self-Healing Materials Discovery · Evidence-first research prototype")
