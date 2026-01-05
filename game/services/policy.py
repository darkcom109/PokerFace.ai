from . import hand_eval


def evaluate_draws(cards):
    suits = {}
    ranks = []
    for c in cards:
        suits[c[1]] = suits.get(c[1], 0) + 1
        ranks.append(hand_eval.card_value(c))
    flush_draw = any(count >= 4 for count in suits.values())

    uniq = sorted(set(ranks))
    if 14 in uniq:
        uniq.append(1)
    straight_draw = False
    for i in range(len(uniq) - 3):
        window = uniq[i : i + 4]
        if window[-1] - window[0] <= 4 and len(window) == 4:
            straight_draw = True
            break
    return flush_draw, straight_draw


def recommend(state, win_prob):
    """
    Lightweight heuristic "policy" layered on top of Monte Carlo equity.
    Returns an action hint and reason string.
    """
    street = state.get("street", "preflop")
    pending = state.get("pending_call", 0)
    pot = state.get("pot", 0)
    player = state.get("player", {})
    hero_cards = (player.get("hand") or []) + (state.get("community") or [])
    best_score = hand_eval.evaluate_best(hero_cards)
    rank_label = hand_eval_rank_label(best_score[0])
    flush_draw, straight_draw = evaluate_draws(hero_cards)

    reason_bits = []
    if flush_draw:
        reason_bits.append("flush draw")
    if straight_draw:
        reason_bits.append("straight draw")
    reason_bits.append(f"best hand: {rank_label}")
    reason_bits.append(f"equity: {int(win_prob*100)}%")

    if win_prob >= 0.7:
        action = "raise"
    elif win_prob >= 0.45:
        action = "call" if pending else "check"
    elif flush_draw or straight_draw:
        action = "call" if pending <= pot * 0.2 else "fold"
    else:
        action = "fold" if pending else "check"

    reason = " / ".join(reason_bits)
    return {"action": action, "reason": reason}


def hand_eval_rank_label(rank_idx):
    labels = [
        "high card",
        "pair",
        "two pair",
        "three of a kind",
        "straight",
        "flush",
        "full house",
        "four of a kind",
        "straight flush",
    ]
    return labels[rank_idx] if 0 <= rank_idx < len(labels) else "unknown"
