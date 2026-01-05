# PokerFace.ai

A Django-powered Texas Hold'em trainer with bot opponents, Monte Carlo win equity, heuristic policy hints, and an optional local LLM tipper (via Ollama) layered on top.

<img width="960" height="441" alt="2026-01-05" src="https://github.com/user-attachments/assets/7113133c-3a28-49e7-80e0-d4dbcccd8240" />
<img width="960" height="441" alt="Screenshot 2026-01-05 022818" src="https://github.com/user-attachments/assets/60014b9e-5ffe-489e-962e-1e3deb6d408d" />

## Features
- Fast, session-based play against 4 bots (no DB writes per hand).
- Monte Carlo win probability + heuristic policy advice each street.
- Optional local LLM guidance (Ollama) fetched asynchronously.
- Dashboard with chip top-up, quick table entry, and clean UI with card art.
- All-in handling, showdown hand explanations, and bot card reveal at end.

## Quick start (local dev)
```bash
python -m venv venv
./venv/Scripts/activate          # On Windows PowerShell: .\venv\Scripts\Activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000/.

## Optional: local LLM tips (offline)
1) Install Ollama (https://ollama.com/download) and start it: `ollama serve`.
2) Pull a small model (default in code is `gemma3:4b`): `ollama pull gemma3:4b`.
3) Test it:
   ```powershell
   $body = @{ model = "gemma3:4b"; prompt = "hi"; stream = $false } | ConvertTo-Json
   Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:11434/api/generate" -Method POST -Body $body -ContentType "application/json"
   ```
4) (Optional) Override via env vars: `OLLAMA_MODEL=gemma3:4b` and `OLLAMA_ENDPOINT=http://127.0.0.1:11434/api/generate`.
If the endpoint is up, the app fetches tips in the background; Monte Carlo advice stays instant.

## Gameplay notes
- Turn order is randomized each hand; if bots start, they act once preflop before your turn.
- Equity thresholds: player advice uses ≥70% raise, 45–69% call/check, <45% fold/check. Bots raise at ≥65% (if no pending bet), call at ≥40% otherwise fold.
- All-in: if you shove, bots either call all-in (if they like their equity) or fold; remaining board is dealt and showdown runs.
- Actions are AJAX; no page reload. A brief “thinking” delay simulates bot timing.

## Deploying (summary)
- Use a real server (gunicorn/uvicorn + nginx), set `DEBUG=False`, `ALLOWED_HOSTS`, `SECRET_KEY`, and move to Postgres.
- `python manage.py collectstatic` and serve static via nginx.
- For LLM in production: run an Ollama service on the host (or point `OLLAMA_ENDPOINT` to a hosted model), or disable the tip if you don’t want to ship a model.

## Project structure
- `game/services/` – cards, hand eval, Monte Carlo sim, policy, engine, optional LLM helper.
- `templates/` – Django templates (auth, dashboard, play table).
- `static/game/` – JS (action handling, rendering) and CSS (cards, layout).
- `game/views.py` – session-backed gameplay endpoints and auth flows.
