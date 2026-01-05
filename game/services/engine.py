from . import cards, hand_eval, simulation, advice, policy, llm

CALL_AMOUNT = 10
RAISE_AMOUNT = 20
ADVICE_ITERATIONS = 350


def ensure_advice(state):
    if state.get("street") == "hand_over" or state["player"].get("folded"):
        state["last_advice"] = None
        return

    active_bots = sum(1 for bot in state["bots"] if not bot.get("folded"))
    best_score = hand_eval.evaluate_best(state["player"]["hand"] + state["community"])
    hand_label = advice.hand_rank_label(best_score)
    win_prob = simulation.estimate_win_prob(
        state["player"]["hand"],
        state["community"],
        num_opponents=active_bots,
        iterations=ADVICE_ITERATIONS,
        deck=state["deck"],
    )
    pending = state.get("pending_call", 0) or CALL_AMOUNT
    to_call = min(pending, state["player"]["stack"])
    policy_hint = policy.recommend(state, win_prob)
    prev_ai = state.get("last_advice", {}).get("ai_note") if state.get("last_advice") else None
    llm_note = llm.ai_guidance(state, win_prob, policy_hint) or prev_ai
    state["last_equity"] = win_prob
    state["last_policy"] = policy_hint
    state["last_advice"] = advice.suggest(
        win_prob,
        pot=state["pot"],
        to_call=to_call,
        street=state.get("street", "preflop"),
        opponents=active_bots,
        hand_label=hand_label,
        board_cards=len(state["community"]),
        policy_note=f"{policy_hint['action']} - {policy_hint['reason']}",
        ai_note=llm_note or "AI tip pending...",
    )


def apply_player_move(state, move):
    events = []
    player = state["player"]
    pending = state.get("pending_call", 0)

    if state.get("street") == "hand_over":
        msg = "Hand is over. Start a new hand to play again."
        events.append(msg)
        state["log"].append(msg)
        ensure_advice(state)
        return state, events

    if move == "fold":
        player["folded"] = True
        msg = "You folded. Hand ends."
        events.append(msg)
        state["log"].append(msg)
        state["pending_call"] = 0
        player["all_in"] = False
        award_uncontested(state, events)
        state["last_advice"] = None
        return state, events

    if move == "allin":
        bet = player["stack"]
        player["stack"] = 0
        state["pot"] += bet
        player["all_in"] = True
        state["pending_call"] = max(pending - bet, 0)
        state["raise_done"] = True
        msg = f"You go all-in for {bet}."
    elif move == "raise":
        total_bet = (pending or 0) + RAISE_AMOUNT
        bet = min(total_bet, player["stack"])
        player["stack"] -= bet
        state["pot"] += bet
        state["pending_call"] = RAISE_AMOUNT
        state["raise_done"] = True
        msg = f"You raise {bet}."
    elif move == "call":
        due = pending if pending else CALL_AMOUNT
        bet = min(due, player["stack"])
        player["stack"] -= bet
        state["pot"] += bet
        state["pending_call"] = max(pending - bet, 0)
        if player["stack"] == 0:
            player["all_in"] = True
        msg = f"You call {bet}." if bet else "You check."
    else:
        msg = "You check."
    events.append(msg)
    state["log"].append(msg)

    bot_events = bots_act(state)
    events.extend(bot_events)

    if award_uncontested(state, events):
        ensure_advice(state)
        return state, events

    if player.get("all_in"):
        deal_remaining_board(state, events)
        showdown(state, events)
        ensure_advice(state)
        return state, events

    if state.get("pending_call", 0) > 0:
        ensure_advice(state)
        return state, events

    if state["street"] == "river":
        showdown(state, events)
    else:
        advance_board(state, events)
        if state["street"] == "river":
            showdown(state, events)

    ensure_advice(state)
    return state, events


def bots_act(state):
    events = []
    pending = state.get("pending_call", 0)
    raise_allowed = not state.get("raise_done", False)
    player_all_in = state.get("player", {}).get("all_in", False)
    for bot in state["bots"]:
        if bot.get("folded"):
            continue

        if bot["stack"] <= 0:
            action = f"{bot['name']} is all-in."
            events.append(action)
            state["log"].append(action)
            continue

        bot_prob = simulation.estimate_win_prob(
            bot["hand"], state["community"], num_opponents=1, iterations=200, deck=state["deck"]
        )

        if raise_allowed and pending == 0 and bot_prob >= 0.65 and not player_all_in:
            bet = min(RAISE_AMOUNT, bot["stack"])
            bot["stack"] -= bet
            state["pot"] += bet
            state["pending_call"] = bet  # player must call this raise
            state["raise_done"] = True
            action = f"{bot['name']} raises {bet}."
        elif bot_prob >= 0.4:
            bet = min(pending if pending else CALL_AMOUNT, bot["stack"])
            bot["stack"] -= bet
            state["pot"] += bet
            action = f"{bot['name']} calls {bet}." if bet else f"{bot['name']} checks (all-in)."
        else:
            bot["folded"] = True
            action = f"{bot['name']} folds."

        events.append(action)
        state["log"].append(action)
    return events


def advance_board(state, events):
    deck = state["deck"]
    street = state["street"]
    state["pending_call"] = 0
    state["raise_done"] = False
    state["player"]["all_in"] = False

    if street == "preflop":
        state["community"].extend(cards.draw(deck, 3))
        state["street"] = "flop"
        events.append("Flop dealt.")
    elif street == "flop":
        state["community"].extend(cards.draw(deck, 1))
        state["street"] = "turn"
        events.append("Turn dealt.")
    elif street == "turn":
        state["community"].extend(cards.draw(deck, 1))
        state["street"] = "river"
        events.append("River dealt.")


def showdown(state, events):
    active = []
    if not state["player"].get("folded"):
        active.append(("You", state["player"]["hand"]))
    for bot in state["bots"]:
        if not bot.get("folded"):
            active.append((bot["name"], bot["hand"]))

    if not active:
        msg = "Everyone folded. Hand over."
        events.append(msg)
        state["log"].append(msg)
        state["street"] = "hand_over"
        return

    board = state["community"]
    scored = [(name, hand, hand_eval.evaluate_best(hand + board)) for name, hand in active]
    best_score = max(score for _, _, score in scored)
    winners = [name for name, _, score in scored if score == best_score]

    payout_events = []
    if winners:
        share = state["pot"] // len(winners)
        remainder = state["pot"] % len(winners)
        for idx, name in enumerate(winners):
            payout = share + (1 if idx < remainder else 0)
            if name == "You":
                state["player"]["stack"] += payout
            else:
                for bot in state["bots"]:
                    if bot["name"] == name:
                        bot["stack"] += payout
                        break
            payout_events.append(f"{name} receives {payout}.")

    if "You" in winners and len(winners) == 1:
        msg = "Showdown: you win the pot!"
    elif "You" in winners:
        msg = f"Showdown: split pot between {', '.join(winners)}."
    else:
        msg = f"Showdown: {', '.join(winners)} win(s)."

    events.append(msg)
    state["log"].append(msg)
    # Explain best hands
    for name, hand, score in scored:
        label = advice.hand_rank_label(score)
        hand_str = " ".join(hand)
        detail = f"{name} shows {hand_str} ({label})."
        events.append(detail)
        state["log"].append(detail)
    for pe in payout_events:
        events.append(pe)
        state["log"].append(pe)
    state["pot"] = 0
    state["street"] = "hand_over"
    state["pending_call"] = 0
    state["player"]["all_in"] = False
    state["pending_call"] = 0
    state["raise_done"] = False
    state["pending_call"] = 0


def award_uncontested(state, events):
    active = []
    if not state["player"].get("folded"):
        active.append(("You", state["player"]))
    for bot in state["bots"]:
        if not bot.get("folded"):
            active.append((bot["name"], bot))

    if len(active) == 1:
        # Deal remaining board for transparency, then showdown
        deal_remaining_board(state, events)
        showdown(state, events)
        return True
    return False


def deal_remaining_board(state, events):
    deck = state["deck"]
    while len(state["community"]) < 5 and deck:
        state["community"].extend(cards.draw(deck, 1))
    if len(state["community"]) == 5:
        state["street"] = "river"
    state["pending_call"] = 0
    state["raise_done"] = False
