from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import SignUpForm
from .services import engine, state as state_svc, simulation, policy, llm, advice, hand_eval


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    state = state_svc.load(request.session)
    summary = None
    if state:
        summary = {
            "street": state.get("street"),
            "pot": state.get("pot"),
            "player_stack": state.get("player", {}).get("stack"),
            "bots": state.get("bots", []),
        }
    return render(request, "game/dashboard.html", {"summary": summary})


@login_required
def play(request):
    state = state_svc.load(request.session)
    if state is None or state.get("street") == "hand_over":
        state = state_svc.new_game()
    engine.maybe_opening_bots(state)
    engine.ensure_advice(state)
    state_svc.save(request.session, state)
    is_over = state.get("street") == "hand_over" or state.get("player", {}).get("folded")
    return render(
        request,
        "game/play.html",
        {
            "state": state,
            "call_amount": engine.CALL_AMOUNT,
            "raise_amount": engine.RAISE_AMOUNT,
            "is_over": is_over,
        },
    )


@login_required
def new_hand(request):
    prev = state_svc.load(request.session)
    state = state_svc.new_hand(prev_state=prev)
    # If bots are set to start, let them act once before rendering play.
    engine.maybe_opening_bots(state)
    engine.ensure_advice(state)
    state_svc.save(request.session, state)
    return redirect("play")


@login_required
def player_action(request, move):
    state = state_svc.load(request.session) or state_svc.new_game()
    state, events = engine.apply_player_move(state, move)
    state_svc.save(request.session, state)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"events": events, "state": state})
    return redirect("play")


@login_required
def collect_chips(request):
    state = state_svc.load(request.session) or state_svc.new_game()
    state["player"]["stack"] += 100
    # Don't clutter hand log with bonus info; keep this quiet.
    state_svc.save(request.session, state)
    return redirect("dashboard")


def logout_get(request):
    """Allow logout via GET for convenience; redirects home."""
    logout(request)
    return redirect("home")


@login_required
def ai_tip(request):
    """
    Return only the LLM tip without blocking the main gameplay flow.
    """
    state = state_svc.load(request.session)
    if not state:
        return JsonResponse({"ai_note": None}, status=400)
    if state.get("street") == "hand_over" or state.get("player", {}).get("folded"):
        return JsonResponse({"ai_note": None}, status=400)

    # Ensure we have an equity estimate to drive the prompt.
    win_prob = state.get("last_equity")
    if win_prob is None:
        active_bots = sum(1 for bot in state.get("bots", []) if not bot.get("folded"))
        win_prob = simulation.estimate_win_prob(
            state.get("player", {}).get("hand", []),
            state.get("community", []),
            num_opponents=active_bots,
            iterations=engine.ADVICE_ITERATIONS,
            deck=state.get("deck"),
        )
        state["last_equity"] = win_prob
    policy_hint = state.get("last_policy") or policy.recommend(state, win_prob)

    note = llm.ai_guidance(state, win_prob, policy_hint)
    if note:
        # Update advice in session so UI renders the real tip on next refresh.
        if not state.get("last_advice"):
            best_score = hand_eval.evaluate_best(
                (state.get("player", {}).get("hand", []) or []) + (state.get("community", []) or [])
            )
            state["last_advice"] = {
                "win_prob": round(win_prob * 100, 1),
                "suggested_action": policy_hint["action"],
                "message": "",
                "explanation": advice.hand_rank_label(best_score),
                "ai_note": note,
            }
        else:
            state["last_advice"]["ai_note"] = note
            base_expl = state["last_advice"].get("explanation", "") or ""
            if "AI guidance:" in base_expl:
                base_expl = base_expl.split("AI guidance:")[0].strip()
            state["last_advice"]["explanation"] = (base_expl + f" AI guidance: {note}").strip()
        state_svc.save(request.session, state)
        return JsonResponse({"ai_note": note})

    # Return a friendly unavailable message to avoid indefinite "pending".
    return JsonResponse({"ai_note": "AI tip unavailable right now; will retry shortly."}, status=202)
