import random

RANKS = "23456789TJQKA"
SUITS = "SHDC"


def new_deck():
    """Return a freshly ordered deck."""
    return [r + s for r in RANKS for s in SUITS]


def shuffle(deck):
    random.shuffle(deck)
    return deck


def remaining_deck(excluded):
    excluded_set = set(excluded)
    return [card for card in new_deck() if card not in excluded_set]


def draw(deck, count):
    drawn = deck[:count]
    del deck[:count]
    return drawn


def describe_cards(cards):
    return " ".join(cards)
