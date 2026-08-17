# 🧪 Self-Healing Materials Discovery

AI-assisted discovery platform for self-healing polymer materials from scientific literature.

## Session 1 prototype

This first version provides a simple Streamlit UI where a user can describe the material they are looking for and view candidate material systems from a small prototype dataset.

### Planned development

- Natural-language requirement extraction
- Curated database of ~30 published self-healing polymer systems
- Requirement-based ranking and filtering
- "Why this matches" explanations
- Side-by-side material comparison
- Evidence and paper citations
- Hallucination controls and scientific limitations

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

Deploy the repository using `app.py` as the application entrypoint.

> The current records are explicitly demo records for the UI prototype and should not be treated as validated scientific evidence. The literature dataset will be curated and evidence-linked in a later phase.
