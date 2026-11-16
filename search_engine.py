"""Transparent, testable search parsing and relevance ranking."""
import re
import pandas as pd

MECH = {
 "metal-ligand coordination":["metal-ligand coordination","metal ligand coordination","metal–ligand coordination","coordination bond","coordination interaction","ligand interaction","ligand interactions","metal coordination","fe3+-catechol coordination","fe3+ coordination","iron-catechol coordination","zinc coordination","catechol coordination"],
 "hydrogen bonding":["hydrogen bond","hydrogen bonding","h-bond"],
 "disulfide exchange":["disulfide","disulfide exchange"],
 "imine/schiff base":["imine","schiff base"],
 "boronic ester":["boronic ester","boronate"],
 "diels-alder":["diels-alder","diels alder"],
 "transesterification":["transesterification","ester exchange"],
 "ionic interactions":["ionic interaction","ionic interactions","ion-dipole","ion dipole"],
 "π–π stacking":["π–π","pi-pi stacking","pi pi stacking"],
 "chain interdiffusion":["chain interdiffusion","chain diffusion"],
 "dynamic covalent bonds":["dynamic covalent","covalent exchange"],
}

def norm(value):
    return re.sub(r"\s+"," ",str(value or "").lower().replace("–","-").replace("—","-")).strip()

def number(value):
    if pd.isna(value) or not str(value).strip(): return None
    match=re.search(r"-?\d+(?:\.\d+)?",str(value).replace(",",""))
    return float(match.group()) if match else None

def parse_query(query):
    q=norm(query); out=[]
    mechanisms=[key for key,aliases in MECH.items() if any(norm(alias) in q for alias in aliases)]
    if mechanisms: out.append({"key":"Mechanism","label":"Healing mechanism","value":mechanisms,"weight":2.0})
    temp=re.search(r"(?:≤|<=|below|under|less than|at most|no more than|up to|maximum(?: of)?)\s*(-?\d+(?:\.\d+)?)\s*°?\s*c\b",q)
    if temp: out.append({"key":"Temperature","label":"Maximum healing temperature","value":float(temp.group(1)),"weight":1.5})
    eff=re.search(r"(?:≥|>=|at least|minimum(?: of)?|min(?:imum)?|over|above|greater than)\s*(\d+(?:\.\d+)?)\s*%",q)
    if eff: out.append({"key":"Efficiency","label":"Minimum healing efficiency / recovery","value":float(eff.group(1)),"weight":1.5})
    tm=re.search(r"(?:within|under|less than|in|at most)\s*(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|days?)",q)
    if tm: out.append({"key":"Time","label":"Maximum healing time","value":float(tm.group(1))*(24 if tm.group(2).startswith("day") else 1),"weight":1.0})
    vocab={"Flexibility":["flexible","stretchable","elastic","elastomeric"],
           "Stimulus":["autonomous","room temperature","room temp","ambient temperature","light","uv","water","pressure","mechanical","heat","thermal"],
           "Application":["wearable electronics","wearable sensors","soft robotics","robotics","coatings","biomedical","sensors","electronics","adhesives"]}
    for key,words in vocab.items():
        hits=[word for word in words if word in q]
        if hits: out.append({"key":key,"label":key,"value":hits,"weight":1.0})
    return out

def status(row,c):
    key,target=c["key"],c["value"]
    actual={"Mechanism":row.get("Mechanism",""),"Temperature":row.get("__temp"),"Efficiency":row.get("__eff"),"Time":row.get("__time"),
            "Flexibility":row.get("Flexibility",""),"Stimulus":row.get("Stimulus",""),"Application":row.get("Application","")}[key]
    if key=="Mechanism":
        evidence=norm(" ".join(str(row.get(col,"")) for col in ["Mechanism","Notes","Evidence","Advantages","Limitations"]))
        if any(norm(alias) in evidence for mechanism in target for alias in MECH[mechanism]): return "Match"
        if norm(actual) in ("","other","not reported","not stated","unknown","n/a","na"): return "Not reported"
        return "No match"
    if key in ("Temperature","Efficiency","Time"):
        if actual is None: return "Not reported"
        ok=actual<=target if key in ("Temperature","Time") else actual>=target
        return "Match" if ok else "No match"
    if not str(actual or "").strip(): return "Not reported"
    actual_text=norm(actual)
    if key=="Flexibility":
        aliases={"flexible":["flexible","highly flexible","semi-flexible","elastomeric","stretchable"],
                 "stretchable":["stretchable","highly flexible","elastomeric"],"elastic":["elastic","elastomeric","flexible"],
                 "elastomeric":["elastomeric","highly flexible"]}
        return "Match" if any(alias in actual_text for item in target for alias in aliases.get(item,[item])) else "No match"
    if key=="Stimulus":
        aliases={"room temperature":["room temperature","room temp","ambient","autonomous"],
                 "room temp":["room temp","room temperature","ambient","autonomous"],
                 "ambient temperature":["ambient","room temperature","room temp","autonomous"],
                 "autonomous":["autonomous","no external stimulus","no external stimuli"]}
        return "Match" if any(alias in actual_text for item in target for alias in aliases.get(item,[item])) else "No match"
    return "Match" if any(norm(item) in actual_text for item in target) else "No match"

def rank(data,criteria,required):
    rows=[]
    for _,record in data.iterrows():
        checks=[(c["label"],status(record,c),c["weight"]) for c in criteria]
        reported=[item for item in checks if item[1]!="Not reported"]
        denominator=sum(item[2] for item in reported)
        score=round(100*sum(item[2] for item in reported if item[1]=="Match")/denominator) if denominator else None
        failures=[label for label,result,_ in checks if label in required and result=="No match"]
        states=[result for _,result,_ in checks]
        if states and all(result=="Match" for result in states): classification="Exact match"
        elif any(result=="Match" for result in states) and all(result in ("Match","Not reported") for result in states): classification="Potential match · incomplete data"
        elif any(result=="Match" for result in states): classification="Partial match"
        elif states and all(result=="Not reported" for result in states): classification="Insufficient reported data"
        else: classification="No matching criteria"
        rows.append((score,checks,failures,classification,f"{len(reported)}/{len(checks)}" if checks else "—"))
    ranked=data.copy()
    ranked["Match score"]=[row[0] for row in rows]
    ranked["Checks"]=[row[1] for row in rows]
    ranked["Required failures"]=[row[2] for row in rows]
    ranked["Match type"]=[row[3] for row in rows]
    ranked["Coverage"]=[row[4] for row in rows]
    if required: ranked=ranked[ranked["Required failures"].map(len)==0]
    return ranked.sort_values(["Match score","__eff"],ascending=[False,False],na_position="last").reset_index(drop=True)

def shown(value,suffix=""):
    return "Not reported" if value is None or str(value).strip()=="" else f"{value}{suffix}"

def doi_url(value):
    text=str(value or "").strip()
    return (text if text.startswith(("http://","https://")) else "https://doi.org/"+text) if text else None

def score_text(value):
    return "Not scorable" if value is None or pd.isna(value) else f"{int(value)}/100"

def sentence_start(value):
    text=str(value)
    for index,char in enumerate(text):
        if char.isalpha(): return text[:index]+char.upper()+text[index+1:]
    return text
