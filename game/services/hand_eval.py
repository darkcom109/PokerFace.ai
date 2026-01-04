import itertools
from collections import Counter

RANKS = "23456789TJQKA"
RANK_VALUE = {rank: idx + 2 for idx, rank in enumerate(RANKS)}


def card_value(card):
    return RANK_VALUE[card[0]]


def straight_high(values):
    uniq = sorted(set(values), reverse=True)
    if 14 in uniq:
        uniq.append(1)  # Ace can play low
    for i in range(len(uniq) - 4):
        window = uniq[i : i + 5]
        if window[0] - window[4] == 4 and len(window) == 5:
            return window[0]
    return None


def score_five(cards):
    values = sorted([card_value(card) for card in cards], reverse=True)
    suits = [card[1] for card in cards]
    counts = Counter(values)
    ordered = sorted(counts.items(), key=lambda x: (-x[1], -x[0]))

    is_flush = len(set(suits)) == 1
    straight_top = straight_high(values)

    if is_flush and straight_top:
        return (8, [straight_top])

    if ordered[0][1] == 4:
        quad = ordered[0][0]
        kicker = max(v for v in values if v != quad)
        return (7, [quad, kicker])

    if ordered[0][1] == 3 and len(ordered) > 1 and ordered[1][1] == 2:
        return (6, [ordered[0][0], ordered[1][0]])

    if is_flush:
        return (5, values)

    if straight_top:
        return (4, [straight_top])

    if ordered[0][1] == 3:
        trips = ordered[0][0]
        kickers = [v for v in values if v != trips][:2]
        return (3, [trips] + kickers)

    if ordered[0][1] == 2 and len(ordered) > 1 and ordered[1][1] == 2:
        high_pair, low_pair = ordered[0][0], ordered[1][0]
        kicker = max(v for v in values if v not in (high_pair, low_pair))
        return (2, [high_pair, low_pair, kicker])

    if ordered[0][1] == 2:
        pair = ordered[0][0]
        kickers = [v for v in values if v != pair][:3]
        return (1, [pair] + kickers)

    return (0, values)


def evaluate_best(cards):
    """Return best 5-card score for up to 7 cards."""
    best = (-1, [])
    for combo in itertools.combinations(cards, 5):
        score = score_five(combo)
        if score > best:
            best = score
    return best


def compare(hand_a, hand_b):
    """Compare two (rank, detail) tuples."""
    return (hand_a > hand_b) - (hand_a < hand_b)
