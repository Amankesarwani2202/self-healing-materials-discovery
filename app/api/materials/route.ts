import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "csv-parse/sync";
import type { Material } from "@/lib/search";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const aliases: Record<string,string> = {
"id":"id","material/polymer name":"material","material name":"material","material":"material",
"polymer family":"polymerFamily","healing mechanism":"mechanism","mechanism":"mechanism",
"external stimulus required":"stimulus","stimulus":"stimulus","healing temp (°c)":"healingTemperature",
"healing temperature":"healingTemperature","healing temp notes":"healingTemperatureNotes",
"healing time (hrs)":"healingTime","healing time":"healingTime","healing efficiency (%)":"healingEfficiency",
"healing efficiency":"healingEfficiency","efficiency measured property":"efficiencyProperty",
"tensile strength (mpa)":"tensileStrength","elongation at break (%)":"elongation","flexibility category":"flexibility",
"application area":"application","main advantages":"advantages","main limitations/trade-offs":"limitations",
"supporting evidence":"evidence","paper title":"paperTitle","authors":"authors","year":"year","journal":"journal",
"doi/link":"doi","data collector":"dataCollector","date collected":"dateCollected",
"verification status":"verificationStatus","notes/uncertainty flags":"notes"
};
function normalizeHeader(s:string){return s.toLowerCase().replace(/[–—]/g,"-").replace(/\\s+/g," ").trim();}
export async function GET(){
  try{
    const file=path.join(process.cwd(),"data","self_healing_materials.csv");
    const csv=await readFile(file,"utf8");
    const rows=parse(csv,{columns:true,skip_empty_lines:true,relax_quotes:true,relax_column_count:true,trim:true}) as Record<string,string>[];
    const materials:Material[]=rows.filter(r=>String(r["Material/Polymer Name"]??r.Material??"").trim()).map((r)=>{
      const m:Record<string,string>={};
      for(const [key,value] of Object.entries(r)){const dest=aliases[normalizeHeader(key)]??key;m[dest]=String(value??"").trim();}
      return {...m,id:m.id??"",material:m.material??"",mechanism:m.mechanism??"",stimulus:m.stimulus??"",healingTemperature:m.healingTemperature??"",healingTime:m.healingTime??"",healingEfficiency:m.healingEfficiency??"",paperTitle:m.paperTitle??"",doi:m.doi??"",evidence:m.evidence??""} as Material;
    });
    return NextResponse.json({materials,count:materials.length,source:"Repository CSV"},{headers:{"Cache-Control":"no-store"}});
  }catch(error){console.error("Dataset load failed",error);return NextResponse.json({error:"The repository dataset could not be loaded."},{status:500});}
}