from . import cards
import random

DEFAULT_STACK = 500
DEFAULT_BOTS = 4


def new_game(num_bots=DEFAULT_BOTS):
    return new_hand(num_bots=num_bots)


def new_hand(prev_state=None, num_bots=DEFAULT_BOTS, starting_stack=DEFAULT_STACK):
    """Start a fresh hand; reuse existing stacks if prev_state is provided."""
    # Always seat DEFAULT_BOTS to avoid carrying over larger tables from prior state
    num_bots = DEFAULT_BOTS
    player_first = random.choice([True, False])
    if prev_state:
        prev_bots = prev_state.get("bots", [])
        player_stack = prev_state.get("player", {}).get("stack", starting_stack)
        bot_stacks = [b.get("stack", starting_stack) for b in prev_bots[:num_bots]]
    else:
        player_stack = starting_stack
        bot_stacks = [starting_stack] * num_bots

    deck = cards.new_deck()
    cards.shuffle(deck)

    player_hand = cards.draw(deck, 2)
    bots = []
    for idx in range(num_bots):
        bot_hand = cards.draw(deck, 2)
        bots.append(
            {
                "name": f"Bot {idx + 1}",
                "hand": bot_hand,
                "stack": bot_stacks[idx] if idx < len(bot_stacks) else starting_stack,
                "folded": False,
            }
        )

    state = {
        "deck": deck,
        "player": {
            "name": "You",
            "hand": player_hand,
            "stack": player_stack,
            "folded": False,
            "all_in": False,
        },
        "bots": bots,
        "community": [],
        "street": "preflop",
        "pot": 0,
        "pending_call": 0,  # amount player must call to see next card
        "raise_done": False,  # cap raises per street
        "log": ["New hand started."],
        "last_advice": None,
        "player_first": player_first,
        "opening_done": player_first,  # if bots start, we'll run them once and flip this
    }
    return state


def load(session):
    state = session.get("game_state")
    if state and len(state.get("bots", [])) > DEFAULT_BOTS:
        state["bots"] = state["bots"][:DEFAULT_BOTS]
    return state


def save(session, state):
    session["game_state"] = state
