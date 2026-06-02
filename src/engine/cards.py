"""
斗地主牌面定义。
54 张牌：52 张普通牌 + 小王 + 大王
排序规则：点数从大到小 大王,小王,2,A,K,Q,J,10,9,8,7,6,5,4,3
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional
import random


class Suit(IntEnum):
    """花色，值用于比较"""
    DIAMOND = 1    # ♦ 方块
    CLUB = 2       # ♣ 梅花
    HEART = 3      # ♥ 红心
    SPADE = 4      # ♠ 黑桃


class Rank(IntEnum):
    """点数，值用于比较大小"""
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14
    TWO = 15
    SMALL_JOKER = 16   # 小王
    BIG_JOKER = 17     # 大王


SUIT_SYMBOLS = {
    Suit.DIAMOND: "♦",
    Suit.CLUB: "♣",
    Suit.HEART: "♥",
    Suit.SPADE: "♠",
}

RANK_NAMES = {
    Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
    Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8",
    Rank.NINE: "9", Rank.TEN: "10", Rank.JACK: "J",
    Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
    Rank.TWO: "2", Rank.SMALL_JOKER: "🃏", Rank.BIG_JOKER: "👑",
}

# 顺子合法范围（不能包含 2 和王）
STRAIGHT_VALID_RANKS = set(range(Rank.THREE.value, Rank.TWO.value))  # 3-14


@dataclass(frozen=True, order=True)
class Card:
    """一张牌，按 (rank, suit) 排序"""
    rank: Rank
    suit: Optional[Suit] = None  # 大小王没有花色

    def __str__(self) -> str:
        if self.suit is None:
            return RANK_NAMES[self.rank]
        sym = SUIT_SYMBOLS[self.suit]
        rn = RANK_NAMES[self.rank]
        if len(rn) == 1:
            return f"{sym} {rn}"
        return f"{sym}{rn}"

    def __repr__(self) -> str:
        return str(self)


class Deck:
    """一副牌，54张"""

    @staticmethod
    def create() -> List[Card]:
        """创建一副新牌"""
        cards: List[Card] = []
        for suit in Suit:
            for rank in Rank:
                if rank.value <= Rank.TWO.value:
                    cards.append(Card(rank, suit))
        cards.append(Card(Rank.SMALL_JOKER))
        cards.append(Card(Rank.BIG_JOKER))
        return cards

    @staticmethod
    def shuffle(cards: List[Card]) -> List[Card]:
        """洗牌（Fisher-Yates）"""
        shuffled = cards[:]
        random.shuffle(shuffled)
        return shuffled

    @staticmethod
    def deal(cards: List[Card]) -> tuple:
        """
        三人斗地主发牌：每人 17 张，底牌 3 张。
        返回 (player1, player2, player3, bottom_cards)
        """
        return cards[:17], cards[17:34], cards[34:51], list(cards[51:])


def sort_cards(cards: List[Card]) -> List[Card]:
    """按 rank 降序排列（大牌在前），同 rank 按 suit 降序"""
    return sorted(
        cards,
        key=lambda c: (c.rank.value, c.suit.value if c.suit else 0),
        reverse=True
    )
