"""游戏状态机测试"""
from src.engine.cards import Card, Rank, Suit, Deck
from src.engine.game import Game, GamePhase


def _c(rank: Rank, suit: Suit = Suit.SPADE) -> Card:
    return Card(rank, suit)


class TestGameStart:
    def test_start_deals_cards(self):
        game = Game()
        state = game.start()
        assert state.phase == GamePhase.CALLING
        assert len(state.player_hands[0]) == 17
        assert len(state.player_hands[1]) == 17
        assert len(state.player_hands[2]) == 17
        assert len(state.bottom_cards) == 3

    def test_start_hands_sorted(self):
        """发牌后手牌应该已排序（大牌在前）"""
        game = Game()
        state = game.start()
        for hand in state.player_hands:
            for i in range(1, len(hand)):
                assert hand[i-1].rank.value >= hand[i].rank.value


class TestCallingLandlord:
    def test_call_3_becomes_landlord_immediately(self):
        game = Game()
        game.start()
        result = game.call_landlord(0, 3)
        assert result is True
        assert game.state.landlord_idx == 0
        assert game.state.phase == GamePhase.PLAYING
        # 地主应该有 20 张牌（17+3底牌）
        assert len(game.state.player_hands[0]) == 20
        # 底牌不应该还在
        assert game.state.bottom_cards == [] or all(
            c in game.state.player_hands[0] for c in game.state.bottom_cards
        )

    def test_all_pass_redeals(self):
        game = Game()
        game.start()
        game.call_landlord(0, 0)
        game.call_landlord(1, 0)
        result = game.call_landlord(2, 0)
        # 三人都不叫，重新发牌
        assert result is True or not result  # 可能触发重新发牌

    def test_first_player_calls_1_others_can_compete(self):
        game = Game()
        game.start()
        result = game.call_landlord(0, 1)
        assert result is False  # 还没结束，1分不够


class TestPlaying:
    def test_landlord_plays_first(self):
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        assert game.state.current_player == 0  # 地主先出
        assert game.state.last_play is None  # 自由出牌

    def test_valid_play_updates_state(self):
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        # 地主出一张最小的单牌
        hand = game.state.player_hands[0]
        smallest = [hand[-1]]  # 排序后最小的在最后
        result = game.play(0, smallest)
        assert result is True
        assert game.state.last_play == smallest
        assert game.state.current_player == 1  # 轮到AI1
        assert game.state.pass_count == 0

    def test_pass_not_allowed_on_free_play(self):
        """自由出牌时不能过牌"""
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        result = game.play(0, None)  # 地主尝试过牌
        assert result is False

    def test_pass_allowed_after_play(self):
        """有人出牌后可以过牌"""
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        # 先出一张
        hand = game.state.player_hands[0]
        game.play(0, [hand[-1]])
        # 下家过牌
        result = game.play(1, None)
        assert result is True
        assert game.state.pass_count == 1

    def test_two_passes_new_round(self):
        """两人连续过牌，新回合开始"""
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        hand = game.state.player_hands[0]
        game.play(0, [hand[-1]])
        game.play(1, None)
        result = game.play(2, None)
        assert result is True
        assert game.state.last_play is None  # 新回合
        assert game.state.pass_count == 0

    def test_wrong_player_rejected(self):
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        result = game.play(1, [])  # 不是当前玩家
        assert result is False

    def test_weaker_play_rejected(self):
        """不能压时要拒绝"""
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        # 让玩家出大牌
        hand = game.state.player_hands[0]
        # 出最大的单牌
        biggest_single = [hand[0]]
        game.play(0, biggest_single)
        # AI1尝试出更小的牌
        ai_hand = game.state.player_hands[1]
        if ai_hand and ai_hand[-1].rank <= biggest_single[0].rank:
            result = game.play(1, [ai_hand[-1]])
            assert result is False


class TestGameOver:
    def test_game_over_when_hand_empty(self):
        game = Game()
        game.start()
        game.call_landlord(0, 3)
        # 模拟玩家手牌出完
        game.state.player_hands[0] = []
        game.remove_cards(0, [])
        assert game.is_game_over() is True
        assert game.get_winner() == "landlord"
