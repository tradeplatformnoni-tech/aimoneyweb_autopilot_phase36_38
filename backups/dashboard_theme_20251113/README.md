# NeoLight Dashboard Theme Backup (2025-11-13)

This snapshot captures the neon HUD dashboard theme deployed on 2025-11-13.  
Use the files in this directory to restore or audit the production styling.

## Contents

- `theme-neon.css` – HUD styling tokens and component rules.
- `dashboard.js` – Client-side logic (charts, auto-refresh, parallax, audio).
- `dashboard.html` – FastAPI template served at `/`.
- `gallery.json` – Metadata for Neo Gallery artwork.

To restore manually:

```bash
cp backups/dashboard_theme_20251113/theme-neon.css dashboard/static/css/theme-neon.css
cp backups/dashboard_theme_20251113/dashboard.js dashboard/static/js/dashboard.js
cp backups/dashboard_theme_20251113/dashboard.html dashboard/templates/dashboard.html
cp backups/dashboard_theme_20251113/gallery.json dashboard/static/data/gallery.json
```

Remember to drop your ambient loop audio in `dashboard/static/audio/ambient_loop.mp3` if you want the ambience toggle active.***

