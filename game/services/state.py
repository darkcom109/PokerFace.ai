from . import cards

DEFAULT_STACK = 500
DEFAULT_BOTS = 5


def new_game(num_bots=DEFAULT_BOTS):
    return new_hand(num_bots=num_bots)


def new_hand(prev_state=None, num_bots=DEFAULT_BOTS, starting_stack=DEFAULT_STACK):
    """Start a fresh hand; reuse existing stacks if prev_state is provided."""
    if prev_state:
        prev_bots = prev_state.get("bots", [])
        num_bots = max(len(prev_bots), num_bots, DEFAULT_BOTS)
        player_stack = prev_state.get("player", {}).get("stack", starting_stack)
        bot_stacks = [b.get("stack", starting_stack) for b in prev_bots]
    else:
        num_bots = max(num_bots, DEFAULT_BOTS)
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
        "player": {"name": "You", "hand": player_hand, "stack": player_stack, "folded": False},
        "bots": bots,
        "community": [],
        "street": "preflop",
        "pot": 0,
        "log": ["New hand started."],
        "last_advice": None,
    }
    return state


def load(session):
    return session.get("game_state")


def save(session, state):
    session["game_state"] = state
