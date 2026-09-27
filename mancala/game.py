"""Core Kalah rules: board state, legal moves, sowing, captures, game end.

Board layout (indices):

        12  11  10   9   8   7        <- NORTH's pits (player 1)
   13                          6      <- 13 = North store, 6 = South store
         0   1   2   3   4   5        <- SOUTH's pits (player 0)

Player 0 ("South") owns pits 0-5 and store 6.
Player 1 ("North") owns pits 7-12 and store 13.
Sowing goes counter-clockwise: 0 -> 1 -> ... -> 5 -> 6 -> 7 -> ... -> 12 -> 13 -> 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

PITS_PER_SIDE = 6
SOUTH, NORTH = 0, 1
STORE = {SOUTH: 6, NORTH: 13}
FIRST_PIT = {SOUTH: 0, NORTH: 7}


def pits_of(player: int) -> range:
    """Indices of the six pits belonging to ``player``."""
    start = FIRST_PIT[player]
    return range(start, start + PITS_PER_SIDE)


def opposite(pit: int) -> int:
    """The pit directly across the board from ``pit``."""
    return 12 - pit


@dataclass
class MoveResult:
    """What happened during a single move, for the UI to narrate."""

    player: int
    pit: int
    last_pit: int
    extra_turn: bool = False
    captured: int = 0
    capture_pit: Optional[int] = None
    sow_path: List[int] = field(default_factory=list)


@dataclass
class Game:
    """Full game state. ``board`` has 14 slots: 12 pits + 2 stores."""

    board: List[int] = field(default_factory=lambda: [4] * 6 + [0] + [4] * 6 + [0])
    current: int = SOUTH
    seeds_per_pit: int = 4

    @classmethod
    def new(cls, seeds_per_pit: int = 4, first: int = SOUTH) -> "Game":
        board = [seeds_per_pit] * 6 + [0] + [seeds_per_pit] * 6 + [0]
        return cls(board=board, current=first, seeds_per_pit=seeds_per_pit)

    # ------------------------------------------------------------------ helpers
    def copy(self) -> "Game":
        return Game(board=self.board[:], current=self.current, seeds_per_pit=self.seeds_per_pit)

    def store(self, player: int) -> int:
        return self.board[STORE[player]]

    def side_seeds(self, player: int) -> int:
        return sum(self.board[i] for i in pits_of(player))

    def legal_moves(self, player: Optional[int] = None) -> List[int]:
        """Pit indices the given (default: current) player may sow from."""
        p = self.current if player is None else player
        return [i for i in pits_of(p) if self.board[i] > 0]

    def is_over(self) -> bool:
        return self.side_seeds(SOUTH) == 0 or self.side_seeds(NORTH) == 0

    def winner(self) -> Optional[int]:
        """0 / 1 for a winner, None for a draw. Only meaningful once ``is_over``."""
        s, n = self.store(SOUTH), self.store(NORTH)
        if s > n:
            return SOUTH
        if n > s:
            return NORTH
        return None

    # -------------------------------------------------------------------- rules
    def play(self, pit: int) -> MoveResult:
        """Sow from ``pit`` for the current player, mutating the game in place.

        Raises ``ValueError`` for an illegal pit.
        """
        player = self.current
        if pit not in pits_of(player):
            raise ValueError(f"pit {pit} does not belong to player {player}")
        seeds = self.board[pit]
        if seeds == 0:
            raise ValueError(f"pit {pit} is empty")

        my_store = STORE[player]
        their_store = STORE[1 - player]
        result = MoveResult(player=player, pit=pit, last_pit=pit)

        self.board[pit] = 0
        idx = pit
        while seeds > 0:
            idx = (idx + 1) % 14
            if idx == their_store:  # skip opponent's store
                continue
            self.board[idx] += 1
            result.sow_path.append(idx)
            seeds -= 1
        result.last_pit = idx

        if idx == my_store:
            # Landed in own store: play again.
            result.extra_turn = True
        elif idx in pits_of(player) and self.board[idx] == 1:
            # Landed in an empty pit on own side: capture opposite seeds.
            opp = opposite(idx)
            if self.board[opp] > 0:
                captured = self.board[opp] + 1
                self.board[opp] = 0
                self.board[idx] = 0
                self.board[my_store] += captured
                result.captured = captured
                result.capture_pit = idx

        if self.is_over():
            self._sweep()
        elif not result.extra_turn:
            self.current = 1 - player

        return result

    def _sweep(self) -> None:
        """When one side is empty, the other player keeps all remaining seeds."""
        for p in (SOUTH, NORTH):
            for i in pits_of(p):
                self.board[STORE[p]] += self.board[i]
                self.board[i] = 0

    def score(self) -> Tuple[int, int]:
        return self.store(SOUTH), self.store(NORTH)
