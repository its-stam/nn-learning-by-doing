"""Digital simulation of the NIM game (misere variant) in three phases.

Rules (classroom version of the game):
- Players alternately remove 1, 2 or 3 stones.
- Whoever takes the last stone loses.

Phase 1: 20 stones, two random players, 10 games.
Phase 2: 20 stones (4 rows of 5), the opponent always starts,
         random opponent vs. strategy player, 10 games.
Phase 3: 5 stones, the human starts. The "computer" draws a coloured chip
         blindly from the box that matches the number of stones left
         (2 -> left box, 3 -> middle box, 4 -> right box).
         Red = take 1, yellow = take 2, grey = take 3.
         Computer wins: chip goes back and an identical chip from storage
         is added. Computer loses: chip goes from the box into storage.

Run: python3 nim_game.py (needs matplotlib and ffmpeg)
"""

import csv
import random
from pathlib import Path

SEED = 2026
OUT_DIR = Path(__file__).resolve().parent
IMG_DIR = OUT_DIR / "images"

COLORS = ("red", "yellow", "grey")
TAKE = {"red": 1, "yellow": 2, "grey": 3}
PLOT_COLORS = {"red": "#d62728", "yellow": "#e6b800", "grey": "#7f7f7f"}
BOX_NAMES = {2: "left box (2 left)", 3: "middle box (3 left)",
             4: "right box (4 left)"}

# Start setup of the classroom game: each box holds one chip of every
# colour, the remaining chips (10 per colour in total) lie in storage.
CHIPS_PER_COLOR = 10
FIG_SIZE = (19.2, 10.8)
DPI = 100


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------
def random_move(stones, rng):
    """Take 1 to 3 stones at random, never more than are left."""
    return rng.randint(1, min(3, stones))


def strategy_move(stones, rng):
    """Winning strategy: leave the opponent a count with remainder 1 mod 4.

    If that is not possible (we already face such a count), take one stone
    and hope the opponent makes a mistake.
    """
    take = (stones - 1) % 4
    if take == 0:
        return 1
    return take


def play_game(stones, first, second, rng):
    """Play one misere NIM game.

    first, second: (name, move_function).
    Returns (winner_name, list of (player_name, taken)).
    """
    players = (first, second)
    turn = 0
    moves = []
    while stones > 0:
        name, move = players[turn % 2]
        take = move(stones, rng)
        if not 1 <= take <= min(3, stones):
            raise ValueError(f"illegal move {take} with {stones} stones")
        stones -= take
        moves.append((name, take))
        if stones == 0:
            # The player who took the last stone loses.
            return players[(turn + 1) % 2][0], moves
        turn += 1
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------------------
# Phase 3: learning box computer
# ---------------------------------------------------------------------------
class BoxComputer:
    """Matchbox learner (MENACE-like)."""

    def __init__(self):
        self.boxes = {n: {c: 1 for c in COLORS} for n in (2, 3, 4)}
        used = {c: sum(self.boxes[n][c] for n in self.boxes) for c in COLORS}
        self.storage = {c: CHIPS_PER_COLOR - used[c] for c in COLORS}
        self.drawn = []

    def move(self, stones, rng):
        """Draw a chip blindly from the box for the current stone count."""
        if stones == 1:
            # No box for one stone: the computer must take the last one.
            return 1
        box = self.boxes[stones]
        bag = [c for c in COLORS for _ in range(box[c])]
        if not bag:
            # Empty box (not reached with this setup): take one stone.
            return 1
        color = rng.choice(bag)
        self.drawn.append((stones, color))
        # Assumption: a grey chip with only 2 stones left means the computer
        # takes all remaining stones, so it takes the last one and loses.
        return min(TAKE[color], stones)

    def learn(self, computer_won):
        """Reward or punish every chip drawn in this game."""
        for stones, color in self.drawn:
            if computer_won:
                if self.storage[color] > 0:
                    self.storage[color] -= 1
                    self.boxes[stones][color] += 1
            elif self.boxes[stones][color] > 0:
                self.boxes[stones][color] -= 1
                self.storage[color] += 1
        self.drawn = []

    def snapshot(self):
        return {n: dict(self.boxes[n]) for n in (2, 3, 4)}


def run_phase3(human_move, games, rng):
    computer = BoxComputer()
    history = []
    for game in range(1, games + 1):
        winner, moves = play_game(5, ("human", human_move),
                                  ("computer", computer.move), rng)
        computer.learn(winner == "computer")
        history.append({"game": game, "winner": winner, "moves": moves,
                        "boxes": computer.snapshot()})
    return history


def optimal_human(stones, rng):
    """Perfect player: leave remainder 1 mod 4, otherwise play randomly."""
    take = (stones - 1) % 4
    if take == 0:
        return random_move(stones, rng)
    return take


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def _pyplot():
    """Import matplotlib only when plotting, so the game logic runs without it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def moves_text(moves):
    short = {"A": "A", "B": "B", "random": "R", "strategy": "S",
             "human": "H", "computer": "C"}
    return " ".join(f"{short[n]}{t}" for n, t in moves)


def write_csv(rows, path):
    header = ["phase", "run", "game", "winner", "moves"]
    header += [f"box{n}_{c}" for n in (2, 3, 4) for c in COLORS]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def plot_phase12(p1_wins, p2_wins, path):
    plt = _pyplot()
    fig, axes = plt.subplots(1, 2, figsize=FIG_SIZE, dpi=DPI)
    data = [(axes[0], p1_wins, "Phase 1: random A vs. random B (20 stones)"),
            (axes[1], p2_wins,
             "Phase 2: random (starts) vs. strategy (20 stones)")]
    for ax, wins, title in data:
        names = list(wins)
        bars = ax.bar(names, [wins[n] for n in names],
                      color=["#1f77b4", "#ff7f0e"], width=0.5)
        ax.bar_label(bars, fontsize=28)
        ax.set_ylim(0, 10.5)
        ax.set_ylabel("Wins out of 10 games", fontsize=22)
        ax.set_title(title, fontsize=22)
        ax.tick_params(labelsize=20)
    fig.suptitle("NIM game: wins in phase 1 and phase 2", fontsize=30)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_boxes(histories, path):
    plt = _pyplot()
    fig, axes = plt.subplots(2, 3, figsize=FIG_SIZE, dpi=DPI, sharey=True)
    for row, (label, history) in enumerate(histories):
        games = [h["game"] for h in history]
        for col, n in enumerate((2, 3, 4)):
            ax = axes[row][col]
            for c in COLORS:
                ax.plot(games, [h["boxes"][n][c] for h in history],
                        color=PLOT_COLORS[c], lw=3,
                        label=f"{c} (take {TAKE[c]})")
            ax.set_title(f"{BOX_NAMES[n]}, vs. {label} human", fontsize=17)
            ax.set_xlabel("Game", fontsize=15)
            ax.tick_params(labelsize=14)
            ax.grid(alpha=0.3)
        axes[row][0].set_ylabel("Chips in box", fontsize=15)
    axes[0][0].legend(fontsize=14)
    fig.suptitle("Phase 3: chips per colour in each box after every game",
                 fontsize=26)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def rolling(values, window):
    out = []
    for i in range(len(values)):
        part = values[max(0, i - window + 1):i + 1]
        out.append(sum(part) / len(part))
    return out


def plot_win_rate(histories, path, window=10):
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=DPI)
    for (label, history), color in zip(histories, ("#1f77b4", "#d62728")):
        wins = [1 if h["winner"] == "computer" else 0 for h in history]
        ax.plot([h["game"] for h in history],
                [100 * v for v in rolling(wins, window)],
                lw=4, color=color, label=f"vs. {label} human")
    ax.set_ylim(0, 105)
    ax.set_xlabel("Game", fontsize=22)
    ax.set_ylabel(f"Computer win rate, last {window} games (%)", fontsize=22)
    ax.set_title("Phase 3: the box computer learns to win", fontsize=30)
    ax.tick_params(labelsize=18)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=20)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def animate_boxes(history, path, fps=4):
    plt = _pyplot()
    from matplotlib import animation

    fig, axes = plt.subplots(1, 3, figsize=FIG_SIZE, dpi=DPI, sharey=True)
    ymax = max(h["boxes"][n][c] for h in history
               for n in (2, 3, 4) for c in COLORS) + 1
    start = {n: {c: 1 for c in COLORS} for n in (2, 3, 4)}
    frames = [{"game": 0, "winner": "-", "boxes": start}] + history
    frames += [history[-1]] * (2 * fps)  # hold the final state

    bars = {}
    for ax, n in zip(axes, (2, 3, 4)):
        bars[n] = ax.bar(COLORS, [1, 1, 1],
                         color=[PLOT_COLORS[c] for c in COLORS])
        ax.set_ylim(0, ymax)
        ax.set_title(BOX_NAMES[n], fontsize=24)
        ax.tick_params(labelsize=20)
    axes[0].set_ylabel("Chips in box", fontsize=22)
    title = fig.suptitle("", fontsize=30)
    fig.tight_layout(rect=(0, 0, 1, 0.92))

    def update(i):
        frame = frames[i]
        for n in (2, 3, 4):
            for bar, c in zip(bars[n], COLORS):
                bar.set_height(frame["boxes"][n][c])
        title.set_text(f"Phase 3: box computer learning, game "
                       f"{frame['game']}, winner: {frame['winner']}")
        return [b for n in bars for b in bars[n]] + [title]

    anim = animation.FuncAnimation(fig, update, frames=len(frames))
    writer = animation.FFMpegWriter(
        fps=fps, codec="libx264",
        extra_args=["-pix_fmt", "yuv420p", "-profile:v", "high"])
    anim.save(path, writer=writer, dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    rng = random.Random(SEED)
    rows = []

    p1_wins = {"A": 0, "B": 0}
    for game in range(1, 11):
        winner, moves = play_game(20, ("A", random_move),
                                  ("B", random_move), rng)
        p1_wins[winner] += 1
        rows.append({"phase": 1, "run": "random_vs_random", "game": game,
                     "winner": winner, "moves": moves_text(moves)})

    p2_wins = {"random": 0, "strategy": 0}
    for game in range(1, 11):
        winner, moves = play_game(20, ("random", random_move),
                                  ("strategy", strategy_move), rng)
        p2_wins[winner] += 1
        rows.append({"phase": 2, "run": "random_vs_strategy", "game": game,
                     "winner": winner, "moves": moves_text(moves)})

    games = 80
    histories = [("random", run_phase3(random_move, games, rng)),
                 ("optimal", run_phase3(optimal_human, games, rng))]
    for label, history in histories:
        for h in history:
            row = {"phase": 3, "run": f"computer_vs_{label}_human",
                   "game": h["game"], "winner": h["winner"],
                   "moves": moves_text(h["moves"])}
            for n in (2, 3, 4):
                for c in COLORS:
                    row[f"box{n}_{c}"] = h["boxes"][n][c]
            rows.append(row)

    write_csv(rows, OUT_DIR / "results.csv")
    IMG_DIR.mkdir(exist_ok=True)
    plot_phase12(p1_wins, p2_wins, IMG_DIR / "phase12_results.png")
    plot_boxes(histories, IMG_DIR / "phase3_boxes.png")
    plot_win_rate(histories, IMG_DIR / "phase3_win_rate.png")
    animate_boxes(histories[0][1], OUT_DIR / "phase3_learning.mp4")

    print("Phase 1 wins:", p1_wins)
    print("Phase 2 wins:", p2_wins)
    for label, history in histories:
        wins = sum(h["winner"] == "computer" for h in history)
        first = sum(h["winner"] == "computer" for h in history[:20])
        last = sum(h["winner"] == "computer" for h in history[-20:])
        print(f"Phase 3 vs {label}: computer won {wins}/{len(history)} "
              f"(first 20: {first}/20, last 20: {last}/20)")
        print(f"  final boxes: {history[-1]['boxes']}")


if __name__ == "__main__":
    main()
