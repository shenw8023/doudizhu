# 斗地主 AI-TUI 实现方案

> **For Hermes:** 按 Task 逐项实施，每完成一个 Task 运行验证命令确认无误后再进入下一个。

**目标：** 构建一个终端交互式斗地主游戏，玩家对抗两个 AI 农民，AI 采用蒙特卡洛搜索 + 规则混合策略，终端用 `rich` 库渲染扑克牌。

**架构：** 引擎层（牌面/牌型/规则/状态机） → AI 层（随机基线 → 规则 AI → MCTS AI → 可选 LLM）→ UI 层（TUI 渲染 + 交互）。纯 Python，零外部依赖（除 rich/textual）。

**技术栈：** Python 3.11+, `rich`（TUI 渲染）, `pytest`（测试）, 可选 `textual`（高级交互）。

---

## 项目结构

```
/ubuntu/doudizhu/
├── main.py                  # 入口
├── requirements.txt         # 依赖
├── README.md                # 使用手册
├── IMPLEMENTATION_PLAN.md   # 本文档
├── docs/
│   └── USER_GUIDE.md        # 详细使用文档
├── src/
│   ├── __init__.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── cards.py         # 牌、牌堆、发牌
│   │   ├── patterns.py      # 牌型识别
│   │   ├── rules.py         # 规则判断
│   │   └── game.py          # 游戏状态机
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── base.py          # AI 接口
│   │   ├── random_ai.py     # 随机 AI
│   │   ├── rule_ai.py       # 规则 AI
│   │   └── mcts_ai.py       # 蒙特卡洛 AI
│   └── ui/
│       ├── __init__.py
│       ├── display.py       # 牌面渲染
│       └── tui.py           # TUI 交互
└── tests/
    ├── __init__.py
    ├── test_cards.py
    ├── test_patterns.py
    ├── test_rules.py
    └── test_game.py
```

---

## Phase 1：基础设施 + 牌引擎（约 60 分钟）

### Task 1: 项目初始化

**目标：** 创建项目骨架、虚拟环境、依赖文件

**文件：**
- 创建: `requirements.txt`
- 创建: `src/__init__.py`, `src/engine/__init__.py`, `src/ai/__init__.py`, `src/ui/__init__.py`
- 创建: `tests/__init__.py`

**操作：**
```bash
mkdir -p /ubuntu/doudizhu/{src/engine,src/ai,src/ui,docs,tests}
cd /ubuntu/doudizhu
python3 -m venv .venv
source .venv/bin/activate
```

**`requirements.txt`:**
```
rich>=13.0.0
pytest>=8.0.0
```

**验证：**
```bash
cd /ubuntu/doudizhu && source .venv/bin/activate
pip install -r requirements.txt
python -c "import rich; print('OK')"
# 期望: OK
```

---

### Task 2: 牌面数据结构

**目标：** 定义牌的花色、点数、大小比较

**文件：**
- 创建: `src/engine/cards.py`
- 测试: `tests/test_cards.py`

**实现内容：**

```python
# src/engine/cards.py
"""
斗地主牌面定义。
54 张牌：52 张普通牌 + 小王 + 大王
排序规则：点数从小到大 3,4,5,6,7,8,9,10,J,Q,K,A,2,小王,大王
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import List
import random

class Suit(IntEnum):
    """花色，值用于比较"""
    SPADE = 4      # ♠ 黑桃
    HEART = 3      # ♥ 红心
    CLUB = 2       # ♣ 梅花
    DIAMOND = 1    # ♦ 方块

class Rank(IntEnum):
    """点数，值用于比较"""
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

# 显示用的符号映射
SUIT_SYMBOLS = {
    Suit.SPADE: "♠",
    Suit.HEART: "♥",
    Suit.CLUB: "♣",
    Suit.DIAMOND: "♦",
}

RANK_NAMES = {
    Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
    Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8",
    Rank.NINE: "9", Rank.TEN: "10", Rank.JACK: "J",
    Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
    Rank.TWO: "2", Rank.SMALL_JOKER: "🃏", Rank.BIG_JOKER: "👑",
}

@dataclass(frozen=True, order=True)
class Card:
    """一张牌，按 rank 排序，rank 相同时按 suit 排序"""
    rank: Rank
    suit: Suit | None = None  # 大小王没有花色

    def __str__(self):
        if self.suit is None:
            return RANK_NAMES[self.rank]
        return f"{SUIT_SYMBOLS[self.suit]}{RANK_NAMES[self.rank]}"

    def __repr__(self):
        return str(self)

class Deck:
    """一副 54 张牌"""
    @staticmethod
    def create() -> List[Card]:
        cards = [Card(Rank(r), Suit(s)) for s in Suit for r in Rank if r <= Rank.TWO]
        cards.append(Card(Rank.SMALL_JOKER))
        cards.append(Card(Rank.BIG_JOKER))
        return cards

    @staticmethod
    def shuffle(cards: List[Card]) -> List[Card]:
        shuffled = cards[:]
        random.shuffle(shuffled)
        return shuffled

    @staticmethod
    def deal(cards: List[Card]) -> tuple[List[Card], List[Card], List[Card], List[Card]]:
        """
        三人斗地主发牌：每人 17 张，底牌 3 张。
        返回 (player1, player2, player3, 底牌)
        """
        return cards[:17], cards[17:34], cards[34:51], cards[51:]

def sort_cards(cards: List[Card]) -> List[Card]:
    """按 rank 降序排列（大牌在前）"""
    return sorted(cards, key=lambda c: (c.rank.value, c.suit.value if c.suit else 0), reverse=True)
```

**测试：**

```python
# tests/test_cards.py
from src.engine.cards import Card, Rank, Suit, Deck, sort_cards

def test_card_creation():
    c = Card(Rank.ACE, Suit.SPADE)
    assert str(c) == "♠A"
    assert c.rank == Rank.ACE
    assert c.suit == Suit.SPADE

def test_joker_creation():
    small = Card(Rank.SMALL_JOKER)
    big = Card(Rank.BIG_JOKER)
    assert small.suit is None
    assert small < big

def test_deck_size():
    deck = Deck.create()
    assert len(deck) == 54

def test_deal():
    deck = Deck.create()
    shuffled = Deck.shuffle(deck)
    p1, p2, p3, bottom = Deck.deal(shuffled)
    assert len(p1) == 17
    assert len(p2) == 17
    assert len(p3) == 17
    assert len(bottom) == 3

def test_sort_cards():
    cards = [Card(Rank.THREE, Suit.SPADE), Card(Rank.ACE, Suit.HEART), Card(Rank.TWO, Suit.CLUB)]
    sorted_cards = sort_cards(cards)
    assert sorted_cards[0].rank == Rank.TWO
    assert sorted_cards[-1].rank == Rank.THREE

def test_card_comparison():
    assert Card(Rank.TWO, Suit.SPADE) > Card(Rank.ACE, Suit.HEART)
    assert Card(Rank.BIG_JOKER) > Card(Rank.SMALL_JOKER)
    assert Card(Rank.SMALL_JOKER) > Card(Rank.TWO, Suit.SPADE)
```

**验证：**
```bash
cd /ubuntu/doudizhu && source .venv/bin/activate
python -m pytest tests/test_cards.py -v
# 期望: 6 passed
```

---

### Task 3: 牌型识别引擎

**目标：** 实现所有斗地主牌型的识别：单张、对子、三带一/二、顺子、连对、飞机、炸弹、火箭

**文件：**
- 创建: `src/engine/patterns.py`
- 测试: `tests/test_patterns.py`

**牌型定义（15种）：**
```
单张(1), 对子(2), 三不带(3), 三带一(4), 三带二(5),
顺子(6, ≥5张), 连对(7, ≥3连对), 飞机不带(8, ≥2连三),
飞机带单(9), 飞机带双(10), 四带二单(11), 四带二对(12),
炸弹(13), 火箭(14), 无效(0)
```

**关键约束：**
- 顺子不能包含 2 和王
- 飞机不能包含 2 和王
- 火箭 = 大王 + 小王（最大）
- 炸弹 > 普通牌，火箭 > 炸弹

```python
# src/engine/patterns.py
"""
斗地主牌型识别。
输入：一组牌的 List[Card]
输出：(牌型类型, 主牌点数) 或 (INVALID, 0)
"""
from enum import IntEnum
from typing import List, Tuple
from collections import Counter
from src.engine.cards import Card, Rank

class Pattern(IntEnum):
    INVALID = 0
    SINGLE = 1          # 单张
    PAIR = 2            # 对子
    TRIPLE = 3          # 三不带
    TRIPLE_ONE = 4      # 三带一
    TRIPLE_TWO = 5      # 三带二
    STRAIGHT = 6        # 顺子 (≥5)
    STRAIGHT_PAIR = 7   # 连对 (≥3连对)
    PLANE = 8           # 飞机不带 (≥2连三)
    PLANE_SINGLE = 9    # 飞机带单
    PLANE_PAIR = 10     # 飞机带双
    FOUR_TWO_SINGLE = 11  # 四带二单
    FOUR_TWO_PAIR = 12    # 四带二对
    BOMB = 13           # 炸弹
    ROCKET = 14         # 火箭

def identify_pattern(cards: List[Card]) -> Tuple[Pattern, int]:
    """
    识别牌型，返回 (Pattern, 主点数 rank.value)。
    rank.value 用于比较大小。
    """
    if not cards:
        return Pattern.INVALID, 0

    n = len(cards)
    counter = Counter(c.rank for c in cards)
    counts = sorted(counter.values(), reverse=True)

    # 火箭：大王+小王
    if n == 2 and Rank.BIG_JOKER in counter and Rank.SMALL_JOKER in counter:
        return Pattern.ROCKET, Rank.BIG_JOKER.value

    # 炸弹：4张同点数
    if n == 4 and counts == [4]:
        main_rank = max(counter.keys(), key=lambda r: r.value)
        return Pattern.BOMB, main_rank.value

    # 单张
    if n == 1:
        r = cards[0].rank
        return Pattern.SINGLE, r.value

    # 对子
    if n == 2 and counts == [2]:
        r = cards[0].rank
        return Pattern.PAIR, r.value

    # 三不带
    if n == 3 and counts == [3]:
        r = cards[0].rank
        return Pattern.TRIPLE, r.value

    # 三带一 / 三带二 / 四带二等 —— 见下方完整实现
    return _identify_complex(cards, counter, counts, n)
```

完整实现需包括 `_identify_complex` 处理顺子/连对/飞机/带牌等。详细代码在 Task 3 实施时写出。

**测试覆盖 15 种牌型 + 边界情况。**

**验证：**
```bash
cd /ubuntu/doudizhu && source .venv/bin/activate
python -m pytest tests/test_patterns.py -v
# 期望: 20+ passed
```

---

### Task 4: 出牌规则引擎

**目标：** 判断一手牌能否压过上一手牌

**文件：**
- 创建: `src/engine/rules.py`
- 测试: `tests/test_rules.py`

```python
# src/engine/rules.py
"""
出牌规则：判断一手牌是否能压过目标牌。
"""
from typing import List
from src.engine.cards import Card
from src.engine.patterns import identify_pattern, Pattern

def can_beat(my_cards: List[Card], target_cards: List[Card] | None) -> bool:
    """
    判断 my_cards 能否压过 target_cards。
    - target_cards 为 None 表示自由出牌（开局或接牌后新回合）
    - 牌型必须相同（除炸弹/火箭可压任何牌型）
    - 同牌型点数必须更大
    """
    if not target_cards:
        # 自由出牌：任何有效牌型都可
        pat, _ = identify_pattern(my_cards)
        return pat != Pattern.INVALID

    my_pat, my_main = identify_pattern(my_cards)
    tar_pat, tar_main = identify_pattern(target_cards)

    if my_pat == Pattern.INVALID:
        return False

    # 火箭最大
    if my_pat == Pattern.ROCKET:
        return True

    # 炸弹可压非炸弹/非火箭
    if my_pat == Pattern.BOMB and tar_pat not in (Pattern.BOMB, Pattern.ROCKET):
        return True

    # 炸弹压炸弹：点数大者胜
    if my_pat == Pattern.BOMB and tar_pat == Pattern.BOMB:
        return my_main > tar_main

    # 同牌型比大小
    if my_pat == tar_pat and len(my_cards) == len(target_cards):
        return my_main > tar_main

    return False


def get_all_playable(current: List[Card], last_play: List[Card] | None) -> List[List[Card]]:
    """
    从当前手牌中找出所有能压过 last_play 的出牌组合。
    如果 last_play 为 None，返回所有可能的出牌组合。
    """
    # 此函数较复杂，在实施时详写
    # 策略：枚举所有可能组合（优化：先找同牌型，再找炸弹/火箭）
    pass
```

**验证：**
```bash
cd /ubuntu/doudizhu && source .venv/bin/activate
python -m pytest tests/test_rules.py -v
# 期望: 10+ passed
```

---

### Task 5: 游戏状态机

**目标：** 管理一局斗地主从发牌到结束的完整状态流转

**文件：**
- 创建: `src/engine/game.py`
- 测试: `tests/test_game.py`

**状态流转：**
```
DEAL → CALL_LANDLORD → PLAYING → (重复出牌)... → GAME_OVER
```

**关键属性：**
- `players`: 3 个玩家的手牌
- `landlord_idx`: 地主索引 (0=玩家, 1=AI1, 2=AI2)
- `bottom_cards`: 底牌
- `current_player`: 当前出牌者
- `last_play`: 上一手牌（用于比较）
- `pass_count`: 连续过牌次数
- `history`: 出牌历史

**核心方法：**
- `start()`: 发牌 + 叫地主
- `play(cards)`: 出牌
- `pass_turn()`: 过牌
- `is_game_over()`: 判断游戏是否结束
- `get_winner()`: 获取胜方

**验证：**
```bash
cd /ubuntu/doudizhu && source .venv/bin/activate
python -m pytest tests/test_game.py -v
# 期望: 8+ passed
```

---

## Phase 2：AI 引擎（约 90 分钟）

### Task 6: AI 基类 + 随机 AI

**目标：** 定义 AI 接口，实现随机 AI 作为基线

**文件：**
- 创建: `src/ai/base.py`
- 创建: `src/ai/random_ai.py`
- 测试: `tests/test_ai.py`（追加）

```python
# src/ai/base.py
from abc import ABC, abstractmethod
from typing import List, Optional
from src.engine.cards import Card

class BaseAI(ABC):
    """AI 基类"""
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def decide(self, hand: List[Card], last_play: Optional[List[Card]],
               history: List, position: int) -> Optional[List[Card]]:
        """
        决定出牌。
        返回 None 表示过牌。
        position: 0=地主, 1=农民1, 2=农民2
        """
        pass
```

```python
# src/ai/random_ai.py
import random
from typing import List, Optional
from src.engine.cards import Card
from src.engine.rules import get_all_playable, can_beat
from src.ai.base import BaseAI

class RandomAI(BaseAI):
    """随机 AI：从合法出牌中随机选一组"""
    def __init__(self, pass_rate: float = 0.3):
        super().__init__("RandomAI")
        self.pass_rate = pass_rate

    def decide(self, hand, last_play, history, position):
        if last_play and random.random() < self.pass_rate:
            return None  # 过牌
        options = get_all_playable(hand, last_play)
        return random.choice(options) if options else None
```

**验证：** 能跑通一局完整游戏（AI vs AI vs AI）。

---

### Task 7: 规则 AI

**目标：** 实现基于启发式规则的 AI，比随机 AI 强

**策略要点：**
1. 优先出最小的合法牌（保留大牌）
2. 有炸弹时不急着出
3. 农民模式：配合队友（队友出牌时尽量不过牌）
4. 地主模式：压死农民

**验证：** 与随机 AI 对局 1000 次，胜率 > 60%。

---

### Task 8: 蒙特卡洛搜索 AI（主力 AI）

**目标：** 实现轻量级 MCTS，每手牌模拟 100-500 局选最优

**简化 MCTS：**
- 不建树，纯随机模拟
- 对每种合法出牌，模拟 N 局随机出牌，选胜率最高的
- 模拟中用规则 AI 填充对手决策

**验证：** 与规则 AI 对局 1000 次，胜率 > 55%。

---

## Phase 3：TUI 界面（约 60 分钟）

### Task 9: 牌面渲染

**目标：** 用 `rich` 在终端渲染扑克牌

**文件：**
- 创建: `src/ui/display.py`

**设计：** 每张牌渲染成 5x7 的彩色方块：
```
┌─────┐
│♠A   │
│  ♠  │
│     │
│   A♠│
└─────┘
```
使用 `rich` 的 `Panel`、`Text`、`Table` 组合。

**函数：**
- `render_card(card) → Panel`：渲染单张牌
- `render_hand(cards, selected=[]) → Table`：渲染一手牌（带序号选择）
- `render_game_state(game) → Layout`：渲染完整游戏界面

---

### Task 10: 主 TUI 循环

**目标：** 实现交互式游戏循环

**文件：**
- 创建: `src/ui/tui.py`
- 创建: `main.py`

**交互流程：**
```
1. 显示手牌（带序号 1-17）
2. 玩家输入：序号选牌 → 出牌 / 输入 p 过牌
3. AI 自动出牌
4. 更新显示
5. 直到有人出完
```

**`main.py` 入口：**
```python
# main.py
"""斗地主 TUI 游戏入口"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.tui import GameTUI
from src.ai.mcts_ai import MCTSAI

def main():
    tui = GameTUI(ai_class=MCTSAI)
    tui.run()

if __name__ == "__main__":
    main()
```

**验证：** 完整运行一局，玩家操作流畅，AI 正常出牌。

---

## Phase 4：完善 + 文档（约 30 分钟）

### Task 11: 用户文档

**文件：**
- 完善: `README.md`
- 创建: `docs/USER_GUIDE.md`

**README.md 内容：**
- 项目简介 + 截图（ASCII）
- 快速开始（3 条命令）
- 操作说明
- 牌型参考

**`docs/USER_GUIDE.md` 内容：**
- 详细安装步骤
- 游戏规则回顾
- 操作指南（选牌 / 出牌 / 过牌 / 快捷键）
- AI 难度说明
- 常见问题

---

### Task 12: 最终验证

**验证命令：**
```bash
cd /ubuntu/doudizhu && source .venv/bin/activate
# 全部测试
python -m pytest tests/ -v
# 期望: 所有测试通过
```

---

## 总结

| 指标 | 值 |
|------|-----|
| 总 Task 数 | 12 |
| 预计总时间 | ~4 小时 |
| 核心文件数 | ~15 个 |
| 预计代码量 | ~2000 行 |
| 外部依赖 | `rich`（仅 TUI 渲染） |
| AI 水平 | 蒙特卡洛（≈ 中级玩家） |
