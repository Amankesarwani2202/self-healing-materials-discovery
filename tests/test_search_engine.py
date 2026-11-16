import unittest
import pandas as pd
from search_engine import parse_query, rank, status, number, score_text

def sample(**updates):
    row={"ID":"T1","Material":"Test polymer","Mechanism":"Other","Stimulus":"Autonomous (Room Temp)",
         "Flexibility":"Highly Flexible/Elastomeric","Application":"Wearable Electronics",
         "Healing temperature":"-20","Healing efficiency":"85.7","Healing time":"6",
         "Notes":"Reported metal–ligand coordination and hydrogen bonding in the paper.",
         "Evidence":"Strength recovery of 85.7% after healing at −20 °C for 6 h.",
         "Advantages":"","Limitations":"","Verification status":"Verified"}
    row.update(updates)
    row["__temp"]=number(row["Healing temperature"])
    row["__eff"]=number(row["Healing efficiency"])
    row["__time"]=number(row["Healing time"])
    return row

class SearchEngineTests(unittest.TestCase):
    def test_unicode_comparators_and_recovery(self):
        criteria=parse_query("flexible polymer heals at ≤ 60°C and has ≥ 80% strength recovery")
        self.assertEqual([c["key"] for c in criteria],["Temperature","Efficiency","Flexibility"])
        self.assertEqual(criteria[0]["value"],60.0)
        self.assertEqual(criteria[1]["value"],80.0)
        self.assertEqual(criteria[1]["property"],"Tensile Strength")
    def test_efficiency_measured_property_must_match(self):
        c=parse_query("at least 80% tensile strength recovery")[0]
        self.assertEqual(status(sample(**{"Efficiency property":"Elongation"}),c),"No match")
        self.assertEqual(status(sample(**{"Efficiency property":"Tensile Strength"}),c),"Match")
    def test_worded_thresholds(self):
        criteria=parse_query("heals below 40°C with at least 90% recovery")
        self.assertEqual([c["key"] for c in criteria],["Temperature","Efficiency"])
    def test_ligand_alias(self):
        criteria=parse_query("healing through ligand interactions")
        self.assertEqual(criteria[0]["key"],"Mechanism")
        self.assertEqual(status(sample(),criteria[0]),"Match")
    def test_room_temperature_alias(self):
        criteria=parse_query("autonomous room temperature healing")
        stimulus=next(c for c in criteria if c["key"]=="Stimulus")
        self.assertEqual(status(sample(),stimulus),"Match")
    def test_single_criterion_match_is_full_score(self):
        data=pd.DataFrame([sample(),sample(ID="T2",Mechanism="Hydrogen bonding",Notes="")])
        results=rank(data,parse_query("metal-ligand coordination"),[])
        self.assertEqual(int(results.iloc[0]["Match score"]),100)
        self.assertEqual(results.iloc[0]["Match type"],"Exact match")
    def test_unreported_is_not_zero(self):
        row=sample(Mechanism="Other",Notes="",Evidence="",Advantages="",Limitations="")
        result=rank(pd.DataFrame([row]),parse_query("metal-ligand coordination"),[])
        self.assertTrue(pd.isna(result.iloc[0]["Match score"]))
        self.assertEqual(result.iloc[0]["Match type"],"Insufficient reported data")
        self.assertEqual(score_text(result.iloc[0]["Match score"]),"Not scorable")
    def test_essential_mismatch_removed_unknown_retained(self):
        rows=[sample(ID="match"),sample(ID="unknown",Mechanism="Other",Notes="",Evidence="",Advantages="",Limitations=""),
              sample(ID="mismatch",Mechanism="Disulfide exchange",Notes="",Evidence="",Advantages="",Limitations="")]
        result=rank(pd.DataFrame(rows),parse_query("metal-ligand coordination"),["Healing mechanism"])
        self.assertEqual(set(result["ID"]),{"match","unknown"})
    def test_missing_criterion_does_not_reduce_score(self):
        criteria=parse_query("metal-ligand coordination and below 0°C")
        result=rank(pd.DataFrame([sample(**{"Healing temperature":""})]),criteria,[])
        self.assertEqual(int(result.iloc[0]["Match score"]),100)
        self.assertEqual(result.iloc[0]["Coverage"],"1/2")
        self.assertEqual(result.iloc[0]["Match type"],"Potential match · incomplete data")

if __name__=="__main__":
    unittest.main()
