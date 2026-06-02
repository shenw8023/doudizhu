"""AI 层测试 + 集成测试"""
import pytest
from src.engine.cards import Card, Rank, Suit, Deck, sort_cards
from src.engine.rules import get_all_playable
from src.engine.game import Game
from src.ai.base import GameContext
from src.ai.random_ai import RandomAI
from src.ai.rule_ai import RuleAI
from src.ai.mcts_ai import MCTSAI


def _c(rank: Rank, suit: Suit = Suit.SPADE) -> Card:
    return Card(rank, suit)


class TestRandomAI:
    def test_creates(self):
        ai = RandomAI(pass_rate=0.5, seed=42)
        assert ai.name is not None

    def test_returns_none_when_no_options(self):
        ai = RandomAI(seed=42)
        hand = [_c(Rank.THREE)]
        last = [_c(Rank.ACE)]
        ctx = GameContext(my_idx=0)
        result = ai.decide(hand, last, ctx)
        assert result is None  # 3 不能压 A

    def test_free_play_always_plays(self):
        ai = RandomAI(pass_rate=0.9, seed=42)  # 很高的过牌率
        hand = [_c(Rank.THREE), _c(Rank.FOUR)]
        ctx = GameContext(my_idx=0)
        result = ai.decide(hand, None, ctx)
        # 自由出牌必须出（不能过牌）
        assert result is not None
        assert len(result) >= 1

    def test_deterministic_with_seed(self):
        """相同种子应该产生相同结果"""
        ai1 = RandomAI(seed=42)
        ai2 = RandomAI(seed=42)
        hand = [Card(Rank.ACE, Suit.SPADE), Card(Rank.KING, Suit.HEART),
                Card(Rank.QUEEN, Suit.CLUB), _c(Rank.THREE)]
        ctx = GameContext(my_idx=0)
        for _ in range(10):
            r1 = ai1.decide(hand, None, ctx)
            r2 = ai2.decide(hand, None, ctx)
            assert r1 == r2


class TestRuleAI:
    def test_creates(self):
        ai = RuleAI()
        assert ai.name is not None

    def test_free_play_picks_single(self):
        """自由出牌时优先出单张"""
        ai = RuleAI()
        hand = [_c(Rank.THREE), _c(Rank.FIVE), _c(Rank.ACE)]
        ctx = GameContext(my_idx=0)
        result = ai.decide(hand, None, ctx)
        assert result is not None
        # 应该出最小的单张 (3)
        assert result[0].rank == Rank.THREE

    def test_respond_picks_smallest(self):
        """接牌时出最小的合法牌"""
        ai = RuleAI()
        hand = [_c(Rank.ACE), _c(Rank.KING), _c(Rank.THREE)]
        last = [_c(Rank.QUEEN)]
        ctx = GameContext(my_idx=0)
        result = ai.decide(hand, last, ctx)
        # KING 和 ACE 都能压 QUEEN，应该出 KING（更小的）
        assert result is not None
        assert result[0].rank == Rank.KING

    def test_passes_when_no_good_option(self):
        """没有合法出牌时必须过牌"""
        ai = RuleAI()
        hand = [_c(Rank.THREE)]
        last = [_c(Rank.ACE)]
        ctx = GameContext(my_idx=0)
        result = ai.decide(hand, last, ctx)
        assert result is None


class TestMCTSAI:
    def test_creates(self):
        ai = MCTSAI(num_simulations=10, seed=42)
        assert ai.name is not None

    def test_basic_decision(self):
        """基本决策测试：能正常返回结果"""
        ai = MCTSAI(num_simulations=10, seed=42)
        hand = [_c(Rank.THREE), _c(Rank.FOUR), _c(Rank.SEVEN)]
        ctx = GameContext(my_idx=0, landlord_idx=0, position="landlord")
        result = ai.decide(hand, None, ctx)
        assert result is not None
        assert len(result) >= 1

    def test_no_options_returns_none(self):
        ai = MCTSAI(num_simulations=10, seed=42)
        hand = [_c(Rank.THREE)]
        last = [_c(Rank.ACE)]
        ctx = GameContext(my_idx=0)
        result = ai.decide(hand, last, ctx)
        assert result is None


class TestIntegration:
    """集成测试：AI vs AI 完整对局"""

    def test_full_game_random_vs_random(self):
        """两个随机AI对局，确保能跑完"""
        game = Game()
        game.start()
        game.call_landlord(0, 3)  # 玩家(0)是地主

        # 用随机AI代替玩家
        ai = RandomAI(pass_rate=0.3, seed=42)

        turn = 0
        max_turns = 500
        while not game.is_game_over() and turn < max_turns:
            player = game.state.current_player
            hand = game.state.player_hands[player]

            ctx = GameContext(
                position=game.get_player_role(player),
                players_hand_count=[len(h) for h in game.state.player_hands],
                history=game.state.history,
                bottom_cards=game.state.bottom_cards,
                landlord_idx=game.state.landlord_idx,
                my_idx=player,
                pass_count=game.state.pass_count,
            )

            decision = ai.decide(hand, game.state.last_play, ctx)

            if decision is not None:
                # 出牌
                assert game.play(player, decision), f"Turn {turn}: invalid play by {player}"
                game.remove_cards(player, decision)
            else:
                # 过牌
                assert game.play(player, None), f"Turn {turn}: invalid pass by {player}"

            turn += 1

        assert turn < max_turns, "游戏超时未结束"
        assert game.is_game_over()
        assert game.get_winner() in ("landlord", "farmer")

    def test_full_game_rule_vs_rule(self):
        """两个规则AI对局"""
        game = Game()
        game.start()
        game.call_landlord(0, 3)

        ai = RuleAI()

        turn = 0
        max_turns = 500
        while not game.is_game_over() and turn < max_turns:
            player = game.state.current_player
            hand = game.state.player_hands[player]

            ctx = GameContext(
                position=game.get_player_role(player),
                players_hand_count=[len(h) for h in game.state.player_hands],
                history=game.state.history,
                bottom_cards=game.state.bottom_cards,
                landlord_idx=game.state.landlord_idx,
                my_idx=player,
                pass_count=game.state.pass_count,
            )

            decision = ai.decide(hand, game.state.last_play, ctx)

            if decision is not None:
                assert game.play(player, decision)
                game.remove_cards(player, decision)
            else:
                assert game.play(player, None)

            turn += 1

        assert turn < max_turns
        assert game.is_game_over()
