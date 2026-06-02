"""牌型识别测试 - 覆盖所有15种牌型"""
from src.engine.cards import Card, Rank, Suit
from src.engine.patterns import identify_pattern, Pattern, PATTERN_NAMES


def _c(rank: Rank, suit: Suit = Suit.SPADE) -> Card:
    """快捷创建牌（默认黑桃）"""
    return Card(rank, suit)


def _cards(*pairs) -> list:
    """快捷创建多张牌：_cards((Rank.THREE, Suit.SPADE), (Rank.FOUR, Suit.HEART), ...)"""
    result = []
    for r, s in pairs:
        result.append(Card(r, s))
    return result


class TestSingle:
    def test_single(self):
        pat, val = identify_pattern([_c(Rank.ACE)])
        assert pat == Pattern.SINGLE
        assert val == 14

    def test_single_three(self):
        pat, val = identify_pattern([_c(Rank.THREE)])
        assert pat == Pattern.SINGLE
        assert val == 3


class TestPair:
    def test_pair(self):
        pat, val = identify_pattern([
            Card(Rank.ACE, Suit.SPADE), Card(Rank.ACE, Suit.HEART)
        ])
        assert pat == Pattern.PAIR
        assert val == 14

    def test_not_pair_different_rank(self):
        pat, val = identify_pattern([
            Card(Rank.ACE, Suit.SPADE), Card(Rank.KING, Suit.HEART)
        ])
        assert pat == Pattern.INVALID


class TestTriple:
    def test_triple_none(self):
        pat, val = identify_pattern([
            Card(Rank.SEVEN, Suit.SPADE),
            Card(Rank.SEVEN, Suit.HEART),
            Card(Rank.SEVEN, Suit.DIAMOND),
        ])
        assert pat == Pattern.TRIPLE
        assert val == 7


class TestTripleOne:
    def test_triple_one(self):
        pat, val = identify_pattern([
            Card(Rank.ACE, Suit.SPADE),
            Card(Rank.ACE, Suit.HEART),
            Card(Rank.ACE, Suit.CLUB),
            Card(Rank.THREE, Suit.DIAMOND),
        ])
        assert pat == Pattern.TRIPLE_ONE
        assert val == 14


class TestTripleTwo:
    def test_triple_two(self):
        pat, val = identify_pattern([
            Card(Rank.KING, Suit.SPADE),
            Card(Rank.KING, Suit.HEART),
            Card(Rank.KING, Suit.CLUB),
            Card(Rank.FOUR, Suit.DIAMOND),
            Card(Rank.FOUR, Suit.CLUB),
        ])
        assert pat == Pattern.TRIPLE_TWO
        assert val == 13


class TestStraight:
    def test_straight_34567(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE),
            Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB),
            Card(Rank.SIX, Suit.DIAMOND),
            Card(Rank.SEVEN, Suit.SPADE),
        ])
        assert pat == Pattern.STRAIGHT
        assert val == 7

    def test_straight_10JQKA(self):
        pat, val = identify_pattern([
            Card(Rank.TEN, Suit.SPADE),
            Card(Rank.JACK, Suit.HEART),
            Card(Rank.QUEEN, Suit.CLUB),
            Card(Rank.KING, Suit.DIAMOND),
            Card(Rank.ACE, Suit.SPADE),
        ])
        assert pat == Pattern.STRAIGHT
        assert val == 14

    def test_straight_too_short(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE),
            Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB),
            Card(Rank.SIX, Suit.DIAMOND),
        ])
        assert pat == Pattern.INVALID

    def test_straight_contains_two(self):
        """顺子不能包含 2"""
        pat, val = identify_pattern([
            Card(Rank.QUEEN, Suit.SPADE),
            Card(Rank.KING, Suit.HEART),
            Card(Rank.ACE, Suit.CLUB),
            Card(Rank.TWO, Suit.DIAMOND),
            Card(Rank.THREE, Suit.SPADE),  # 不连续 + 含2
        ])
        assert pat == Pattern.INVALID

    def test_straight_has_duplicate_rank(self):
        """顺子不能有重复点数"""
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE),
            Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB),
            Card(Rank.FIVE, Suit.DIAMOND),  # 重复
            Card(Rank.SIX, Suit.SPADE),
        ])
        assert pat == Pattern.INVALID


class TestStraightPair:
    def test_straight_pair_334455(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART),
            Card(Rank.FOUR, Suit.CLUB), Card(Rank.FOUR, Suit.DIAMOND),
            Card(Rank.FIVE, Suit.SPADE), Card(Rank.FIVE, Suit.HEART),
        ])
        assert pat == Pattern.STRAIGHT_PAIR
        assert val == 5

    def test_straight_pair_too_short(self):
        """连对至少3连"""
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART),
            Card(Rank.FOUR, Suit.CLUB), Card(Rank.FOUR, Suit.DIAMOND),
        ])
        assert pat == Pattern.INVALID


class TestPlane:
    def test_plane_333444(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART), Card(Rank.THREE, Suit.CLUB),
            Card(Rank.FOUR, Suit.DIAMOND), Card(Rank.FOUR, Suit.SPADE), Card(Rank.FOUR, Suit.HEART),
        ])
        assert pat == Pattern.PLANE
        assert val == 4

    def test_plane_single_333444_56(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART), Card(Rank.THREE, Suit.CLUB),
            Card(Rank.FOUR, Suit.DIAMOND), Card(Rank.FOUR, Suit.SPADE), Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB),
            Card(Rank.SIX, Suit.DIAMOND),
        ])
        assert pat == Pattern.PLANE_SINGLE
        assert val == 4

    def test_plane_pair_333444_5566(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART), Card(Rank.THREE, Suit.CLUB),
            Card(Rank.FOUR, Suit.DIAMOND), Card(Rank.FOUR, Suit.SPADE), Card(Rank.FOUR, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB), Card(Rank.FIVE, Suit.DIAMOND),
            Card(Rank.SIX, Suit.HEART), Card(Rank.SIX, Suit.CLUB),
        ])
        assert pat == Pattern.PLANE_PAIR
        assert val == 4

    def test_plane_only_one_triple(self):
        """只有一组三张不是飞机"""
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART), Card(Rank.THREE, Suit.CLUB),
        ])
        assert pat == Pattern.TRIPLE


class TestFourTwo:
    def test_four_two_single(self):
        pat, val = identify_pattern([
            Card(Rank.SEVEN, Suit.SPADE), Card(Rank.SEVEN, Suit.HEART),
            Card(Rank.SEVEN, Suit.CLUB), Card(Rank.SEVEN, Suit.DIAMOND),
            Card(Rank.THREE, Suit.SPADE),
            Card(Rank.FOUR, Suit.HEART),
        ])
        assert pat == Pattern.FOUR_TWO_SINGLE
        assert val == 7

    def test_four_two_pair(self):
        pat, val = identify_pattern([
            Card(Rank.EIGHT, Suit.SPADE), Card(Rank.EIGHT, Suit.HEART),
            Card(Rank.EIGHT, Suit.CLUB), Card(Rank.EIGHT, Suit.DIAMOND),
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART),
            Card(Rank.FIVE, Suit.CLUB), Card(Rank.FIVE, Suit.DIAMOND),
        ])
        assert pat == Pattern.FOUR_TWO_PAIR
        assert val == 8


class TestBomb:
    def test_bomb(self):
        pat, val = identify_pattern([
            Card(Rank.SEVEN, Suit.SPADE), Card(Rank.SEVEN, Suit.HEART),
            Card(Rank.SEVEN, Suit.CLUB), Card(Rank.SEVEN, Suit.DIAMOND),
        ])
        assert pat == Pattern.BOMB
        assert val == 7


class TestRocket:
    def test_rocket(self):
        pat, val = identify_pattern([
            Card(Rank.SMALL_JOKER), Card(Rank.BIG_JOKER),
        ])
        assert pat == Pattern.ROCKET
        assert val == 17


class TestInvalid:
    def test_empty(self):
        pat, val = identify_pattern([])
        assert pat == Pattern.INVALID

    def test_random_mess(self):
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.SEVEN, Suit.HEART),
            Card(Rank.KING, Suit.CLUB),
        ])
        assert pat == Pattern.INVALID

    def test_two_pairs_not_straight(self):
        """两个不对子但不成连对"""
        pat, val = identify_pattern([
            Card(Rank.THREE, Suit.SPADE), Card(Rank.THREE, Suit.HEART),
            Card(Rank.KING, Suit.CLUB), Card(Rank.KING, Suit.DIAMOND),
        ])
        assert pat == Pattern.INVALID


class TestPatternNames:
    def test_all_patterns_have_names(self):
        for pat in Pattern:
            if pat != Pattern.INVALID:
                assert pat in PATTERN_NAMES, f"Missing name for {pat}"
