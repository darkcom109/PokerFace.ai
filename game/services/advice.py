def hand_rank_label(score):
    rank_idx = score[0] if score else -1
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


def suggest(win_prob, pot=0, to_call=0, *, street="preflop", opponents=0, hand_label=""):
    """Return textual advice based on win probability and pot odds."""
    pct = round(win_prob * 100, 1)

    if win_prob >= 0.7:
        action = "raise"
        reason = "Strong equity; pressure the bots and build the pot."
    elif win_prob >= 0.45:
        action = "call/check"
        reason = "Playable equity; realize your hand without inflating the pot."
    else:
        action = "fold/check"
        reason = "Low equity; conserve chips unless odds are exceptional."

    odds_hint = ""
    if to_call:
        odds_hint = f" Pot {pot}, to call {to_call}."

    explanation = (
        f"Win estimate {pct}% on the {street} versus {opponents} active bot(s). "
        f"Your best made hand is {hand_label or 'incomplete'}, which drives this probability. "
        "Opponent count lowers equity; values update as community cards land."
    )

    return {
        "win_prob": pct,
        "suggested_action": action,
        "message": f"Est. win chance {pct}%. {reason}{odds_hint}",
        "explanation": explanation,
        "pot": pot,
        "to_call": to_call,
    }
