export type Material = Record<string, string> & {
  id: string; material: string; mechanism: string; stimulus: string;
  healingTemperature: string; healingTime: string; healingEfficiency: string;
  paperTitle: string; doi: string; evidence: string; matchScore?: number | null;
  matchType?: string; checks?: { label: string; status: string; weight: number }[];
  coverage?: string;
};

export type Criterion = { key: string; label: string; value: string | number | string[]; weight: number; property?: string };
export const MECH: Record<string, string[]> = {
  "metal-ligand coordination": ["metal-ligand coordination","metal ligand coordination","metal–ligand coordination","coordination bond","coordination interaction","ligand interaction","ligand interactions","metal coordination","fe3+-catechol coordination","fe3+ coordination","iron-catechol coordination","zinc coordination","catechol coordination"],
  "hydrogen bonding": ["hydrogen bond","hydrogen bonding","h-bond"],
  "disulfide exchange": ["disulfide","disulfide exchange"],
  "imine/schiff base": ["imine","schiff base"],
  "boronic ester": ["boronic ester","boronate"],
  "diels-alder": ["diels-alder","diels alder"],
  "transesterification": ["transesterification","ester exchange"],
  "ionic interactions": ["ionic interaction","ionic interactions","ion-dipole","ion dipole"],
  "π–π stacking": ["π–π","pi-pi stacking","pi pi stacking"],
  "chain interdiffusion": ["chain interdiffusion","chain diffusion"],
  "dynamic covalent bonds": ["dynamic covalent","covalent exchange"]
};
export const norm = (v: unknown) => String(v ?? "").toLowerCase().replace(/[–—]/g,"-").replace(/\s+/g," ").trim();
export const numeric = (v: unknown): number | null => { const m=String(v ?? "").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/); return m ? Number(m[0]) : null; };

export function parseQuery(input: string): Criterion[] {
  const q=norm(input), out: Criterion[]=[];
  const mechanisms=Object.entries(MECH).filter(([,a])=>a.some(x=>q.includes(norm(x)))).map(([k])=>k);
  if(mechanisms.length) out.push({key:"Mechanism",label:"Healing mechanism",value:mechanisms,weight:2});
  const temp=q.match(/(?:≤|<=|below|under|less than|at most|no more than|up to|maximum(?: of)?)\s*(-?\d+(?:\.\d+)?)\s*°?\s*c\b/);
  if(temp) out.push({key:"Temperature",label:"Maximum healing temperature",value:Number(temp[1]),weight:1.5});
  const eff=q.match(/(?:≥|>=|at least|minimum(?: of)?|min(?:imum)?|over|above|greater than)\s*(\d+(?:\.\d+)?)\s*%/);
  if(eff){ const prop=(q.includes("strength")&&!q.includes("elongation"))||q.includes("strength restoration")?"Tensile Strength":q.includes("elongation recovery")?"Elongation":undefined; out.push({key:"Efficiency",label:"Minimum healing efficiency / recovery",value:Number(eff[1]),weight:1.5,property:prop}); }
  const tm=q.match(/(?:within|under|less than|in|at most)\s*(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|days?)\b/);
  if(tm) out.push({key:"Time",label:"Maximum healing time",value:Number(tm[1])*(tm[2].startsWith("day")?24:1),weight:1});
  const vocab: Record<string,string[]>={Flexibility:["flexible","stretchable","elastic","elastomeric"],Stimulus:["autonomous","room temperature","room temp","ambient temperature","light","uv","water","pressure","mechanical","heat","thermal"],Application:["wearable electronics","wearable sensors","soft robotics","robotics","coatings","biomedical","sensors","electronics","adhesives"]};
  for(const [key,words] of Object.entries(vocab)){const hits=words.filter(w=>q.includes(w));if(hits.length)out.push({key,label:key,value:hits,weight:1});}
  return out;
}
function get(m:Material,key:string){return key==="Mechanism"?m.mechanism:key==="Temperature"?numeric(m.healingTemperature):key==="Efficiency"?numeric(m.healingEfficiency):key==="Time"?numeric(m.healingTime):m[key==="Flexibility"?"flexibility":key==="Stimulus"?"stimulus":"application"];}
function assess(m:Material,c:Criterion):string{
  const actual=get(m,c.key), target=c.value;
  if(c.key==="Mechanism"){
    const evidence=norm([m.mechanism,m.notes,m.evidence,m.advantages,m.limitations].join(" "));
    return (target as string[]).some(k=>MECH[k].some(a=>evidence.includes(norm(a))))?"Match":(!actual||["other","not reported","not stated","unknown","n/a"].includes(norm(actual)))?"Not reported":"No match";
  }
  if(["Temperature","Efficiency","Time"].includes(c.key)){
    if(actual===null||actual===undefined||actual==="")return "Not reported";
    if(c.key==="Efficiency"&&c.property){const measured=norm(m.efficiencyProperty),wanted=norm(c.property);if(!measured)return "Not reported";if(!measured.includes(wanted)&&!wanted.includes(measured))return "No match";}
    return (c.key==="Efficiency"?Number(actual)>=Number(target):Number(actual)<=Number(target))?"Match":"No match";
  }
  if(!String(actual??"").trim())return "Not reported";
  const a=norm(actual);
  if(c.key==="Flexibility")return (target as string[]).some(x=>a.includes(x)||(x==="elastic"&&a.includes("elastomeric"))||(x==="flexible"&&a.includes("elastomeric")))?"Match":"No match";
  if(c.key==="Stimulus"){const aliases=["room temperature","room temp","ambient","autonomous"];return (target as string[]).some(x=>a.includes(x)||(aliases.includes(x)&&aliases.some(y=>a.includes(y))))?"Match":"No match";}
  return (target as string[]).some(x=>a.includes(norm(x)))?"Match":"No match";
}
export function rankMaterials(data:Material[],criteria:Criterion[],required:string[]=[]):Material[]{
  if(!criteria.length)return data.map(m=>({...m,matchScore:null,matchType:"Not searched",checks:[],coverage:"—"}));
  return data.map(m=>{const checks=criteria.map(c=>({label:c.label,status:assess(m,c),weight:c.weight}));const reported=checks.filter(x=>x.status!=="Not reported");const denominator=reported.reduce((s,x)=>s+x.weight,0);const matched=reported.filter(x=>x.status==="Match").reduce((s,x)=>s+x.weight,0);const score=denominator?Math.round(100*matched/denominator):null;const states=checks.map(x=>x.status);const type=states.every(x=>x==="Match")?"Exact match":states.some(x=>x==="Match")&&states.every(x=>x==="Match"||x==="Not reported")?"Potential match · incomplete data":states.some(x=>x==="Match")?"Partial match":states.every(x=>x==="Not reported")?"Insufficient reported data":"No matching criteria";return {...m,matchScore:score,matchType:type,checks,coverage:`${reported.length}/${checks.length}`};}).filter(m=>!required.some(label=>m.checks?.some(c=>c.label===label&&c.status==="No match"))).sort((a,b)=>(b.matchScore??-1)-(a.matchScore??-1)||(numeric(b.healingEfficiency)??-1)-(numeric(a.healingEfficiency)??-1));
}
export const display = (v:string|undefined,suffix="") => v?.trim()?v+suffix:"Not reported";
export const doiLink = (v:string) => !v?"":v.startsWith("http")?v:`https://doi.org/${v}`;