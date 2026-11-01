# VPS Demo (Render free tier)

Lightweight VPS-like demo: dashboard, allowlist-only commands (no shell), and file listing confined to `demo_files/`.

Run locally:

```
pip install -r requirements.txt
APP_PASSWORD=your-code python app.py
```

Deploy on Render: create a Free Web Service in Frankfurt from this repo, set `APP_PASSWORD` as an environment variable in the Render dashboard (do NOT commit it here), build `pip install -r requirements.txt`, start `gunicorn app:app --bind 0.0.0.0:$PORT`.

Limits: no SSH, no persistent disk on the free tier, 512 MB RAM, sleeps after 15 minutes without traffic.
