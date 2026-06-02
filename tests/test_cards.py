"""牌面数据结构测试"""
from src.engine.cards import Card, Rank, Suit, Deck, sort_cards, STRAIGHT_VALID_RANKS


class TestCard:
    def test_card_creation(self):
        c = Card(Rank.ACE, Suit.SPADE)
        assert str(c) == "♠ A"
        assert c.rank == Rank.ACE
        assert c.suit == Suit.SPADE

    def test_card_str_diamond(self):
        c = Card(Rank.TEN, Suit.DIAMOND)
        assert str(c) == "♦10"

    def test_card_str_heart(self):
        c = Card(Rank.KING, Suit.HEART)
        assert str(c) == "♥ K"

    def test_card_str_club(self):
        c = Card(Rank.TWO, Suit.CLUB)
        assert str(c) == "♣ 2"

    def test_joker_creation(self):
        small = Card(Rank.SMALL_JOKER)
        big = Card(Rank.BIG_JOKER)
        assert small.suit is None
        assert big.suit is None
        assert str(small) == "🃏"
        assert str(big) == "👑"

    def test_card_comparison_rank(self):
        """点数大的牌大于点数小的牌"""
        assert Card(Rank.TWO, Suit.SPADE) > Card(Rank.ACE, Suit.HEART)
        assert Card(Rank.BIG_JOKER) > Card(Rank.SMALL_JOKER)
        assert Card(Rank.SMALL_JOKER) > Card(Rank.TWO, Suit.SPADE)

    def test_card_comparison_suit(self):
        """同点数时花色大的更大"""
        assert Card(Rank.ACE, Suit.SPADE) > Card(Rank.ACE, Suit.HEART)
        assert Card(Rank.KING, Suit.HEART) > Card(Rank.KING, Suit.DIAMOND)

    def test_card_equality(self):
        c1 = Card(Rank.THREE, Suit.SPADE)
        c2 = Card(Rank.THREE, Suit.SPADE)
        assert c1 == c2
        assert not (c1 == Card(Rank.THREE, Suit.HEART))

    def test_card_hashable(self):
        """Card 应该可哈希（可以用作 dict key）"""
        s = {Card(Rank.ACE, Suit.SPADE), Card(Rank.ACE, Suit.HEART)}
        assert len(s) == 2
        s.add(Card(Rank.ACE, Suit.SPADE))
        assert len(s) == 2


class TestDeck:
    def test_deck_size(self):
        deck = Deck.create()
        assert len(deck) == 54

    def test_deck_has_all_ranks(self):
        deck = Deck.create()
        rank_counts = {}
        for c in deck:
            rank_counts[c.rank] = rank_counts.get(c.rank, 0) + 1
        for rank in Rank:
            if rank in (Rank.SMALL_JOKER, Rank.BIG_JOKER):
                assert rank_counts.get(rank) == 1
            else:
                assert rank_counts.get(rank) == 4

    def test_shuffle_preserves_deck(self):
        deck = Deck.create()
        shuffled = Deck.shuffle(deck)
        assert len(shuffled) == 54
        assert set(deck) == set(shuffled)  # 内容不变

    def test_deal(self):
        deck = Deck.create()
        shuffled = Deck.shuffle(deck)
        p1, p2, p3, bottom = Deck.deal(shuffled)
        assert len(p1) == 17
        assert len(p2) == 17
        assert len(p3) == 17
        assert len(bottom) == 3
        # 所有牌不重复
        all_cards = set(p1) | set(p2) | set(p3) | set(bottom)
        assert len(all_cards) == 54


class TestSortCards:
    def test_sort_cards_descending(self):
        cards = [
            Card(Rank.THREE, Suit.SPADE),
            Card(Rank.ACE, Suit.HEART),
            Card(Rank.TWO, Suit.CLUB),
            Card(Rank.BIG_JOKER),
        ]
        sorted_cards = sort_cards(cards)
        assert sorted_cards[0].rank == Rank.BIG_JOKER   # 大王最小索引（最大牌在前）
        assert sorted_cards[1].rank == Rank.TWO
        assert sorted_cards[2].rank == Rank.ACE
        assert sorted_cards[3].rank == Rank.THREE

    def test_sort_same_rank_by_suit(self):
        cards = [
            Card(Rank.ACE, Suit.DIAMOND),
            Card(Rank.ACE, Suit.SPADE),
            Card(Rank.ACE, Suit.HEART),
            Card(Rank.ACE, Suit.CLUB),
        ]
        sorted_cards = sort_cards(cards)
        suits = [c.suit for c in sorted_cards]
        assert suits == [Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND]


class TestStraightValidRanks:
    def test_valid_ranks_range(self):
        """顺子合法范围：3-14（不含2和王）"""
        assert Rank.THREE.value in STRAIGHT_VALID_RANKS
        assert Rank.ACE.value in STRAIGHT_VALID_RANKS
        assert Rank.TWO.value not in STRAIGHT_VALID_RANKS
        assert Rank.SMALL_JOKER.value not in STRAIGHT_VALID_RANKS
        assert Rank.BIG_JOKER.value not in STRAIGHT_VALID_RANKS
