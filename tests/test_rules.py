"""出牌规则测试"""
from src.engine.cards import Card, Rank, Suit
from src.engine.rules import can_beat, get_all_playable


def _c(rank: Rank, suit: Suit = Suit.SPADE) -> Card:
    return Card(rank, suit)


class TestCanBeat:
    def test_free_play_any_valid(self):
        """自由出牌时任意有效牌型都可出"""
        assert can_beat([_c(Rank.ACE)], None) is True
        assert can_beat([_c(Rank.THREE)], None) is True

    def test_free_play_invalid(self):
        """无效牌型不可出"""
        assert can_beat([_c(Rank.ACE), _c(Rank.THREE)], None) is False

    def test_rocket_beats_everything(self):
        rocket = [Card(Rank.SMALL_JOKER), Card(Rank.BIG_JOKER)]
        bomb = [
            Card(Rank.TWO, Suit.SPADE), Card(Rank.TWO, Suit.HEART),
            Card(Rank.TWO, Suit.CLUB), Card(Rank.TWO, Suit.DIAMOND),
        ]
        assert can_beat(rocket, bomb) is True
        # 同样，炸弹不能压火箭
        assert can_beat(bomb, rocket) is False

    def test_bomb_beats_normal(self):
        bomb = [
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART),
            Card(Rank.THREE, Suit.CLUB), Card(Rank.THREE, Suit.DIAMOND),
        ]
        single = [_c(Rank.TWO)]  # 2 是最大单牌
        assert can_beat(bomb, single) is True

    def test_bomb_vs_bomb_bigger_wins(self):
        bomb7 = [
            Card(Rank.SEVEN, Suit.SPADE), Card(Rank.SEVEN, Suit.HEART),
            Card(Rank.SEVEN, Suit.CLUB), Card(Rank.SEVEN, Suit.DIAMOND),
        ]
        bomb8 = [
            Card(Rank.EIGHT, Suit.SPADE), Card(Rank.EIGHT, Suit.HEART),
            Card(Rank.EIGHT, Suit.CLUB), Card(Rank.EIGHT, Suit.DIAMOND),
        ]
        assert can_beat(bomb8, bomb7) is True
        assert can_beat(bomb7, bomb8) is False

    def test_same_pattern_bigger_wins(self):
        """同牌型同张数，点数大者胜"""
        big_single = [_c(Rank.KING)]
        small_single = [_c(Rank.QUEEN)]
        assert can_beat(big_single, small_single) is True
        assert can_beat(small_single, big_single) is False

    def test_different_pattern_cannot_beat(self):
        """不同牌型（非炸弹）不能互压"""
        pair = [Card(Rank.TWO, Suit.SPADE), Card(Rank.TWO, Suit.HEART)]
        single = [_c(Rank.ACE)]
        assert can_beat(pair, single) is False

    def test_different_length_cannot_beat(self):
        """同牌型但不同长度不能互压（如5张顺子 vs 6张顺子）"""
        straight5 = [
            Card(Rank.THREE, Suit.SPADE), Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB), Card(Rank.SIX, Suit.DIAMOND),
            Card(Rank.SEVEN, Suit.SPADE),
        ]
        straight6 = [
            Card(Rank.THREE, Suit.SPADE), Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB), Card(Rank.SIX, Suit.DIAMOND),
            Card(Rank.SEVEN, Suit.HEART), Card(Rank.EIGHT, Suit.CLUB),
        ]
        assert can_beat(straight6, straight5) is False


class TestGetAllPlayable:
    def test_free_play_includes_singles(self):
        hand = [_c(Rank.ACE), _c(Rank.THREE), _c(Rank.SEVEN)]
        options = get_all_playable(hand, None)
        singles = [o for o in options if len(o) == 1]
        assert len(singles) == 3

    def test_free_play_includes_pairs(self):
        hand = [
            Card(Rank.SEVEN, Suit.SPADE), Card(Rank.SEVEN, Suit.HEART),
            _c(Rank.ACE),
        ]
        options = get_all_playable(hand, None)
        pairs = [o for o in options if len(o) == 2]
        assert len(pairs) >= 1

    def test_must_beat_single(self):
        """必须压单张时只能出更大的单张"""
        hand = [
            _c(Rank.ACE), _c(Rank.THREE),
            Card(Rank.ACE, Suit.DIAMOND),
        ]
        last = [_c(Rank.KING)]
        options = get_all_playable(hand, last)
        # 只有 ACE 能压 KING
        for opt in options:
            assert all(isinstance(c, Card) for c in opt)
        singles = [o for o in options if len(o) == 1]
        assert all(_c_first_rank_val(o) >= Rank.ACE.value for o in singles)

    def test_must_beat_returns_bombs(self):
        """压单张时炸弹也算可选"""
        hand = [
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART),
            Card(Rank.THREE, Suit.CLUB), Card(Rank.THREE, Suit.DIAMOND),
            _c(Rank.FOUR),
        ]
        last = [_c(Rank.TWO)]
        options = get_all_playable(hand, last)
        # 4不能压2，所以只有炸弹
        assert len(options) == 1
        assert len(options[0]) == 4

    def test_no_playable_returns_empty(self):
        """没有能出的牌"""
        hand = [_c(Rank.THREE)]
        last = [_c(Rank.ACE)]
        options = get_all_playable(hand, last)
        assert options == []

    def test_free_play_no_duplicates(self):
        """自由出牌不应该有重复选项"""
        hand = [
            Card(Rank.SEVEN, Suit.SPADE), Card(Rank.SEVEN, Suit.HEART),
            _c(Rank.ACE),
        ]
        options = get_all_playable(hand, None)
        # 检查无重复
        seen = set()
        for opt in options:
            key = tuple(sorted(c.rank.value for c in opt))
            assert key not in seen
            seen.add(key)


def _c_first_rank_val(cards):
    return cards[0].rank.value
