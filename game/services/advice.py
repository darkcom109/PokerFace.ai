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


def suggest(
    win_prob,
    pot=0,
    to_call=0,
    *,
    street="preflop",
    opponents=0,
    hand_label="",
    board_cards=0,
    policy_note=None,
    ai_note=None,
):
    """Return textual advice based on win probability and pot odds, with explanation."""
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

    stage = street or "preflop"
    board_desc = f"{board_cards} community card(s) shown" if board_cards else "no board yet"
    made = hand_label or "no made hand"
    opp_text = f"{opponents} active bot(s)" if opponents else "no active bots"
    explanation = (
        f"Win estimate {pct}% on the {stage}: {board_desc}, best made hand {made}, versus {opp_text}. "
        "Monte Carlo sim fills remaining cards and deals bot hole cards; more opponents and weaker made strength lower equity. "
        "Probabilities refresh each street as more cards are known."
    )
    if policy_note:
        explanation += f" Policy hint: {policy_note}"
    if ai_note:
        explanation += f" AI guidance: {ai_note}"

    return {
        "win_prob": pct,
        "suggested_action": action,
        "message": f"Est. win chance {pct}%. {reason}{odds_hint}",
        "explanation": explanation,
        "pot": pot,
        "to_call": to_call,
        "ai_note": ai_note,
    }
