import re
from io import StringIO

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Self-Healing Materials Discovery", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")

DEMO_MATERIALS = [
    {"Material":"Dynamic polyurethane network","Polymer family":"Polyurethane","Mechanism":"Dynamic covalent bonds","Healing temperature":"50°C","Healing time":"2 h","Healing efficiency":"85% tensile strength","Flexibility":"High","Stimulus":"Heat","Application":"Flexible electronics","Advantages":"Good flexibility and repeatable healing","Limitations":"Requires moderate heating","Source":"Prototype record","DOI":"","Evidence":"Prototype/demo record; replace with paper evidence during curation."},
    {"Material":"Hydrogen-bonded elastomer","Polymer family":"Elastomer","Mechanism":"Reversible hydrogen bonding","Healing temperature":"Room temperature","Healing time":"24 h","Healing efficiency":"80% tensile strength","Flexibility":"Very high","Stimulus":"Autonomous","Application":"Wearable sensors","Advantages":"Highly flexible and autonomous healing","Limitations":"Longer healing time","Source":"Prototype record","DOI":"","Evidence":"Prototype/demo record; replace with paper evidence during curation."},
    {"Material":"Disulfide-crosslinked polymer","Polymer family":"Crosslinked polymer","Mechanism":"Disulfide exchange","Healing temperature":"60°C","Healing time":"1 h","Healing efficiency":"90% tensile strength","Flexibility":"High","Stimulus":"Heat","Application":"Soft robotics","Advantages":"High recovery and repeatability","Limitations":"Performance depends on network chemistry","Source":"Prototype record","DOI":"","Evidence":"Prototype/demo record; replace with paper evidence during curation."},
]

SHEET_ID = "1bc3GNT1deeJgbiZyU-uCnf1vyPOpBmgoQHG_s24lKiU"
SHEET_GID = "1184237847"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
ALIASES = {"material":"Material","material name":"Material","polymer":"Polymer family","polymer family":"Polymer family","mechanism":"Mechanism","healing mechanism":"Mechanism","healing temperature":"Healing temperature","temperature":"Healing temperature","healing temp":"Healing temperature","healing time":"Healing time","time":"Healing time","healing efficiency":"Healing efficiency","efficiency":"Healing efficiency","flexibility":"Flexibility","stretchability":"Flexibility","stimulus":"Stimulus","external stimulus":"Stimulus","application":"Application","applications":"Application","advantages":"Advantages","benefits":"Advantages","limitations":"Limitations","trade-offs":"Limitations","source":"Source","paper":"Source","paper title":"Source","doi":"DOI","evidence":"Evidence","supporting evidence":"Evidence"}
COLUMNS = ["Material","Polymer family","Mechanism","Healing temperature","Healing time","Healing efficiency","Flexibility","Stimulus","Application","Advantages","Limitations","Source","DOI","Evidence"]


def parse_percent(v):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(v))
    return float(m.group(1)) if m else None


def normalize_dataset(raw):
    df = raw.copy()
    df = df.rename(columns={c: ALIASES.get(re.sub(r"\s+", " ", str(c).strip().lower()), str(c).strip()) for c in df.columns})
    for c in COLUMNS:
        if c not in df.columns: df[c] = ""
    df["Material"] = df["Material"].fillna("").astype(str).str.strip()
    df = df[df["Material"] != ""].copy()
    df["Efficiency value"] = df["Healing efficiency"].map(parse_percent)
    return df[COLUMNS + ["Efficiency value"]].reset_index(drop=True)


def load_dataset(force=False):
    if not force and "materials_df" in st.session_state: return st.session_state.materials_df, st.session_state.dataset_source
    try:
        import requests
        r = requests.get(SHEET_CSV_URL, timeout=8)
        r.raise_for_status()
        df = normalize_dataset(pd.read_csv(StringIO(r.text)))
        if df.empty: raise ValueError("empty sheet")
        st.session_state.materials_df, st.session_state.dataset_source = df, "Google Sheet"
    except Exception:
        st.session_state.materials_df, st.session_state.dataset_source = normalize_dataset(pd.DataFrame(DEMO_MATERIALS)), "Prototype fallback"
    return st.session_state.materials_df, st.session_state.dataset_source


def number(v):
    m = re.search(r"(\d+(?:\.\d+)?)", str(v))
    return float(m.group(1)) if m else None


def temp(v):
    s = str(v).lower()
    return 25.0 if "room" in s or "ambient" in s else number(s)


def hours(v):
    n = number(v)
    return n * 24 if n is not None and "day" in str(v).lower() else n


def extract_requirements(q):
    q = q.lower()
    req = {"max_temp":None,"min_eff":None,"max_time":None,"flex":False,"stimulus":None,"application":None,"terms":[]}
    m = re.search(r"(?:below|under|less than|at most|max(?:imum)?(?: of)?)\s*(\d+(?:\.\d+)?)\s*°?\s*c", q)
    if m: req["max_temp"] = float(m.group(1))
    m = re.search(r"(?:at least|minimum of|min|over|above|greater than)\s*(\d+(?:\.\d+)?)\s*%", q)
    if m: req["min_eff"] = float(m.group(1))
    m = re.search(r"(?:within|under|less than|in)\s*(\d+(?:\.\d+)?)\s*(hour|hours|h|day|days)", q)
    if m: req["max_time"] = float(m.group(1)) * (24 if m.group(2).startswith("day") else 1)
    req["flex"] = any(x in q for x in ["flexible","stretchable","elastic","very high flexibility","high flexibility"])
    for s in ["light","uv","water","pressure","heat","thermal","autonomous","room temperature"]:
        if s in q: req["stimulus"] = "Autonomous" if s == "room temperature" else s; break
    for a in ["wearable electronics","wearable sensors","electronics","soft robotics","coatings","biomedical","sensors","robotics","energy","adhesives"]:
        if a in q: req["application"] = a; break
    stop = {"need","want","looking","material","polymer","self","healing","that","with","and","the","for","from","below","under","least"}
    req["terms"] = [w for w in re.findall(r"[a-z]{4,}", q) if w not in stop]
    return req


def rank(df, req):
    out=[]
    for _, row in df.iterrows():
        score=0.0; reasons=[]; t=temp(row["Healing temperature"]); e=row["Efficiency value"]; h=hours(row["Healing time"]); text=" ".join(map(str,row.values)).lower()
        if req["max_temp"] is not None:
            if t is not None and t <= req["max_temp"]: score+=35; reasons.append(f"heals at {row['Healing temperature']}, within your ≤{req['max_temp']:g}°C limit")
            elif t is not None: score-=15; reasons.append(f"healing temperature ({row['Healing temperature']}) exceeds your target")
        if req["min_eff"] is not None:
            if e is not None and e >= req["min_eff"]: score+=30; reasons.append(f"reports {e:g}% recovery, meeting your ≥{req['min_eff']:g}% target")
            elif e is not None: score-=15
        if req["max_time"] is not None and h is not None:
            score += 15 if h <= req["max_time"] else -5
            if h <= req["max_time"]: reasons.append(f"reported healing time is {row['Healing time']}")
        if req["flex"] and ("high" in str(row["Flexibility"]).lower() or "flex" in text or "stretch" in text): score+=10; reasons.append("reported as flexible/high-flexibility")
        if req["stimulus"] and req["stimulus"].lower() in str(row["Stimulus"]).lower(): score+=7; reasons.append(f"uses {row['Stimulus']} as the healing stimulus")
        if req["application"] and req["application"].lower() in text: score+=8; reasons.append(f"application aligns with {row['Application']}")
        hits=[x for x in req["terms"] if x in text]; score+=min(10,len(hits)*2)
        if hits: reasons.append("matches keywords: "+", ".join(hits[:4]))
        if not reasons: reasons=["general relevance based on the material record"]
        out.append((score,reasons))
    result=df.copy(); result["Match score"]=[max(0,min(100,s)) for s,_ in out]; result["Match reasons"]=[r for _,r in out]
    return result.sort_values("Match score",ascending=False).reset_index(drop=True)

materials, dataset_source = load_dataset()

st.markdown("""<style>.block-container{max-width:1400px;padding-top:2rem}.hero{padding:1.4rem;border:1px solid rgba(128,128,128,.22);border-radius:18px;margin-bottom:1.2rem;background:linear-gradient(135deg,rgba(64,120,180,.10),rgba(110,80,180,.06))}.eyebrow{font-size:.78rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.7}.score{font-size:1.7rem;font-weight:800}.muted{opacity:.7;font-size:.9rem}.pill{display:inline-block;padding:.25rem .55rem;border-radius:999px;border:1px solid rgba(128,128,128,.25);margin-right:.3rem;font-size:.8rem}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🧪 Materials Lab")
    page=st.radio("Workspace",["Discover","Compare","Dataset","About"],label_visibility="collapsed")
    st.divider(); st.caption("Dataset"); st.write(f"**{len(materials)}** material records"); st.write(f"Source: **{dataset_source}**")
    if st.button("↻ Refresh dataset",use_container_width=True): load_dataset(True); st.rerun()
    st.divider(); st.caption("Evidence-first design"); st.caption("Recommendations use only structured records. Missing scientific values are never guessed.")

if page=="Discover":
    st.markdown('<div class="hero"><div class="eyebrow">AI-assisted literature discovery</div><h1>Find self-healing materials for your requirements</h1><p>Describe the material you need in plain language. Requirements are extracted into measurable constraints, then candidate records are ranked with transparent reasons.</p></div>',unsafe_allow_html=True)
    examples=["Flexible self-healing polymer that heals below 60°C and recovers at least 80% of strength","Room-temperature self-healing material for wearable sensors","Heat-healable polymer for soft robotics with fast recovery"]
    query=st.text_area("Material requirements",placeholder="Example: I need a flexible self-healing polymer that can heal below 60°C and recover at least 80% of its strength.",height=120)
    example=st.selectbox("Or start from an example",["Choose an example…"]+examples)
    if example!="Choose an example…" and not query: query=example
    if st.button("🔍 Find best matches",type="primary",use_container_width=True):
        if not query.strip(): st.warning("Describe at least one material requirement first.")
        else:
            st.session_state.last_query=query; st.session_state.last_requirements=extract_requirements(query); st.session_state.last_results=rank(materials,st.session_state.last_requirements)
    if "last_results" in st.session_state:
        req=st.session_state.last_requirements; ranked=st.session_state.last_results
        st.markdown("### Interpreted requirements")
        chips=[]
        if req["max_temp"] is not None: chips.append(f"Healing ≤ {req['max_temp']:g}°C")
        if req["min_eff"] is not None: chips.append(f"Recovery ≥ {req['min_eff']:g}%")
        if req["max_time"] is not None: chips.append(f"Healing ≤ {req['max_time']:g} h")
        if req["flex"]: chips.append("High flexibility")
        if req["stimulus"]: chips.append(f"Stimulus: {req['stimulus']}")
        if req["application"]: chips.append(f"Application: {req['application']}")
        if not chips: chips=["No hard numeric constraint detected — ranking uses keyword matches"]
        st.markdown(" ".join(f'<span class="pill">{c}</span>' for c in chips),unsafe_allow_html=True)
        st.markdown("### Ranked candidates"); st.caption(f"Showing {len(ranked)} records. Scores indicate relevance, not scientific certainty.")
        for _,m in ranked.iterrows():
            with st.container(border=True):
                left,right=st.columns([5,1])
                with left: st.markdown(f"#### {m['Material']}"); st.caption(f"{m['Polymer family']} · {m['Mechanism']}")
                with right: st.markdown(f'<div class="score">{m["Match score"]:.0f}<span class="muted">/100</span></div><div class="muted">match score</div>',unsafe_allow_html=True)
                a,b,c,d=st.columns(4); a.metric("Healing",m["Healing temperature"] or "Not reported"); b.metric("Recovery",m["Healing efficiency"] or "Not reported"); c.metric("Time",m["Healing time"] or "Not reported"); d.metric("Stimulus",m["Stimulus"] or "Not reported")
                st.write(f"**Application:** {m['Application'] or 'Not reported'} · **Flexibility:** {m['Flexibility'] or 'Not reported'}")
                st.markdown("**Why this matches**")
                for reason in m["Match reasons"][:4]: st.write("✓ "+reason)
                st.markdown(f"**Trade-off:** {m['Limitations'] or 'Not reported'}")
                with st.expander("Evidence & source"):
                    st.write(f"**Source:** {m['Source'] or 'Not reported'}")
                    if m["DOI"]:
                        doi=str(m["DOI"]).strip(); url=doi if doi.startswith("http") else f"https://doi.org/{doi}"; st.markdown(f"[Open DOI]({url})")
                    st.info(m["Evidence"] or "No supporting evidence has been entered for this record.")
else:
    st.markdown(f'<div class="hero"><div class="eyebrow">Research workspace</div><h1>{page}</h1><p>Use the curated records as a transparent research aid. Missing values stay missing rather than being guessed.</p></div>',unsafe_allow_html=True)
    if page=="Compare":
        options=materials["Material"].tolist(); selected=st.multiselect("Select materials to compare",options,default=options[:2],max_selections=4)
        if selected:
            comp=materials[materials["Material"].isin(selected)].set_index("Material").T; fields=[c for c in COLUMNS if c!="Material"]; st.dataframe(comp.loc[[f for f in fields if f in comp.index]],use_container_width=True,height=560)
        else: st.info("Select at least one material.")
    elif page=="Dataset":
        st.metric("Material systems",len(materials)); search=st.text_input("Search curated records",placeholder="polyurethane, disulfide, wearable..."); view=materials.copy()
        if search: view=view[view.apply(lambda r: search.lower() in " ".join(map(str,r.values)).lower(),axis=1)]
        st.dataframe(view.drop(columns=["Efficiency value"]),use_container_width=True,height=620); st.caption("Replace prototype records with paper-backed entries and supporting evidence from the research spreadsheet.")
    else:
        st.markdown("""### How the platform works
1. **Natural-language input** — describe desired material behavior.
2. **Requirement extraction** — parse temperature, recovery, time, stimulus, flexibility and application.
3. **Transparent ranking** — score candidates against the extracted requirements.
4. **Evidence layer** — display source, DOI and supporting evidence with each result.
5. **Comparison** — review multiple systems side by side.

### Hallucination controls
- Only fields present in the curated dataset are used for ranking.
- Missing values display as **Not reported** rather than being inferred.
- Match scores are relevance scores, not experimental confidence.
- Scientific claims should be verified against the cited publication before experimental use.

### Current limitation
If the connected spreadsheet is unavailable, the application safely falls back to clearly labelled prototype records. Once the sheet contains paper-backed records, the same interface uses those rows automatically.
""")

st.divider(); st.caption("Self-Healing Materials Discovery · Evidence should always be verified against the original publication.")
