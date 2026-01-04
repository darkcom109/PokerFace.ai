import random
from . import cards, hand_eval


def estimate_win_prob(player_cards, community_cards, num_opponents=2, iterations=400, deck=None):
    """Monte Carlo win probability vs num_opponents."""
    used = list(player_cards) + list(community_cards)
    base_deck = list(deck) if deck is not None else cards.remaining_deck(used)

    wins = ties = 0
    total = 0
    for _ in range(iterations):
        shuffled = base_deck[:]
        random.shuffle(shuffled)

        community_needed = 5 - len(community_cards)
        community_draw = shuffled[:community_needed]
        del shuffled[:community_needed]

        opp_hands = []
        for _ in range(num_opponents):
            opp_hand = shuffled[:2]
            del shuffled[:2]
            opp_hands.append(opp_hand)

        board = list(community_cards) + community_draw
        player_score = hand_eval.evaluate_best(player_cards + board)
        opp_scores = [hand_eval.evaluate_best(hole + board) for hole in opp_hands]
        best_opp = max(opp_scores) if opp_scores else None

        total += 1
        if best_opp is None or player_score > best_opp:
            wins += 1
        elif player_score == best_opp:
            ties += 1

    return (wins + ties * 0.5) / total if total else 0.0
