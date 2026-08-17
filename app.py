import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Self-Healing Materials Discovery",
    page_icon="🧪",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Demo dataset for Session 1. This will be replaced/expanded with the curated
# literature database in the next phase.
# -----------------------------------------------------------------------------
MATERIALS = pd.DataFrame([
    {
        "Material": "Dynamic polyurethane network",
        "Mechanism": "Dynamic covalent bonds",
        "Healing temperature": "50°C",
        "Healing time": "2 h",
        "Healing efficiency": "85% tensile strength",
        "Flexibility": "High",
        "Stimulus": "Heat",
        "Application": "Flexible electronics",
        "Advantages": "Good flexibility and repeatable healing",
        "Limitations": "Requires moderate heating",
        "Source": "Literature record – demo",
    },
    {
        "Material": "Hydrogen-bonded elastomer",
        "Mechanism": "Reversible hydrogen bonding",
        "Healing temperature": "Room temperature",
        "Healing time": "24 h",
        "Healing efficiency": "80% tensile strength",
        "Flexibility": "Very high",
        "Stimulus": "Autonomous",
        "Application": "Wearable sensors",
        "Advantages": "Highly flexible and autonomous healing",
        "Limitations": "Longer healing time",
        "Source": "Literature record – demo",
    },
    {
        "Material": "Disulfide-crosslinked polymer",
        "Mechanism": "Disulfide exchange",
        "Healing temperature": "60°C",
        "Healing time": "1 h",
        "Healing efficiency": "90% tensile strength",
        "Flexibility": "High",
        "Stimulus": "Heat",
        "Application": "Soft robotics",
        "Advantages": "High recovery and repeatability",
        "Limitations": "Performance depends on network chemistry",
        "Source": "Literature record – demo",
    },
])

st.title("🧪 Self-Healing Materials Discovery")
st.markdown(
    "### AI-assisted discovery of self-healing polymer materials from scientific literature"
)

st.info(
    "🚧 **Session 1 prototype:** The interface is ready for Streamlit deployment. "
    "The AI requirement extraction, literature database, ranking, and evidence layer "
    "will be added in later phases."
)

st.subheader("What material are you looking for?")
query = st.text_area(
    "Describe your requirements in natural language",
    placeholder=(
        "Example: I need a flexible self-healing polymer that can heal below "
        "60°C and recover at least 80% of its strength."
    ),
    height=120,
)

col1, col2 = st.columns([1, 5])
with col1:
    search_clicked = st.button("🔍 Find Materials", type="primary", use_container_width=True)

if search_clicked:
    if not query.strip():
        st.warning("Please describe the material you are looking for.")
    else:
        st.success("Search request received. Showing the current prototype database.")

        # Basic keyword filtering for the first session. This is intentionally
        # simple and will be replaced by structured requirement extraction + ranking.
        terms = query.lower().split()
        mask = MATERIALS.apply(
            lambda row: any(term in " ".join(row.astype(str)).lower() for term in terms if len(term) > 3),
            axis=1,
        )
        results = MATERIALS[mask]
        if results.empty:
            results = MATERIALS

        st.subheader("Candidate materials")
        st.caption(f"Showing {len(results)} candidate(s) from the prototype database.")

        for _, material in results.iterrows():
            with st.container(border=True):
                st.markdown(f"### {material['Material']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Healing temperature", material["Healing temperature"])
                c2.metric("Healing efficiency", material["Healing efficiency"])
                c3.metric("Flexibility", material["Flexibility"])
                c4.metric("Stimulus", material["Stimulus"])

                st.write(f"**Healing mechanism:** {material['Mechanism']}")
                st.write(f"**Healing time:** {material['Healing time']}")
                st.write(f"**Application:** {material['Application']}")
                st.write(f"**Why it may match:** {material['Advantages']}")
                st.write(f"**Trade-off:** {material['Limitations']}")
                st.caption(f"Source: {material['Source']}")

else:
    st.subheader("Example searches")
    examples = [
        "Flexible polymer, healing below 60°C, at least 80% strength recovery",
        "Room-temperature self-healing material for wearable sensors",
        "Heat-healable polymer for soft robotics",
    ]
    for example in examples:
        st.markdown(f"- {example}")

st.divider()

with st.expander("About this project"):
    st.write(
        "The long-term platform will convert natural-language material requirements "
        "into structured constraints, search a curated database of approximately 30 "
        "published self-healing polymer systems, rank candidates, explain trade-offs, "
        "and provide evidence-backed citations to the source papers."
    )
    st.write(
        "The prototype deliberately does not claim that the demo records are validated "
        "scientific evidence. Literature records and supporting evidence will be curated "
        "before they are used for scientific recommendations."
    )
