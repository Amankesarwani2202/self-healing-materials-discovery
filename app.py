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
        s=norm(actual)
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
        match_type="Exact match" if known and all(s=="Match" for _,s,_ in known) else ("Partial match" if any(s=="Match" for _,s,_ in known) else "Unverified / no match")
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
#MainMenu,footer,[data-testid="stStatusWidget"],.viewerBadge_container__1QSob{visibility:hidden}
.block-container{max-width:1480px;padding-top:1.15rem}
.topline{font-size:.75rem;font-weight:750;letter-spacing:.14em;text-transform:uppercase;color:#5c7f9b}
h1{font-size:2rem!important;letter-spacing:-.03em;margin:.1rem 0}
.sub{opacity:.72;font-size:.94rem}
.result{border:1px solid rgba(128,128,128,.3);border-radius:11px;padding:.7rem;margin:.2rem 0}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="topline">Evidence-led literature discovery</div><h1>Self-Healing Materials Discovery</h1><div class="sub">Search, compare, and trace material systems to published research evidence.</div>',unsafe_allow_html=True)
discover,compare,database,method=st.tabs(["Discover materials","Compare","Materials database","Methodology"])
with discover:
    query=st.text_area("Describe the material or healing behaviour you need",placeholder="e.g. Polymer that heals through metal–ligand coordination, preferably at room temperature",height=82)
    go,helpcol=st.columns([1,3])
    with go: clicked=st.button("Search materials",type="primary",use_container_width=True)
    with helpcol: st.caption("Try mechanism names, temperature or efficiency limits, healing time, flexibility, stimulus, or application.")
    if clicked:
        st.session_state["query"]=query
        st.session_state["criteria"]=parse_query(query)
        st.session_state["searched"]=True
        st.session_state["required"]=[]
    if st.session_state.get("searched"):
        criteria=st.session_state.get("criteria",[])
        if not criteria:
            st.info("No structured criterion was recognized. Try a mechanism such as metal–ligand coordination, a numeric limit, or a property. You can still search every record in the Materials database tab.")
        else:
            st.markdown("**Your search criteria**")
            st.write(" · ".join(c["label"]+": "+(", ".join(c["value"]) if isinstance(c["value"],list) else str(c["value"])) for c in criteria))
            required=st.multiselect("Essential criteria (reported mismatches are excluded; unknown values remain visible)",[c["label"] for c in criteria],default=st.session_state.get("required",[]),key="must_have")
            st.session_state["required"]=required
            results=rank(materials,criteria,required) if not materials.empty else materials.copy()
            st.markdown(f"### Matching materials · {len(results)} records")
            if results.empty: st.warning("No records meet all essential criteria. Remove an essential requirement to explore partial matches.")
            else:
                per_page=20; pages=max(1,(len(results)+per_page-1)//per_page)
                page=st.number_input("Results page",min_value=1,max_value=pages,value=1,step=1)
                batch=results.iloc[(page-1)*per_page:page*per_page]
                left,right=st.columns([.95,1.6],gap="large")
                with left:
                    st.markdown("**Ranked materials**")
                    labels=[f"{r['Material']} · {r['Match score']}/100" for _,r in batch.iterrows()]
                    choice=st.radio("Choose a material",labels,label_visibility="collapsed")
                    idx=labels.index(choice); selected=batch.iloc[idx]
                    st.caption(f"Showing {(page-1)*per_page+1}–{min(page*per_page,len(results))} of {len(results)}")
                with right:
                    st.markdown("**Selected material**")
                    st.markdown(f"## {selected['Material']}")
                    st.caption(f"{selected['ID']} · {shown(selected['Polymer family'])}")
                    x,y,z=st.columns(3)
                    x.metric("Match score",f"{selected['Match score']}/100")
                    y.metric("Match type",selected["Match type"])
                    z.metric("Criteria reported",selected["Coverage"])
                    x,y,z=st.columns(3)
                    x.metric("Healing temperature",shown(selected["Healing temperature"]," °C"))
                    y.metric("Healing efficiency",shown(selected["Healing efficiency"],"%"))
                    z.metric("Healing time",shown(selected["Healing time"]," h"))
                    st.write(f"**Healing mechanism:** {shown(selected['Mechanism'])}")
                    st.write(f"**Stimulus:** {shown(selected['Stimulus'])} · **Application:** {shown(selected['Application'])}")
                    st.write(f"**Flexibility:** {shown(selected['Flexibility'])} · **Efficiency measured:** {shown(selected['Efficiency property'])}")
                    st.markdown("**Requirement assessment**")
                    for label,s,_ in selected["Checks"]:
                        icon="✓" if s=="Match" else ("—" if s=="Not reported" else "✕")
                        st.write(f"{icon} **{label}:** {s}")
                    if selected["Advantages"]: st.write("**Reported advantages:** "+str(selected["Advantages"]))
                    if selected["Limitations"]: st.write("**Reported limitations:** "+str(selected["Limitations"]))
                    with st.expander("Research paper and experimental evidence",expanded=True):
                        st.write("**Paper:** "+shown(selected["Paper title"]))
                        st.write("**Authors:** "+shown(selected["Authors"]))
                        st.write("**Year / journal:** "+shown(selected["Year"])+" · "+shown(selected["Journal"]))
                        st.write("**Experimental evidence:** "+shown(selected["Evidence"]))
                        st.write("**Verification status:** "+shown(selected["Verification status"]))
                        link=doi_url(selected["DOI"])
                        if link: st.markdown(f"[Open publication / DOI]({link})")
                        else: st.write("**DOI / paper link:** Not reported")
                        if selected["Notes"]: st.caption("Data notes: "+str(selected["Notes"]))
            with st.expander("How the score works"):
                st.write("The score measures agreement with criteria recognized in your query, not predicted healing performance. A reported match earns its criterion weight; a reported mismatch earns zero. Unreported values are excluded from the score denominator and shown as Not reported. Coverage shows how many criteria have reported values.")
                st.write("Exact match means every evaluated criterion matches. Partial match means at least one evaluated criterion matches and at least one does not. Unknown values are shown separately.")
with compare:
    st.markdown("### Compare material systems")
    st.caption("Compare up to four records using values from the curated dataset.")
    names=materials["Material"].tolist() if not materials.empty else []
    selected_names=st.multiselect("Select materials",names,max_selections=4)
    if selected_names:
        fields=["ID","Polymer family","Mechanism","Stimulus","Healing temperature","Healing temperature notes","Healing time","Healing efficiency","Efficiency property","Tensile strength","Elongation","Flexibility","Application","Advantages","Limitations","Paper title","Authors","Year","Journal","DOI","Evidence","Verification status"]
        view=materials[materials["Material"].isin(selected_names)].set_index("Material")[fields].T
        st.dataframe(view.replace("", "Not reported").fillna("Not reported"),use_container_width=True,height=680)
with database:
    st.markdown("### Materials database")
    st.caption(source+" · Search all records and fields.")
    term=st.text_input("Search the database",placeholder="ligand, disulfide, polyurethane, wearable...")
    view=materials.copy()
    if term:
        needle=norm(term)
        mask=view[COLS].apply(lambda row:needle in " ".join(map(str,row.values)).lower(),axis=1)
        view=view[mask]
    st.caption(f"{len(view)} records")
    st.dataframe(view[COLS].replace("", "Not reported"),use_container_width=True,height=650)
with method:
    st.markdown("### Transparent ranking methodology")
    st.write("The platform extracts supported criteria from the query and compares them with corresponding fields in the literature dataset.")
    st.markdown("""
**Match score:** For each criterion with a reported value, a match earns its criterion weight and a mismatch earns zero. The score is the weighted proportion of evaluated criteria that match, scaled to 100. Healing mechanism has a higher default weight than descriptive preferences. Numeric thresholds follow the requested direction.

**Missing information:** A missing value is shown as Not reported and excluded from the score denominator. It is not treated as a poor result. Criteria coverage indicates how many requested properties have reported values.

**Essential vs preferred:** Mark extracted criteria as essential in the Discover tab. A reported mismatch against an essential criterion excludes that record. An unreported value remains visible as unknown rather than being silently rejected.

**Scientific limitations:** This is a transparent relevance heuristic, not an ML prediction, evidence-quality score, or guarantee of experimental performance. It depends on the completeness and accuracy of curated records. Consult the original publication before drawing scientific conclusions.

**Data provenance:** Records are loaded from the repository CSV. The app displays reported values and source details; it does not generate missing experimental measurements.
""")
st.divider()
st.caption("Self-Healing Materials Discovery · Literature-backed research tool · Verify experimental claims against the original publication.")
