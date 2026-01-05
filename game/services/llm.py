import json
import os
import urllib.error
import urllib.request


def summarize_state(state, win_prob, policy_hint):
    player = state.get("player", {})
    bots = state.get("bots", [])
    board = " ".join(state.get("community") or []) or "none"
    hero = " ".join(player.get("hand") or []) or "unknown"
    pending = state.get("pending_call", 0)
    bot_bits = []
    for bot in bots:
        status = "folded" if bot.get("folded") else "in"
        bot_bits.append(f"{bot.get('name')} ({status}, stack {bot.get('stack')})")
    opponents = "; ".join(bot_bits) or "none"
    policy_text = f"{policy_hint['action']} - {policy_hint['reason']}" if policy_hint else "none"
    pct = int(win_prob * 100)
    return (
        "You are an assistant giving concise poker tips. "
        "Use plain language, one sentence, no emojis. "
        f"Hero hand: {hero}. Board: {board}. "
        f"Street: {state.get('street')}, pot: {state.get('pot')}, to call: {pending}. "
        f"Opponents: {opponents}. Estimated win probability: {pct}%. "
        f"Heuristic policy: {policy_text}. "
        "Give an actionable tip for the hero's next decision."
    )


def query_ollama(prompt, *, timeout=8):
    """
    Hit a local Ollama server if available.
    Returns text or None if unavailable.
    """
    endpoint = os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/generate")
    # Default to the lighter gemma3:4b model for lower latency; env var can override.
    model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 60,  # keep replies snappy
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return None

    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    resp = parsed.get("response")
    if isinstance(resp, str):
        resp = resp.strip()
    return resp or None


def ai_guidance(state, win_prob, policy_hint):
    """
    Optional LLM-based guidance layered on top of Monte Carlo + heuristics.
    Safe to fail silently if no model/server is running.
    """
    prompt = summarize_state(state, win_prob, policy_hint)
    return query_ollama(prompt)
