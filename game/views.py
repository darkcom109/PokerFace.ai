from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .services import engine, state as state_svc
from .forms import SignUpForm


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
