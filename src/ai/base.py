"""
AI 基类接口。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from src.engine.cards import Card


@dataclass
class GameContext:
    """给 AI 提供游戏上下文"""
    position: str = "farmer"          # "landlord" 或 "farmer"
    players_hand_count: List[int] = field(default_factory=lambda: [17, 17, 17])
    history: List = field(default_factory=list)
    bottom_cards: List[Card] = field(default_factory=list)
    landlord_idx: int = -1
    my_idx: int = -1
    pass_count: int = 0


class BaseAI(ABC):
    """AI 基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def decide(
        self,
        hand: List[Card],
        last_play: Optional[List[Card]],
        context: GameContext,
    ) -> Optional[List[Card]]:
        """
        决定出牌。
        返回 List[Card] 表示出牌，None 表示过牌。
        """
        pass
