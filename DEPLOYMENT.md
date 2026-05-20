# Deployment Guide

## Fastest path if you want everything on Vercel

This repo now includes a root `vercel.json` that is set up for Vercel Services:

- frontend at `/`
- FastAPI backend at `/api`

That means the frontend can talk to the backend with a relative `/api` URL in one Vercel project.

### Before you deploy

1. Push the repo to GitHub.
2. Import the repo into Vercel.
3. In the Vercel dashboard, set the Framework Preset to **Services**.
4. Add environment variables:
   - `DATABASE_URL`
   - `API_KEY`
   - `ANTHROPIC_API_KEY` (optional)
5. Redeploy.

### Important note

This is the easiest path if you want one hosted project quickly.

The backend still uses an in-process background runner for match jobs. That is acceptable for a quick demo deployment, but for very large runs or stronger production reliability, a separate persistent worker model would still be better.

## Recommended split

- Frontend: Vercel
- Backend: Render or Railway
- Database: Neon / Railway Postgres / Supabase

This project currently uses a Python background run manager. That makes it a poor fit for a purely serverless backend deployment without refactoring the worker model.

## Frontend on Vercel

1. Import the repo into Vercel.
2. Set the root directory to `frontend`.
3. Build command: `npm run build`
4. Output directory: `dist`
5. Add `VITE_API_KEY` if you want to override the default.
6. Point the frontend API base URL to your deployed backend before production use.

## Backend on Render or Railway

1. Deploy from the repo root.
2. Use `Dockerfile.api`.
3. Set environment variables:
   - `DATABASE_URL`
   - `API_KEY`
   - `ANTHROPIC_API_KEY` (optional)
4. Expose port `8000`.
5. Provision managed Postgres and connect it through `DATABASE_URL`.

## Database

- The local Docker setup uses `pgvector/pgvector:pg15`.
- For hosted deployments, use a managed Postgres instance.
- If you want vector support later, make sure the target platform supports the extension or keep the JSON embedding fallback.

## Notes

- The frontend and backend should not use `localhost` in deployed environments.
- Update [frontend/src/api.js](/Users/vanshika/Patient%20Identity%20Matching%20System/frontend/src/api.js:1) to use an environment-driven API URL before deployment.
