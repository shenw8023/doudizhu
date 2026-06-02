"""
游戏状态机。

管理一局斗地主从发牌叫地主到游戏结束的完整状态。
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from src.engine.cards import Card, Deck, sort_cards
from src.engine.rules import can_beat


class GamePhase(Enum):
    CALLING = "calling"      # 叫地主阶段
    PLAYING = "playing"      # 出牌阶段
    GAME_OVER = "game_over"  # 游戏结束


class Role(Enum):
    LANDLORD = "landlord"
    FARMER = "farmer"


@dataclass
class PlayRecord:
    """一次出牌记录"""
    player_idx: int          # 0=玩家, 1=AI1, 2=AI2
    cards: List[Card]        # 出的牌
    action: str              # "play" 或 "pass"


@dataclass
class GameState:
    """游戏完整状态"""
    # 玩家手牌
    player_hands: List[List[Card]] = field(default_factory=lambda: [[], [], []])

    # 底牌（3张）
    bottom_cards: List[Card] = field(default_factory=list)

    # 地主索引 (0/1/2)
    landlord_idx: int = -1

    # 叫地主数据
    call_scores: List[int] = field(default_factory=lambda: [-1, -1, -1])  # -1=未叫, 0=不叫, 1/2/3=叫分
    current_caller: int = 0

    # 出牌阶段数据
    current_player: int = 0
    last_play: Optional[List[Card]] = None
    last_player: Optional[int] = None  # 最后一个出牌的人（不是过牌的人）
    pass_count: int = 0

    # 历史
    history: List[PlayRecord] = field(default_factory=list)

    # 阶段
    phase: GamePhase = GamePhase.CALLING

    # 结果
    winner_role: Optional[Role] = None


class Game:
    """游戏控制器"""

    def __init__(self):
        self.state = GameState()

    def start(self) -> GameState:
        """开始新游戏：洗牌发牌 → 进入叫地主阶段"""
        deck = Deck.create()
        shuffled = Deck.shuffle(deck)
        p1, p2, p3, bottom = Deck.deal(shuffled)

        self.state = GameState(
            player_hands=[sort_cards(p1), sort_cards(p2), sort_cards(p3)],
            bottom_cards=list(bottom),
            phase=GamePhase.CALLING,
            current_caller=0,
        )
        return self.state

    def call_landlord(self, player_idx: int, score: int) -> bool:
        """
        叫地主。

        score: 0=不叫, 1/2/3=叫分
        返回 True 表示叫地主阶段结束（有人叫3分或三人都表态完）
        """
        if self.state.phase != GamePhase.CALLING:
            return True

        self.state.call_scores[player_idx] = score

        if score == 3:
            # 直接叫3分，立刻成为地主
            self._set_landlord(player_idx)
            return True

        # 如果已有最高分
        max_score = max(self.state.call_scores)
        if max_score >= 1:
            # 看下一个玩家是否还能叫
            next_caller = (player_idx + 1) % 3
            if next_caller == self._find_first_bidder():
                # 轮完一圈，最高分者成为地主
                self._set_landlord(self.state.call_scores.index(max_score))
                return True
            self.state.current_caller = next_caller
            return False

        # 还没人叫：轮流
        self.state.current_caller = (player_idx + 1) % 3

        # 三人都表态完了？
        all_done = all(s >= 0 for s in self.state.call_scores)
        if all_done:
            max_score = max(self.state.call_scores)
            if max_score == 0:
                # 都不叫，重新发牌
                return self.start() is not None  # trigger re-deal via return True
            self._set_landlord(self.state.call_scores.index(max_score))
            return True

        return False

    def _find_first_bidder(self) -> int:
        """找到第一个叫分的人"""
        for i, s in enumerate(self.state.call_scores):
            if s > 0:
                return i
        return 0

    def _set_landlord(self, idx: int):
        """设置地主，分配底牌，进入出牌阶段"""
        self.state.landlord_idx = idx
        self.state.player_hands[idx].extend(self.state.bottom_cards)
        self.state.player_hands[idx] = sort_cards(self.state.player_hands[idx])
        self.state.phase = GamePhase.PLAYING
        self.state.current_player = idx  # 地主先出
        self.state.last_play = None
        self.state.last_player = None
        self.state.pass_count = 0

    def play(self, player_idx: int, cards: Optional[List[Card]]) -> bool:
        """
        出牌或过牌。

        cards: List[Card] 表示出牌，None 表示过牌。
        返回 True 表示操作合法且已执行。

        注意：不会从玩家手牌中移除牌——调用者应在确认合法后自行移除。
              此方法仅验证合法性并更新游戏状态。

        合法性检查：
        1. 必须当前玩家的回合
        2. 出牌必须能压过 last_play（或 last_play 为空时自由出牌）
        3. 过牌的前提是 last_play 非空（不能主动过牌）
        """
        if self.state.phase != GamePhase.PLAYING:
            return False
        if player_idx != self.state.current_player:
            return False

        if cards is None:
            # 过牌
            if self.state.last_play is None:
                return False  # 自由出牌时不能过牌
            self.state.pass_count += 1
            self.state.history.append(PlayRecord(player_idx, [], "pass"))

            if self.state.pass_count >= 2:
                # 新回合：最后出牌者自由出牌
                self.state.last_play = None
                self.state.last_player = None
                self.state.pass_count = 0
                self.state.current_player = self._next_player(self.state.current_player)
            else:
                self.state.current_player = self._next_player(player_idx)
            return True

        # 出牌
        if not can_beat(cards, self.state.last_play):
            return False

        self.state.last_play = cards
        self.state.last_player = player_idx
        self.state.pass_count = 0
        self.state.history.append(PlayRecord(player_idx, cards, "play"))
        self.state.current_player = self._next_player(player_idx)
        return True

    def remove_cards(self, player_idx: int, cards: List[Card]):
        """从玩家手牌中移除已出的牌"""
        hand = self.state.player_hands[player_idx]
        for c in cards:
            if c in hand:
                hand.remove(c)

        # 检查游戏是否结束
        if len(hand) == 0:
            self.state.phase = GamePhase.GAME_OVER
            if player_idx == self.state.landlord_idx:
                self.state.winner_role = Role.LANDLORD
            else:
                self.state.winner_role = Role.FARMER

    def is_game_over(self) -> bool:
        return self.state.phase == GamePhase.GAME_OVER

    def get_winner(self) -> Optional[str]:
        """返回 "landlord" 或 "farmer" """
        if self.state.winner_role == Role.LANDLORD:
            return "landlord"
        elif self.state.winner_role == Role.FARMER:
            return "farmer"
        return None

    def get_player_role(self, idx: int) -> str:
        return "landlord" if idx == self.state.landlord_idx else "farmer"

    def _next_player(self, current: int) -> int:
        return (current + 1) % 3
