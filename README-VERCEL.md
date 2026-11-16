# SelfHeal Materials — Next.js / Vercel migration

This branch adds a Next.js implementation alongside the existing Streamlit application. The Streamlit entry point and Python search engine remain in place; the migration reads the same committed CSV dataset.

## Stack

- Next.js App Router + React + TypeScript
- Server-side CSV loading through `app/api/materials/route.ts`
- Transparent TypeScript port of the query parser and weighted relevance ranking
- Responsive research UI for Discover, Compare, Materials Database, How It Works, and About

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Validate

```bash
npm run typecheck
npm run lint
npm run build
```

## Deploy a preview on Vercel

1. Import this GitHub repository into Vercel.
2. Select the `feature/vercel-migration` branch for a preview deployment.
3. Framework preset: Next.js. Build command: `npm run build`. Output directory: leave the default.
4. No database, paid API, or environment secret is required; the app reads `data/self_healing_materials.csv` from the repository at runtime.
5. Keep the production project on `main` (the Streamlit app) until the preview is reviewed and accepted.

## Scientific limitations

The match score is a query-relevance heuristic, not a model of material performance, durability, safety, manufacturability, or evidence quality. Missing values are displayed as “Not reported” and excluded from the score. Dataset records should be verified against their cited publications before scientific use.
