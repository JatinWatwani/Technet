# Netlify Deployment Guide for Vigilio

This project is fully configured and ready for 1-click deployment on [Netlify](https://www.netlify.com).

---

## Method 1: Connect via GitHub (Recommended)

1. Push your repository to GitHub (or use your existing repository `https://github.com/JatinWatwani/Technet.git`).
2. Log in to [Netlify](https://app.netlify.com).
3. Click **"Add new site"** → **"Import an existing project"**.
4. Select **GitHub** and authorize your repository.
5. Netlify will **automatically detect the configuration** from [netlify.toml](file:///d:/Coding/Vibe%20Code/Tenet/netlify.toml):
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
   - **Node Version**: `20`
6. *(Optional)* If your FastAPI backend is deployed on Railway, Render, Fly.io, or Cloud Run:
   - Go to **Site Configuration** → **Environment variables**.
   - Add variable: `VITE_API_URL` = `https://your-backend-api-url.com`
   - *(Note: If left unset, Vigilio automatically activates its self-contained Standalone Resilience Simulation with full interactivity, live Leaflet radar, and dynamic rerouting).*
7. Click **"Deploy site"**. Netlify will build and publish your site in ~30 seconds!

---

## Method 2: Manual Drag & Drop (Instant)

1. Build the production bundle locally:
   ```bash
   cd frontend
   npm run build
   ```
2. In Netlify dashboard, go to **Sites** → **"Deploy manually"**.
3. Drag and drop the `frontend/dist` folder directly onto the upload dropzone.
4. Your site will be live instantly!

---

## Method 3: Netlify CLI

You can deploy directly from your terminal using `npx`:
```bash
# 1. Login to Netlify
npx netlify login

# 2. Build and deploy
cd frontend
npm run build
npx netlify deploy --prod --dir=dist
```

---

## Key Configurations Pre-Configured for Netlify

- **`netlify.toml`**: Pre-configured at repository root and in `frontend/` with SPA routing rewrites.
- **`public/_redirects`**: Pre-configured `/* /index.html 200` to prevent 404 errors on deep linking or browser page refresh.
- **Leaflet & OpenStreetMap**: Full zero-cost geospatial map tiles, GPS tracking, and route polylines are compatible with all modern browsers without CORS issues or API keys.
- **Standalone Simulation Fallback**: If the Python backend is not attached yet, the frontend automatically activates an interactive simulation layer so recruiters and judges can test all playbooks without backend setup.
