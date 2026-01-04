from . import cards, hand_eval, simulation, advice

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
    to_call = min(CALL_AMOUNT, state["player"]["stack"])
    state["last_advice"] = advice.suggest(
        win_prob,
        pot=state["pot"],
        to_call=to_call,
        street=state.get("street", "preflop"),
        opponents=active_bots,
        hand_label=hand_label,
    )


def apply_player_move(state, move):
    events = []
    player = state["player"]

    if state.get("street") == "hand_over":
        msg = "Hand is over. Start a new hand to play again."
        events.append(msg)
        state["log"].append(msg)
        ensure_advice(state)
        return state, events

    if move == "fold":
        player["folded"] = True
        msg = "You folded. Hand over."
        events.append(msg)
        state["log"].append(msg)
        state["street"] = "hand_over"
        state["last_advice"] = None
        return state, events

    if move == "raise":
        bet = min(RAISE_AMOUNT, player["stack"])
        player["stack"] -= bet
        state["pot"] += bet
        msg = f"You raise {bet}."
    elif move == "call":
        bet = min(CALL_AMOUNT, player["stack"])
        player["stack"] -= bet
        state["pot"] += bet
        msg = f"You call {bet}." if bet else "You check."
    else:
        msg = "You check."
    events.append(msg)
    state["log"].append(msg)

    bot_events = bots_act(state)
    events.extend(bot_events)

    if player.get("folded") or not any(not b.get("folded") for b in state["bots"]):
        state["street"] = "hand_over"
    else:
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

        if bot_prob >= 0.65:
            bet = min(RAISE_AMOUNT, bot["stack"])
            bot["stack"] -= bet
            state["pot"] += bet
            action = f"{bot['name']} raises {bet}."
        elif bot_prob >= 0.4:
            bet = min(CALL_AMOUNT, bot["stack"])
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
    scores = [(name, hand_eval.evaluate_best(hand + board)) for name, hand in active]
    best_score = max(score for _, score in scores)
    winners = [name for name, score in scores if score == best_score]

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
    for pe in payout_events:
        events.append(pe)
        state["log"].append(pe)
    state["pot"] = 0
    state["street"] = "hand_over"
