# Deployment Guide

## Recommended setup

- Frontend: Vercel
- Backend: Render
- Database: Neon Postgres

This project is a good fit for that split because the frontend is light, while the backend needs a heavier Python/ML runtime than Vercel handles comfortably.

## 1. Create the database in Neon

1. Create a Neon project.
2. Copy the connection string.
3. Save it as `DATABASE_URL`.

Use the pooled or direct Postgres URL Neon gives you. Either is fine for this project.

## 2. Deploy the backend on Render

The repo includes [render.yaml](/Users/vanshika/Patient%20Identity%20Matching%20System/render.yaml:1), so Render can read the service config automatically.

1. Go to Render and choose **New +** -> **Blueprint**.
2. Connect this GitHub repo.
3. Render should detect `render.yaml`.
4. Create the service.
5. Add these environment variables in Render:
   - `DATABASE_URL`
   - `API_KEY`
   - `ANTHROPIC_API_KEY` optional

Suggested values:
- `API_KEY=demo-key`
- `ANTHROPIC_API_KEY` can be left blank

The backend runs from [Dockerfile.api](/Users/vanshika/Patient%20Identity%20Matching%20System/Dockerfile.api:1) and serves FastAPI on port `8000`.

When the deploy finishes, your backend URL will look something like:

```text
https://patient-identity-matching-api.onrender.com
```

Check it at:

```text
https://your-render-url/api/health
```

## 3. Deploy the frontend on Vercel

1. Import the same GitHub repo into Vercel.
2. Set the root directory to `frontend`.
3. Framework: `Vite`
4. Build command: `npm run build`
5. Output directory: `dist`

Add these Vercel environment variables:

- `VITE_API_BASE_URL=https://your-render-url/api`
- `VITE_API_KEY=demo-key`

The frontend already reads those values from [frontend/src/api.js](/Users/vanshika/Patient%20Identity%20Matching%20System/frontend/src/api.js:1), so you do not need to edit code for the split deployment.

## 4. Test the live app

1. Open the Vercel frontend URL.
2. Upload `records_A_smoke.csv` and `records_B_smoke.csv`.
3. Click `Run matching`.
4. Confirm metrics and results populate.

## Notes

- Leaving `ANTHROPIC_API_KEY` blank is okay.
- The app will still run without the paid Claude layer.
- For the cleanest demo, use Neon instead of the SQLite fallback.
