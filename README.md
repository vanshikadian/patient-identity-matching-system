# Patient Identity Matching System

This project is a healthcare record matching system built to answer a simple but important question:

When two messy patient records come from different sources, are they actually the same person?

Instead of relying on one exact string match, the app uses a layered approach:

- candidate blocking to avoid comparing every record to every other record
- an ML classifier to score likely matches quickly
- an LLM fallback for ambiguous cases

The goal is to make identity matching feel practical, inspectable, and demoable, not just theoretical.

## What the app does

You upload two CSV files, labeled source A and source B.

The system then:

1. normalizes the incoming records
2. tries to map flexible CSV column names into the fields it understands
3. generates candidate pairs instead of brute-forcing every comparison
4. computes similarity features for those candidate pairs
5. scores them with an XGBoost model
6. sends uncertain cases through an LLM-style resolution layer
7. shows the final results and metrics in the dashboard

The app is built to handle messy records, including things like:

- spelling mistakes
- swapped names
- DOB off by one day
- partial addresses
- inconsistent phone formatting
- missing fields

## Tech stack

- Backend: FastAPI
- Data processing: Pandas
- Similarity + feature engineering: Jellyfish, FAISS, custom feature logic
- Model: XGBoost
- Frontend: React + Tailwind + Recharts
- Database: PostgreSQL
- Local orchestration: Docker Compose

## Project structure

```text
patient-identity-matching/
├── api/                  # FastAPI routes
├── blocking/             # Candidate pair generation
├── common/               # Shared config, models, pipeline logic
├── data/                 # Synthetic data generation scripts
├── features/             # Similarity feature engineering
├── frontend/             # React frontend
├── ingestion/            # CSV ingestion + normalization
├── llm/                  # Ambiguous case resolver
├── model/                # Training and evaluation
├── tests/                # Lightweight backend tests
├── Dockerfile.api
├── Dockerfile.frontend
├── docker-compose.yml
└── DEPLOYMENT.md
```

## Local setup

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the app:

```bash
docker compose up --build
```

3. Open:

- Frontend: `http://localhost:3001`
- API docs: `http://localhost:8001/docs`

## Generating demo data

If you want to use the included synthetic records:

```bash
python3 data/generate.py
python3 data/inject_noise.py
```

That will create files in:

```text
artifacts/generated/
```

Including:

- `records_A.csv`
- `records_B.csv`
- `records_A_smoke.csv`
- `records_B_smoke.csv`
- `matches.csv`

## Running tests

```bash
python3 -m unittest discover -s tests
```

## What is working well right now

- end-to-end uploads
- flexible CSV header mapping
- background run execution for smoother demos
- readable result rows with patient details
- live metrics from completed runs
- smaller demo and smoke-test datasets

## What I would still improve next

This is stronger than a rough prototype, but it is still not a finished production platform.

The biggest next improvements would be:

- manual column mapping in the upload UI
- a persistent background job queue instead of an in-process worker
- auth beyond a simple API key
- fuller test coverage
- deployment-specific environment configuration

## Deployment

The fastest clean deployment path is:

- frontend on Vercel
- backend on Render or Railway
- Postgres on Neon, Railway, or Supabase

Why not deploy the whole thing to Vercel right away?

Because the backend currently runs longer matching jobs in-process. That works locally and on a long-lived backend service, but it is not the best fit for serverless execution as-is.

If you want the exact steps, see [DEPLOYMENT.md](/Users/vanshika/Patient%20Identity%20Matching%20System/DEPLOYMENT.md:1).

## Why this project exists

This project is meant to show a more realistic matching story than exact string comparison alone.

In healthcare, records are often incomplete, inconsistent, and duplicated across systems. A layered matching pipeline like this is much closer to how you would approach the problem in practice: narrow the search space, score intelligently, and reserve the most expensive reasoning for edge cases that actually need it.
