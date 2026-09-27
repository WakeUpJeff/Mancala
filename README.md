# Mancala

A colourful, zero-dependency **Mancala (Kalah)** game for your terminal.

```
  ╔═════════════════════════════════════════════════════════════════════════╗
  ║  Grandmaster ◀ sows this way                                            ║
  ║  ╭───────╮     6       5       4       3       2       1     ╭───────╮  ║
  ║  │       │  ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮  │       │  ║
  ║  │       │  │  0  │ │  4  │ │  4  │ │  4  │ │  4  │ │  5  │  │       │  ║
  ║  │       │  │  ·  │ │●●●● │ │●●●● │ │●●●● │ │●●●● │ │●●●●●│  │       │  ║
  ║  │   N   │  ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯  │   S   │  ║
  ║  │   1   │                                                   │   1   │  ║
  ║  │ store │  ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮  │ store │  ║
  ║  │       │  │  5  │ │  5  │ │  5  │ │  0  │ │  5  │ │  5  │  │       │  ║
  ║  │       │  │●●●●●│ │●●●●●│ │●●●●●│ │  ·  │ │●●●●●│ │●●●●●│  │       │  ║
  ║  │       │  ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯  │       │  ║
  ║  ╰───────╯     1       2       3       4       5       6     ╰───────╯  ║
  ║                                                    sows this way ▶ You  ║
  ╚═════════════════════════════════════════════════════════════════════════╝
```

## Features

- **Two ways to play**: hot-seat two-player, or one player against the computer.
- **Three AI levels**
  - *Novice* – mostly random, great for learning.
  - *Tactician* – greedy one-move lookahead that hunts captures and extra turns.
  - *Grandmaster* – depth-8 minimax with alpha-beta pruning and a positional evaluation.
- **Pretty board**: 24-bit colours, rounded Unicode pits, seed pictograms, and a
  seed-by-seed sowing animation that highlights captures.
- **Quality of life**: legal-move hints, undo, in-game rules, choose who opens,
  optional seed count (3–6 per pit), ASCII and no-colour fallbacks.
- **No dependencies**. Python 3.8+ and a terminal are all you need.

## Run it

```bash
python3 mancala.py
```

or, from the repo root:

```bash
python3 -m mancala
```

Optional install as a command:

```bash
pip install -e .
mancala
```

### Options

| Flag         | Effect                                            |
| ------------ | ------------------------------------------------- |
| `--no-anim`  | Skip the sowing animation                          |
| `--no-color` | Plain text (also honours `NO_COLOR`)               |
| `--ascii`    | Draw the board with ASCII instead of box characters |
| `--seeds N`  | Seeds per pit, 3–6 (default 4)                     |
| `--seed N`   | Random seed for the computer opponent              |

### Keys during a game

| Key   | Action                         |
| ----- | ------------------------------ |
| `1-6` | Sow from that pit              |
| `u`   | Undo back to your last move    |
| `r`   | Show the rules                 |
| `q`   | Quit                           |

## Rules (Kalah)

Each player owns the six pits on their side and the store to their right.
South sits at the bottom and sows rightward; North sits at the top and sows
leftward, so seeds always travel counter-clockwise.

1. Pick one of your pits. Lift all its seeds and drop one into each following
   pit, including your own store but **skipping the opponent's store**.
2. **Extra turn** – if the last seed lands in your store, move again.
3. **Capture** – if the last seed lands in an empty pit on your side and the
   opposite pit holds seeds, both go into your store.
4. When one side is empty the game ends. The other player sweeps the seeds
   left on their side into their store. Most seeds wins.

## Project layout

```
mancala.py            launcher
mancala/game.py       rules engine (board, sowing, captures, game end)
mancala/ai.py         the three computer opponents
mancala/ui.py         ANSI rendering: board, banners, prompts
mancala/cli.py        menus, turn loop, animation, undo
tests/test_game.py    rules and AI tests
```

Run the tests with:

```bash
python3 -m unittest
```
