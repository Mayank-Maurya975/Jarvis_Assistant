# JARVIS — Live Hosting Guide

## Option A: Always-on UI (GitHub Pages)

### Step 1 — Deploy UI to GitHub Pages
1. Create a new GitHub repo: `jarvis-ui`
2. Copy `jarvis_assistant/templates/index.html` into it
3. Go to repo Settings → Pages → Deploy from `main` branch
4. Your permanent URL: `https://yourusername.github.io/jarvis-ui`

### Step 2 — Run JARVIS with public tunnel
```bash
cd jarvis_assistant
python main.py --tunnel
```
Terminal shows:
```
║  Public:  https://xxxx.ngrok-free.app  ║
```

### Step 3 — Connect UI to backend
In `index.html`, find this line near the top of the `<script>` block:
```js
const JARVIS_URL = window.JARVIS_BACKEND_URL || window.location.origin;
```
Add above it:
```js
window.JARVIS_BACKEND_URL = "https://xxxx.ngrok-free.app";
```
Push to GitHub → anyone visits your GitHub Pages URL → connects to your live JARVIS.

---

## Option B: Cloudflare Tunnel (free, permanent URL)

```bash
# Install once
winget install Cloudflare.cloudflared

# Run every time you start JARVIS
cloudflared tunnel --url http://localhost:8080
```
Gives you a permanent `https://xxxx.trycloudflare.com` URL.

---

## When JARVIS is offline
The UI still loads and shows **OFFLINE** status.
When you start JARVIS again, it auto-reconnects within 3 seconds.
