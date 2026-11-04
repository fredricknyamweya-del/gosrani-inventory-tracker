# Gosrani Inventory Tracker

Inventory management project for Gosrani Wholesalers Limited in Eldoret, Kenya.

## Project structure

- `frontend/` — React application built with Vite and JavaScript.
- `backend/` — Flask API managed with Pipenv.

## Prerequisites

- Node.js and npm
- Python and Pipenv

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Use `npm run build` to create a production build and `npm run preview` to preview
that build locally.

## Backend setup

```bash
cd backend
pipenv install
pipenv shell
```

Add runtime dependencies to `backend/Pipfile`; `pipenv install` creates or
updates `backend/Pipfile.lock` with the resolved versions.