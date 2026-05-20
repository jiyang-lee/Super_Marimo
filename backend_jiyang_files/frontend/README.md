# Super_Marimo Frontend

This folder serves the beta dashboard directly.

## Main Pages

- `/index.html` - redirects to `beta-dashboard.html`
- `/beta-dashboard.html` - home, chat + sensor overview
- `/sensor-dashboard.html` - sensor dashboard
- `/stt-test.html` - voice dashboard

## Run

```powershell
cd C:\Projects\_active\Super_Marimo\frontend
npm install
npm run dev
```

The app uses the local API endpoints shown in the dashboard and does not require the old React router entrypoint anymore. The Vite build emits the home, sensor, and voice test pages together.
