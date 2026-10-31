"""Assertion demo for nim_game.py.

Run: python3 -m pytest
"""

import random

import nim_game as ng


def test_strategy_always_wins_from_winning_position():
    rng = random.Random(1)
    # 20 stones with the strategy player moving first is a winning
    # position (20 mod 4 != 1), so it must win every game.
    for _ in range(200):
        winner, _ = ng.play_game(20, ("strategy", ng.strategy_move),
                                 ("random", ng.random_move), rng)
        assert winner == "strategy", "strategy player lost a won game"
    # Second check: random starts at 21 (remainder 1 = losing for random).
    for _ in range(200):
        winner, _ = ng.play_game(21, ("random", ng.random_move),
                                 ("strategy", ng.strategy_move), rng)
        assert winner == "strategy", "strategy player lost a won game"


def test_box_update_rule():
    computer = ng.BoxComputer()
    assert computer.boxes[3] == {"red": 1, "yellow": 1, "grey": 1}
    assert computer.storage == {"red": 7, "yellow": 7, "grey": 7}

    # Win: chip goes back and one identical chip comes from storage.
    computer.drawn = [(3, "yellow")]
    computer.learn(computer_won=True)
    assert computer.boxes[3]["yellow"] == 2
    assert computer.storage["yellow"] == 6

    # Loss: drawn chip leaves the box and goes into storage.
    computer.drawn = [(4, "red")]
    computer.learn(computer_won=False)
    assert computer.boxes[4]["red"] == 0
    assert computer.storage["red"] == 8

    # Total number of chips per colour stays 10.
    for c in ng.COLORS:
        total = computer.storage[c] + sum(computer.boxes[n][c]
                                          for n in (2, 3, 4))
        assert total == ng.CHIPS_PER_COLOR


if __name__ == "__main__":
    test_strategy_always_wins_from_winning_position()
    test_box_update_rule()
    print("All tests passed.")
