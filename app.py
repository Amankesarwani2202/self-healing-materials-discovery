import re
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Self-Healing Materials Discovery", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")
DATA_PATH = Path(__file__).parent / "data" / "self_healing_materials.csv"
ALIASES = {
"id":"ID","material/polymer name":"Material","material name":"Material","material":"Material","polymer family":"Polymer family",
"healing mechanism":"Mechanism","mechanism":"Mechanism","external stimulus required":"Stimulus","stimulus":"Stimulus",
"healing temp (°c)":"Healing temperature","healing temperature":"Healing temperature","temperature":"Healing temperature",
"healing temp notes":"Healing temperature notes","healing time (hrs)":"Healing time","healing time":"Healing time",
"healing efficiency (%)":"Healing efficiency","healing efficiency":"Healing efficiency","efficiency":"Healing efficiency",
"efficiency measured property":"Efficiency property","tensile strength (mpa)":"Tensile strength","elongation at break (%)":"Elongation",
"flexibility category":"Flexibility","application area":"Application","main advantages":"Advantages",
"main limitations/trade-offs":"Limitations","supporting evidence":"Evidence","paper title":"Paper title","authors":"Authors",
"year":"Year","journal":"Journal","doi/link":"DOI","data collector":"Data collector","date collected":"Date collected",
"verification status":"Verification status","notes/uncertainty flags":"Notes"}
COLS = ["ID","Material","Polymer family","Mechanism","Stimulus","Healing temperature","Healing temperature notes","Healing time",
"Healing efficiency","Efficiency property","Tensile strength","Elongation","Flexibility","Application","Advantages","Limitations",
"Evidence","Paper title","Authors","Year","Journal","DOI","Data collector","Date collected","Verification status","Notes"]
MECH = {
"metal-ligand coordination":["metal-ligand coordination","metal–ligand coordination","metal ligand coordination","coordination bond","coordination interaction","ligand interaction","ligand interactions","metal coordination","zn2+","fe3+"],
"hydrogen bonding":["hydrogen bond","hydrogen bonding","h-bond"],"disulfide exchange":["disulfide","disulfide exchange"],
"imine/schiff base":["imine","schiff base"],"boronic ester":["boronic ester","boronate"],"diels-alder":["diels-alder","diels alder"],
"transesterification":["transesterification","ester exchange"],"ionic interactions":["ionic interaction","ionic interactions","ion-dipole","ion dipole"],
"π–π stacking":["π–π","pi-pi stacking","pi pi stacking"],"chain interdiffusion":["chain interdiffusion","chain diffusion"],
"dynamic covalent bonds":["dynamic covalent","covalent exchange"]}

def norm(v):
    return re.sub(r"\s+"," ",str(v or "").lower().replace("–","-").replace("—","-")).strip()
def number(v):
    if pd.isna(v) or not str(v).strip(): return None
    m=re.search(r"-?\d+(?:\.\d+)?",str(v).replace(",",""))
    return float(m.group()) if m else None
@st.cache_data(show_spinner=False)
def load_data():
    if not DATA_PATH.exists(): return pd.DataFrame(columns=COLS),"Repository CSV missing"
    raw=pd.read_csv(DATA_PATH,engine="python",quotechar='"',escapechar="\\",on_bad_lines="warn")
    raw.columns=[ALIASES.get(norm(c),str(c).strip()) for c in raw.columns]
    for c in COLS:
        if c not in raw.columns: raw[c]=""
    df=raw[COLS].fillna("").copy()
    df["Material"]=df["Material"].astype(str).str.strip()
    df=df[df["Material"]!=""].copy()
    df["__temp"]=df["Healing temperature"].map(number)
    df["__eff"]=df["Healing efficiency"].map(number)
    df["__time"]=df["Healing time"].map(number)
    return df.reset_index(drop=True),f"Repository dataset · {len(df)} records"

def parse_query(q):
    q=norm(q); out=[]
    mh=[k for k,aliases in MECH.items() if any(norm(a) in q for a in aliases)]
    if mh: out.append({"key":"Mechanism","label":"Healing mechanism","value":mh,"weight":2.0})
    m=re.search(r"(?:below|under|less than|at most|max(?:imum)?(?: of)?)\s*(\d+(?:\.\d+)?)\s*°?\s*c",q)
    if m: out.append({"key":"Temperature","label":"Maximum healing temperature","value":float(m.group(1)),"weight":1.5})
    m=re.search(r"(?:at least|minimum of|min|over|above|greater than)\s*(\d+(?:\.\d+)?)\s*%",q)
    if m: out.append({"key":"Efficiency","label":"Minimum healing efficiency","value":float(m.group(1)),"weight":1.5})
    m=re.search(r"(?:within|under|less than|in)\s*(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|days?)",q)
    if m: out.append({"key":"Time","label":"Maximum healing time","value":float(m.group(1))*(24 if m.group(2).startswith("day") else 1),"weight":1})
    for key,words in {"Flexibility":["flexible","stretchable","elastic","elastomeric"],
    "Stimulus":["autonomous","room temperature","light","uv","water","pressure","mechanical","heat","thermal"],
    "Application":["wearable electronics","wearable sensors","soft robotics","robotics","coatings","biomedical","sensors","electronics","adhesives"]}.items():
        hits=[w for w in words if w in q]
        if hits: out.append({"key":key,"label":key,"value":hits,"weight":1})
    return out

def status(row,c):
    k,t=c["key"],c["value"]
    actual={"Mechanism":row["Mechanism"],"Temperature":row["__temp"],"Efficiency":row["__eff"],"Time":row["__time"],
    "Flexibility":row["Flexibility"],"Stimulus":row["Stimulus"],"Application":row["Application"]}[k]
    if k=="Mechanism":
        if not str(actual).strip(): return "Not reported"
        # Mechanism annotations may be recorded in the notes/evidence fields when
        # the source CSV's normalized mechanism category is broader (for example, "Other").
        s=norm(" ".join(str(row.get(col, "")) for col in ["Mechanism","Notes","Evidence","Advantages"]))
        return "Match" if any(norm(a) in s for x in t for a in MECH[x]) else "No match"
    if k in ("Temperature","Efficiency","Time"):
        if actual is None: return "Not reported"
        ok=actual<=t if k in ("Temperature","Time") else actual>=t
        return "Match" if ok else "No match"
    if not str(actual or "").strip(): return "Not reported"
    s=norm(actual)
    if k=="Flexibility": return "Match" if any(x in s for x in t) or ("high" in s and "flex" in s) else "No match"
    return "Match" if any(norm(x) in s for x in t) else "No match"

def rank(df,criteria,required):
    rows=[]
    for _,r in df.iterrows():
        checks=[(c["label"],status(r,c),c["weight"]) for c in criteria]
        known=[x for x in checks if x[1]!="Not reported"]
        denom=sum(x[2] for x in known)
        score=round(100*sum(x[2] for x in known if x[1]=="Match")/denom) if denom else 0
        failures=[label for label,s,_ in checks if label in required and s=="No match"]
        match_type="Exact match" if checks and all(s=="Match" for _,s,_ in checks) else ("Partial match" if any(s=="Match" for _,s,_ in checks) else "Unverified / no match")
        rows.append((score,checks,failures,match_type,f"{len(known)}/{len(checks)}" if checks else "—"))
    out=df.copy()
    out["Match score"]=[x[0] for x in rows]; out["Checks"]=[x[1] for x in rows]
    out["Required failures"]=[x[2] for x in rows]; out["Match type"]=[x[3] for x in rows]; out["Coverage"]=[x[4] for x in rows]
    if required: out=out[out["Required failures"].map(len)==0]
    return out.sort_values(["Match score","__eff"],ascending=[False,False],na_position="last").reset_index(drop=True)
def shown(v,suffix=""):
    return "Not reported" if v is None or str(v).strip()=="" else f"{v}{suffix}"
def doi_url(v):
    v=str(v or "").strip()
    return (v if v.startswith(("http://","https://")) else "https://doi.org/"+v) if v else None

materials,source=load_data()
st.markdown("""<style>
:root{--navy:#092747;--blue:#0b477b;--teal:#2e7886;--line:#dce5ee;--muted:#64748b}
#MainMenu,footer,[data-testid="stStatusWidget"],[data-testid="stAppDeployButton"],.viewerBadge_container__1QSob,.stAppDeployButton{visibility:hidden}
.block-container{max-width:1600px;padding:1.05rem 1.45rem 2rem}
[data-testid="stSidebar"]{background:#092747}
[data-testid="stSidebar"] *{color:#f4f8fc!important}
[data-testid="stSidebar"] [data-testid="stMetricValue"]{font-size:2rem}
[data-testid="stSidebar"] .stRadio label{padding:.55rem .65rem;border-radius:9px}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#e6eef6}
.brand{display:flex;align-items:center;gap:12px;padding:.15rem 0 .9rem;border-bottom:1px solid var(--line);margin-bottom:1rem}
.brandmark{width:42px;height:42px;border-radius:12px;background:#eaf4fb;color:#0b477b;display:flex;align-items:center;justify-content:center;font-size:1.45rem}
.brandname{font-weight:800;font-size:1.12rem;color:#102c4c}
.brandtag{font-size:.84rem;color:#61738a;border-left:1px solid #cbd5e1;padding-left:15px;margin-left:4px}
.hero{border-radius:18px;padding:1.35rem 1.55rem 1.15rem;background:linear-gradient(112deg,#edf5fc 0%,#e7f2fb 58%,#d8eaf5 100%);border:1px solid #d6e5f1;margin:.45rem 0 1rem}
.hero h1{font-size:2.15rem!important;color:#0a294b;letter-spacing:-.04em;margin:0 0 .25rem}
.hero p{color:#243e5c;margin:0 0 .9rem}
.eyebrow{font-size:.72rem;letter-spacing:.13em;text-transform:uppercase;font-weight:800;color:#27617f;margin-bottom:.3rem}
.criteria-wrap{border:1px solid #dbe5ed;border-radius:13px;padding:.8rem 1rem;background:var(--secondary-background-color);margin:.6rem 0 1rem}
.criteria-chip{display:inline-block;border-radius:30px;padding:.35rem .7rem;margin:.2rem .25rem .1rem 0;background:#e5f5ed;color:#155b3e;font-size:.82rem;font-weight:650}
.panel{border:1px solid #dce5ee;border-radius:14px;padding:.85rem 1rem;background:var(--secondary-background-color);margin-bottom:.55rem}
.material-title{font-size:1.03rem;font-weight:750;color:var(--text-color)}
.material-sub{font-size:.83rem;color:#64748b}
.score{font-size:1.45rem;font-weight:800;color:#0b477b}
.section-kicker{font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;font-weight:800;color:#64748b}
[data-testid="stMetric"]{background:#f7fafc;border:1px solid #e1e9f0;border-radius:11px;padding:.55rem .7rem}
[data-testid="stMetricLabel"]{font-size:.78rem}
.stButton>button[kind="primary"]{background:#0b477b;border-color:#0b477b}
div[data-testid="stTabs"] button{font-weight:650}
@media(max-width:900px){.block-container{padding:.7rem}.hero h1{font-size:1.55rem!important}.brandtag{display:none}}
</style>""",unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🧬 SelfHeal Materials")
    st.caption("RESEARCH DISCOVERY PLATFORM")
    st.divider()
    page=st.radio("Navigation",["🔎  Discover","⚖️  Compare","▤  Materials Database","⬡  How It Works","ⓘ  About"],label_visibility="collapsed")
    st.divider()
    st.markdown("### Research database")
    st.metric("Curated material systems",len(materials))
    st.markdown("✓ Published research")
    st.markdown("✓ Experimentally reported data")
    st.markdown("✓ Polymer-based systems")
    st.divider()
    st.caption(source)
    st.caption("Evidence-led · Literature-backed")

st.markdown('<div class="brand"><div class="brandmark">⬡</div><div class="brandname">SelfHeal Materials</div><div class="brandtag">A Research Platform for Self-Healing Materials Discovery</div><div style="margin-left:auto;color:#52677d;font-size:1.1rem">ⓘ　♧　◎</div></div>',unsafe_allow_html=True)

if page.startswith("🔎"):
    st.markdown('<div class="hero"><div class="eyebrow">Materials discovery workspace</div><h1>Discover Self-Healing Materials</h1><p>Search and compare polymer systems with self-healing properties, backed by published research.</p></div>',unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Describe your ideal material**")
        qcol,bcol=st.columns([5,1.35],vertical_alignment="bottom")
        with qcol:
            query=st.text_input("Search criteria",value=st.session_state.get("query",""),placeholder="e.g., A flexible polymer that heals below 60°C through metal–ligand coordination",label_visibility="collapsed")
        with bcol:
            clicked=st.button("⌕  Find Matching Materials",type="primary",use_container_width=True)
        st.caption("Try an example")
        example_cols=st.columns(4)
        examples=["Low-temperature healing","Hydrogen bonding","Flexible polymer","Disulfide exchange"]
        for col,example in zip(example_cols,examples):
            with col:
                if st.button(example,use_container_width=True):
                    st.session_state["query"]=example
                    st.session_state["criteria"]=parse_query(example)
                    st.session_state["searched"]=True
                    st.session_state["required"]=[]
                    st.rerun()
    if clicked:
        st.session_state["query"]=query
        st.session_state["criteria"]=parse_query(query)
        st.session_state["searched"]=True
        st.session_state["required"]=[]
        st.session_state.pop("must_have",None)
    if st.session_state.get("searched"):
        criteria=st.session_state.get("criteria",[])
        if not criteria:
            st.warning("We couldn't identify a supported structured criterion in that query. Try a healing mechanism, temperature limit, healing-efficiency threshold, healing time, flexibility, stimulus, or application.")
        else:
            st.markdown('<div class="criteria-wrap"><b>◎　Your Search Criteria</b><br/>',unsafe_allow_html=True)
            chips=[]
            for c in criteria:
                val=", ".join(c["value"]) if isinstance(c["value"],list) else str(c["value"])
                chips.append(f'<span class="criteria-chip">✓　{c["label"]}: {val}</span>')
            st.markdown("".join(chips)+"</div>",unsafe_allow_html=True)
            required=st.multiselect("Essential requirements · reported mismatches are excluded; unknown values remain visible", [c["label"] for c in criteria],default=st.session_state.get("required",[]),key="must_have")
            st.session_state["required"]=required
            results=rank(materials,criteria,required) if not materials.empty else materials.copy()
            heading_col,sort_col=st.columns([3,1.2],vertical_alignment="center")
            with heading_col: st.markdown(f"### ▤　Matching Materials <span style='font-size:.85rem;color:#64748b;font-weight:400'>({len(results)} results)</span>",unsafe_allow_html=True)
            with sort_col:
                sort=st.selectbox("Sort by",["Match Score (High to Low)","Healing Efficiency","Healing Temperature","Material Name"],label_visibility="collapsed")
            if not results.empty:
                if sort=="Healing Efficiency": results=results.sort_values("__eff",ascending=False,na_position="last")
                elif sort=="Healing Temperature": results=results.sort_values("__temp",ascending=True,na_position="last")
                elif sort=="Material Name": results=results.sort_values("Material")
            if results.empty:
                st.info("No materials meet all selected essential criteria. Remove an essential requirement to explore partial matches.")
            else:
                per_page=20
                pages=max(1,(len(results)+per_page-1)//per_page)
                page_no=st.number_input("Results page",min_value=1,max_value=pages,value=1,step=1,horizontal=True)
                batch=results.iloc[(page_no-1)*per_page:page_no*per_page]
                list_col,detail_col=st.columns([1.02,1.08],gap="medium")
                with list_col:
                    st.markdown("**Ranked materials**")
                    labels=[f"{i+1+(page_no-1)*per_page}.  {r['Material']}  ·  {r['Match score']}/100" for i,(_,r) in enumerate(batch.iterrows())]
                    selected_label=st.radio("Choose a material",labels,label_visibility="collapsed",key=f"material_select_{page_no}")
                    selected=batch.iloc[labels.index(selected_label)]
                    st.caption(f"Showing {(page_no-1)*per_page+1}–{min(page_no*per_page,len(results))} of {len(results)} matching records")
                with detail_col:
                    st.markdown(f"### {selected['Material']}")
                    score_col,match_col=st.columns([1,1])
                    score_col.metric("Match score",f"{selected['Match score']}/100")
                    match_col.metric("Match classification",selected["Match type"])
                    overview,evidence,mechanism,comparison=st.tabs(["Overview","Evidence & Source","Mechanism","Comparison"])
                    with overview:
                        m1,m2,m3=st.columns(3)
                        m1.metric("Healing temperature",shown(selected["Healing temperature"]," °C"))
                        m2.metric("Healing efficiency",shown(selected["Healing efficiency"],"%"))
                        m3.metric("Healing time",shown(selected["Healing time"]," h"))
                        st.markdown("**Key takeaways**")
                        st.write(f"• Mechanism: {shown(selected['Mechanism'])}")
                        st.write(f"• Stimulus: {shown(selected['Stimulus'])}")
                        st.write(f"• Flexibility: {shown(selected['Flexibility'])}")
                        st.write(f"• Application: {shown(selected['Application'])}")
                        st.markdown("**Requirement assessment**")
                        for label,s,_ in selected["Checks"]:
                            icon="✓" if s=="Match" else ("—" if s=="Not reported" else "✕")
                            st.write(f"{icon} **{label}:** {s}")
                        st.caption(f"Criteria with reported values: {selected['Coverage']}")
                    with evidence:
                        st.markdown("**Research publication**")
                        st.write("**Paper title:** "+shown(selected["Paper title"]))
                        st.write("**Authors:** "+shown(selected["Authors"]))
                        st.write("**Year:** "+shown(selected["Year"]))
                        st.write("**Journal:** "+shown(selected["Journal"]))
                        url=doi_url(selected["DOI"])
                        if url: st.markdown(f"[View publication / DOI ↗]({url})")
                        else: st.write("**DOI:** Not reported")
                        st.markdown("**Experimental evidence**")
                        st.write(shown(selected["Evidence"]))
                        st.write("**Verification status:** "+shown(selected["Verification status"]))
                        if selected["Notes"]: st.caption("Research notes: "+str(selected["Notes"]))
                    with mechanism:
                        st.write("**Reported healing mechanism**")
                        st.write(shown(selected["Mechanism"]))
                        st.write("**Healing stimulus:** "+shown(selected["Stimulus"]))
                        st.write("**Mechanism-related advantages:** "+shown(selected["Advantages"]))
                        st.write("**Reported limitations:** "+shown(selected["Limitations"]))
                    with comparison:
                        st.write("**Material properties**")
                        for label,value in [("Polymer family",selected["Polymer family"]),("Tensile strength",selected["Tensile strength"]),("Elongation",selected["Elongation"]),("Flexibility",selected["Flexibility"]),("Healing temperature notes",selected["Healing temperature notes"]),("Efficiency measured property",selected["Efficiency property"])]:
                            st.write(f"**{label}:** {shown(value)}")
                with st.expander("How match scores are calculated"):
                    st.write("The score reflects agreement with criteria recognized in your query, not predicted material performance. Reported matches earn the criterion weight; reported mismatches earn zero. Unreported values are excluded from the denominator and shown as Not reported. Essential criteria exclude records only when the source reports a mismatch.")
                    st.write("Exact match means all requested criteria have reported matching values. Partial match means at least one criterion matches but one or more do not. Unknown values are separately identified.")
    else:
        st.markdown("### Start exploring the literature")
        st.caption("Enter a research requirement above or choose an example query. Search results are ranked against the criteria recognized from your description.")

elif page.startswith("⚖️"):
    st.markdown('<div class="eyebrow">Research workspace</div><h1>Compare Materials</h1><p class="sub">Compare reported properties across up to four material systems.</p>',unsafe_allow_html=True)
    names=materials["Material"].tolist() if not materials.empty else []
    selected_names=st.multiselect("Select materials to compare",names,max_selections=4)
    if selected_names:
        fields=["ID","Polymer family","Mechanism","Stimulus","Healing temperature","Healing temperature notes","Healing time","Healing efficiency","Efficiency property","Tensile strength","Elongation","Flexibility","Application","Advantages","Limitations","Paper title","Authors","Year","Journal","DOI","Evidence","Verification status"]
        view=materials[materials["Material"].isin(selected_names)].set_index("Material")[fields].T
        st.dataframe(view.replace("", "Not reported").fillna("Not reported"),use_container_width=True,height=680)
    else: st.info("Choose two or more materials to compare their reported properties side by side.")

elif page.startswith("▤"):
    st.markdown('<div class="eyebrow">Curated literature collection</div><h1>Materials Database</h1><p class="sub">Explore the available self-healing material systems and their source information.</p>',unsafe_allow_html=True)
    st.metric("Curated material systems",len(materials))
    term=st.text_input("Search materials and research fields",placeholder="Try ligand, disulfide, polyurethane, DOI, application...")
    view=materials.copy()
    if term:
        needle=norm(term)
        mask=view[COLS].apply(lambda row:needle in " ".join(map(str,row.values)).lower(),axis=1)
        view=view[mask]
    st.caption(f"{len(view)} records")
    st.dataframe(view[COLS].replace("", "Not reported"),use_container_width=True,height=680)

elif page.startswith("⬡"):
    st.markdown('<div class="eyebrow">Platform guide</div><h1>How It Works</h1><p class="sub">A transparent workflow for literature-backed material discovery.</p>',unsafe_allow_html=True)
    st.markdown("#### 1. Describe your research requirements")
    st.write("Enter a healing mechanism, property, numeric threshold, stimulus, or application. The search parser identifies supported criteria from the query.")
    st.markdown("#### 2. Review matching materials")
    st.write("Each material is assessed criterion by criterion. Results are ranked by weighted agreement with the criteria that have reported values.")
    st.markdown("#### 3. Set essential requirements")
    st.write("You can mark criteria as essential. A reported mismatch excludes a material; missing information remains unknown and is not silently treated as failure.")
    st.markdown("#### 4. Inspect evidence")
    st.write("Review the source paper, DOI, reported experimental evidence, verification status, and limitations before using a result in research.")
    st.markdown("#### Understanding match scores")
    st.write("Scores are relevance heuristics, not predictions of healing performance or evidence quality. A missing value is labelled Not reported and excluded from the score denominator.")

else:
    st.markdown('<div class="eyebrow">About this project</div><h1>SelfHeal Materials</h1><p class="sub">A research discovery interface for exploring self-healing polymer systems using curated literature data.</p>',unsafe_allow_html=True)
    st.markdown("### Research-first principles")
    st.write("- Literature-backed records and traceable source information.")
    st.write("- Missing experimental values are identified as Not reported.")
    st.write("- Match scores describe query relevance, not experimental performance.")
    st.write("- Original publications remain the authoritative source for scientific conclusions.")
    st.markdown("### Dataset")
    st.write(source)
    st.caption("The platform presents curated source data; it does not generate or infer missing experimental measurements.")

st.divider()
st.caption("SelfHeal Materials · Literature-backed research discovery · Verify experimental claims against the original publication.")
