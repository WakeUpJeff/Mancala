import random
import unittest

from mancala import ai
from mancala.game import Game, NORTH, SOUTH


class RulesTest(unittest.TestCase):
    def test_initial_board(self):
        g = Game.new()
        self.assertEqual(sum(g.board), 48)
        self.assertEqual(g.legal_moves(), [0, 1, 2, 3, 4, 5])

    def test_simple_sow_switches_turn(self):
        g = Game.new()
        r = g.play(0)  # 4 seeds -> pits 1,2,3,4
        self.assertEqual(g.board[:6], [0, 5, 5, 5, 5, 4])
        self.assertFalse(r.extra_turn)
        self.assertEqual(g.current, NORTH)

    def test_extra_turn_on_store(self):
        g = Game.new()
        r = g.play(2)  # pit 2 with 4 seeds ends in store 6
        self.assertTrue(r.extra_turn)
        self.assertEqual(g.store(SOUTH), 1)
        self.assertEqual(g.current, SOUTH)

    def test_skips_opponent_store(self):
        g = Game.new()
        g.board = [0, 0, 0, 0, 0, 10, 0, 4, 4, 4, 4, 4, 4, 0]
        g.play(5)
        # 10 seeds from pit 5: 6,7,8,9,10,11,12,(skip 13),0,1,2.
        # The last seed lands in empty pit 2 and captures the 5 opposite (pit 10).
        self.assertEqual(g.board[13], 0)
        self.assertEqual(g.board[7:13], [5, 5, 5, 0, 5, 5])
        self.assertEqual(g.board[:3], [1, 1, 0])
        self.assertEqual(g.store(SOUTH), 1 + 6)

    def test_capture(self):
        g = Game.new()
        g.board = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0]
        r = g.play(0)
        self.assertEqual(r.captured, 8)
        self.assertEqual(g.store(SOUTH), 8)
        self.assertEqual(g.board[1], 0)
        self.assertEqual(g.board[11], 0)

    def test_no_capture_when_opposite_empty(self):
        g = Game.new()
        g.board = [1, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0]
        r = g.play(0)
        self.assertEqual(r.captured, 0)
        self.assertEqual(g.board[1], 1)

    def test_illegal_moves(self):
        g = Game.new()
        with self.assertRaises(ValueError):
            g.play(7)
        g.board[0] = 0
        with self.assertRaises(ValueError):
            g.play(0)

    def test_sweep_at_end(self):
        g = Game.new()
        g.board = [0, 0, 0, 0, 0, 1, 20, 3, 3, 3, 3, 3, 3, 9]
        g.play(5)
        self.assertTrue(g.is_over())
        self.assertEqual(sum(g.board), 48)
        self.assertEqual(g.side_seeds(SOUTH), 0)
        self.assertEqual(g.side_seeds(NORTH), 0)
        self.assertEqual(g.store(NORTH), 9 + 18)
        self.assertEqual(g.winner(), NORTH)

    def test_seed_conservation_random_games(self):
        rng = random.Random(1)
        for _ in range(200):
            g = Game.new()
            while not g.is_over():
                g.play(rng.choice(g.legal_moves()))
                self.assertEqual(sum(g.board), 48)


class AITest(unittest.TestCase):
    def _play(self, south, north, rng):
        g = Game.new()
        while not g.is_over():
            lvl = south if g.current == SOUTH else north
            g.play(ai.choose_move(g, lvl, rng))
        return g

    def test_all_levels_return_legal_moves(self):
        rng = random.Random(7)
        for lvl in ai.LEVELS:
            g = Game.new()
            for _ in range(5):
                if g.is_over():
                    break
                m = ai.choose_move(g, lvl, rng)
                self.assertIn(m, g.legal_moves())
                g.play(m)

    def test_hard_beats_easy(self):
        rng = random.Random(3)
        wins = 0
        for i in range(6):
            g = self._play("hard", "easy", rng) if i % 2 == 0 else self._play("easy", "hard", rng)
            hard_seat = SOUTH if i % 2 == 0 else NORTH
            if g.winner() == hard_seat:
                wins += 1
        self.assertGreaterEqual(wins, 5)

    def test_medium_beats_easy(self):
        rng = random.Random(11)
        wins = 0
        for i in range(10):
            g = self._play("medium", "easy", rng) if i % 2 == 0 else self._play("easy", "medium", rng)
            seat = SOUTH if i % 2 == 0 else NORTH
            if g.winner() == seat:
                wins += 1
        self.assertGreaterEqual(wins, 7)


if __name__ == "__main__":
    unittest.main()
