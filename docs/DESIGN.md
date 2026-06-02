# 斗地主 AI-TUI 技术设计文档

> 版本: 1.0 | 作者: Hermes Agent | 日期: 2026-05-31

---

## 目录

1. [系统架构](#1-系统架构)
2. [牌面引擎设计](#2-牌面引擎设计)
3. [牌型识别算法](#3-牌型识别算法)
4. [规则引擎设计](#4-规则引擎设计)
5. [游戏状态机设计](#5-游戏状态机设计)
6. [AI 引擎设计](#6-ai-引擎设计)
7. [TUI 界面设计](#7-tui-界面设计)
8. [数据流与模块契约](#8-数据流与模块契约)

---

## 1. 系统架构

```
┌──────────────────────────────────────────────────┐
│                    main.py                       │
│                 (入口 + 参数解析)                  │
└──────────────┬───────────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │    ui/tui.py         │  ← TUI 循环，用户交互
    │  GameTUI.run()       │
    └────┬────────────┬────┘
         │            │
    ┌────▼────┐  ┌────▼─────┐
    │ engine/ │  │   ai/     │
    │ game.py │◄─┤ mcts_ai   │  ← AI 读 game 状态，返回出牌
    │ 状态机   │  │ rule_ai   │
    └────┬────┘  └──────────┘
         │
    ┌────▼─────┐
    │ patterns │  ← 牌型识别（纯函数）
    │ rules    │  ← 出牌合法性（纯函数）
    │ cards    │  ← 牌面数据结构
    └──────────┘
```

**分层原则：**
- `engine/` 层零依赖，纯逻辑，不碰 UI、不碰 AI
- `ai/` 层只读 game 状态，返回 `List[Card]` 或 `None`
- `ui/` 层只渲染和接收输入，不包含游戏逻辑
- `main.py` 只做组装

---

## 2. 牌面引擎设计

### 2.1 数据结构

```
Card（一张牌）
├── rank: Rank      # 点数枚举 3~17
├── suit: Suit|None # 花色，大小王为 None
└── __str__()       # "♠ A", "♠10", "🃏", "👑"

Rank 枚举（值 = 用于比较大小的数值）
┌─────────────┬───────┬──────────┐
│ 牌名        │ value │ 说明     │
├─────────────┼───────┼──────────┤
│ THREE       │   3   │          │
│ FOUR        │   4   │          │
│ FIVE        │   5   │          │
│ SIX         │   6   │          │
│ SEVEN       │   7   │          │
│ EIGHT       │   8   │          │
│ NINE        │   9   │          │
│ TEN         │  10   │          │
│ JACK        │  11   │          │
│ QUEEN       │  12   │          │
│ KING        │  13   │          │
│ ACE         │  14   │ A       │
│ TWO         │  15   │ 最大单牌 │
│ SMALL_JOKER │  16   │ 小王    │
│ BIG_JOKER   │  17   │ 大王    │
└─────────────┴───────┴──────────┘

Suit 枚举（值 = 同级比较）
SPADE(4) > HEART(3) > CLUB(2) > DIAMOND(1)
```

**排序规则：** `sort_cards()` 按 `(rank.value, suit.value)` 降序，大牌在前。大小王 suit 视为 0。

### 2.2 发牌算法

```python
# 标准 Fisher-Yates 洗牌
shuffled = random.shuffle(deck)

# 分牌：前 3 份各 17 张（玩家），最后 3 张底牌
# 发牌顺序在规则引擎中处理（待叫地主后分配底牌）
```

---

## 3. 牌型识别算法

### 3.1 牌型定义

共识别 **15 种**牌型。每种牌型识别后返回 `(Pattern, main_rank_value)`：

| ID | 牌型 | 牌数 | 示例 | 说明 |
|----|------|------|------|------|
| 0 | INVALID | — | — | 无效组合 |
| 1 | SINGLE | 1 | ♠ A | 单张 |
| 2 | PAIR | 2 | ♠A♣A | 对子 |
| 3 | TRIPLE | 3 | 三张同点数 | 三不带 |
| 4 | TRIPLE_ONE | 4 | 三张+1单 | 三带一 |
| 5 | TRIPLE_TWO | 5 | 三张+1对 | 三带二 |
| 6 | STRAIGHT | ≥5 | 34567 | 顺子（不含2和王） |
| 7 | STRAIGHT_PAIR | 偶数≥6 | 连对 ≥3连 | 不含2和王 |
| 8 | PLANE | 3k | 飞机不带 ≥2连三 | 不含2和王 |
| 9 | PLANE_SINGLE | 4k | 飞机带单牌 | k个三带k个单 |
| 10 | PLANE_PAIR | 5k | 飞机带对子 | k个三带k个对 |
| 11 | FOUR_TWO_SINGLE | 6 | 四张+2单 | 四带二单 |
| 12 | FOUR_TWO_PAIR | 8 | 四张+2对 | 四带二对 |
| 13 | BOMB | 4 | 四张同点 | 炸弹 |
| 14 | ROCKET | 2 | 大王+小王 | 火箭（最大） |

### 3.2 识别算法

```
function identify_pattern(cards):
    if cards 为空 → INVALID
    n = len(cards)
    counter = Counter(c.rank for c in cards)
    
    # 火箭检测
    if n == 2 and 大王 in counter and 小王 in counter:
        return (ROCKET, 17)
    
    # 炸弹检测
    if n == 4 and max(counts) == 4:
        return (BOMB, 四张牌的rank.value)
    
    # 按长度分支
    if n == 1 → SINGLE
    if n == 2 → PAIR (需同rank)
    if n == 3 → TRIPLE (需同rank)
    if n ≥ 5 → _try_straight_and_plane(cards, counter)
    if n == 4 → _try_triple_one_or_bomb(cards, counter)
    if n == 5 → _try_triple_two_or_straight(cards, counter)
    if n == 6 → _try_four_two_single_or_straight_or_plane
    if n == 8 → _try_four_two_pair_or_straight_pair_or_plane_pair
    ...
```

### 3.3 顺子检测（核心算法）

```python
def _is_straight(ranks: List[int], min_len: int = 5) -> bool:
    """
    判断一组rank值是否构成合法顺子。
    约束：
    1. 连续递增
    2. 不能包含 2(15)、小王(16)、大王(17)
    3. 长度 ≥ min_len
    4. 最大点数为 A(14)，即 10JQKA 合法，JQKA2 不合法
    """
    if len(ranks) < min_len:
        return False
    sorted_ranks = sorted(set(ranks))
    if any(r >= 15 for r in sorted_ranks):  # 不能含2和王
        return False
    if sorted_ranks[-1] > 14:  # A是顺子最大
        return False
    if len(sorted_ranks) != len(ranks):
        return False  # 有重复
    for i in range(1, len(sorted_ranks)):
        if sorted_ranks[i] - sorted_ranks[i-1] != 1:
            return False
    return True
```

### 3.4 飞机检测（核心算法）

```python
def _is_plane(cards, counter) -> (Pattern, main_rank):
    """
    飞机：至少2组连续的三张（点数连续）
    连三部分不能含2和王。
    带牌数量 = 连三组数（带单）或 连三组数 × 2（带双）
    """
    triples = [r for r, cnt in counter.items() if cnt >= 3]
    triples = sorted(triples, key=lambda r: r.value)
    
    # 找最长连续三张段
    for start in range(len(triples)):
        end = start
        while end < len(triples) and end - start == triples[end].value - triples[start].value:
            end += 1
        seg_len = end - start
        if seg_len >= 2 and triples[end-1].value <= 14:  # A及以下
            full_triple_ranks = triples[start:end]
            triple_card_count = seg_len * 3
            remaining = n - triple_card_count  # 剩余牌数
            
            if remaining == 0:
                return (PLANE, full_triple_ranks[-1].value)
            elif remaining == seg_len:
                return (PLANE_SINGLE, full_triple_ranks[-1].value)
            elif remaining == seg_len * 2:
                return (PLANE_PAIR, full_triple_ranks[-1].value)
    return (INVALID, 0)
```

### 3.5 大小比较规则

```
比较两张同牌型的手牌：
1. 火箭 > 一切
2. 炸弹牌型 > 非炸弹牌型（如果对方不是炸弹/火箭）
3. 炸弹 vs 炸弹：比较炸弹点数
4. 同牌型 vs 同牌型且同张数：比较 main_rank_value
5. 否则：不能出（不合法）
```

---

## 4. 规则引擎设计

### 4.1 核心函数

```python
def can_beat(my_cards: List[Card], last_play: Optional[List[Card]]) -> bool:
    """
    last_play = None → 自由出牌（任意有效牌型）
    last_play != None → 必须牌型匹配且更大，或炸弹/火箭
    """

def get_all_playable(hand: List[Card], last_play: Optional[List[Card]]) -> List[List[Card]]:
    """
    枚举当前手牌中所有能压过 last_play 的出牌组合。
    这是 AI 决策的输入。
    
    优化策略（减少组合爆炸）：
    1. 先找同牌型组合（如果 last_play 非空）
    2. 再找炸弹和火箭
    3. 如果 last_play 为空，遍历所有可能牌型：
       - 所有单张
       - 所有对子
       - 所有三张（及带牌）
       - 所有顺子（长度5到最大可能）
       - 所有连对
       - 所有飞机
       - 所有炸弹
       - 火箭（如果有）
    """
```

### 4.2 合法出牌枚举（详细策略）

```
枚举顺序（优先级从高到低，找到足够候选后提前终止）：

1. 如果 last_play 为空（自由出牌）：
   a. 火箭（如有）
   b. 所有炸弹
   c. 所有单张
   d. 所有对子
   e. 所有三张 + 三带一/二
   f. 所有顺子（长度 5→max）
   g. 所有连对（长度 3连→max）
   h. 所有飞机（2连→max，各带牌方式）
   i. 四带二单/对

2. 如果 last_play 非空：
   a. 火箭（如有，必定合法）
   b. 比 last_play 大的炸弹（如有）
   c. 同牌型比 last_play 大的组合
```

### 4.3 组合生成算法

```python
def _gen_singles(hand) -> List[List[Card]]:
    """生成所有单张"""
    return [[c] for c in hand]

def _gen_pairs(hand, counter) -> List[List[Card]]:
    """生成所有对子"""
    return [cards for r in ranks_where_count>=2]

def _gen_triples_with_kickers(hand, counter) -> List[List[Card]]:
    """生成所有三张及带牌组合"""
    # 对每个 count>=3 的 rank：
    #   从剩余牌中选 0~2 张作为带牌
    #   (0张→三不带, 1张随机→三带一, 1对→三带二)

def _gen_straights(hand, counter, min_len=5) -> List[List[Card]]:
    """生成顺子：滑动窗口扫描所有连续段"""
    possible_ranks = sorted(set(r.value for r in ranks_where_count>=1 if r < 15))
    for start in range(len(possible_ranks)):
        end = start
        while end < len(possible_ranks) and \
              possible_ranks[end] == possible_ranks[start] + (end - start):
            seg_len = end - start + 1
            if seg_len >= min_len and possible_ranks[end] <= 14:
                # 每种长度生成一组顺子
                ...

def _gen_planes(hand, counter) -> List[List[Card]]:
    """生成飞机组合"""
    # 同顺子逻辑，但找 count>=3 的连续段（≥2连）
    # 带牌由剩余牌中生成组合
```

---

## 5. 游戏状态机设计

### 5.1 状态定义

```
     发牌
      │
      ▼
  ┌──────────┐
  │ 叫地主    │  3人轮询叫/不叫
  │ CALLING  │  叫分: 1分/2分/3分
  └────┬─────┘
       │ 地主确定
       ▼
  ┌──────────┐
  │ 出牌中    │◄──── 循环 ────┐
  │ PLAYING  │               │
  └────┬─────┘               │
       │                     │
       ├─ 有人出完牌 ─────────┤
       │                     │
       │  游戏结束            │
       ▼                     │
  ┌──────────┐              │
  │ GAME_OVER│              │
  └──────────┘              │
                             │
       ┌─────────────────────┘
       │ 两人连续过牌 → 新回合
       │ 当前回合最后出牌者获得自由出牌权
       └── last_play 重置为 None
```

### 5.2 状态机核心字段

```python
@dataclass
class GameState:
    # 玩家数据
    players: List[Player]              # [玩家, AI1, AI2]
    landlord_idx: int                  # 0/1/2
    bottom_cards: List[Card]           # 底牌（3张，地主获得）

    # 回合数据
    current_player: int                # 当前该谁出牌
    last_play: Optional[List[Card]]    # 上一手有效出牌
    last_player: Optional[int]         # 上一手谁出的
    pass_count: int                    # 连续过牌次数
    round_count: int                   # 回合计数

    # 历史
    history: List[PlayRecord]          # 完整出牌历史

    # 状态
    phase: GamePhase                   # CALLING / PLAYING / GAME_OVER
```

### 5.3 状态转换表

```
当前状态      事件              下一状态        副作用
─────────────────────────────────────────────────────
CALLING      玩家叫地主          CALLING         记录叫分
CALLING      三人都不叫          CALLING         重新发牌
CALLING      有人叫3分终局       PLAYING         分配底牌+地主身份
PLAYING      出牌（未被压）      PLAYING         last_play 更新
PLAYING      出牌（被压）        PLAYING         last_play 更新，pass_count 归零
PLAYING      过牌                PLAYING         pass_count += 1
PLAYING      过牌数=2            PLAYING         pass_count 归零，last_play=None（新回合）
PLAYING      某人手牌数=0        GAME_OVER       计算胜负
```

### 5.4 胜负判定

```
地主手牌先出完 → 地主胜
任一农民手牌先出完 → 农民胜
```

**扩展（未来可加）：**
- 春天：对手未出过任何牌 → 加倍
- 反春：地主只出过一手牌 → 农民加倍

---

## 6. AI 引擎设计

### 6.1 AI 接口契约

```python
class BaseAI(ABC):
    name: str

    @abstractmethod
    def decide(
        self,
        hand: List[Card],              # 当前手牌
        last_play: Optional[List[Card]], # 上一手牌
        game_context: GameContext,       # 游戏上下文
    ) -> Optional[List[Card]]:
        """
        返回要出的牌，或 None 表示过牌。
        hand 已排序（大牌在前）。
        """
```

```python
@dataclass
class GameContext:
    """给 AI 提供游戏上下文"""
    position: Literal["landlord", "farmer1", "farmer2"]
    players_hand_count: List[int]    # 其他玩家的剩余牌数
    history: List[PlayRecord]        # 出牌历史
    bottom_cards: List[Card]         # 底牌（地主可见）
```

### 6.2 随机 AI（基线）

```
策略：从所有合法出牌中随机选一组
     有 30% 概率过牌（如果必须接牌）
     
用途：确保游戏能跑通，作为 AI 水平的下限基线
```

### 6.3 规则 AI（启发式）

```
决策树（优先级从高到低）：

1. 只剩一手牌→直接出完
2. 顺子 / 飞机中有能整手出完的→出
3. 如果是必须接牌的情况：
   a. 优先出最小的合法牌组（保留大牌）
   b. 有炸弹但对方手牌还很多→不用炸弹
   c. 对方只剩 1-3 张→有炸弹就炸
4. 如果是自由出牌：
   a. 优先出单张最小的牌（先走弱牌）
   b. 其次出顺子/对子（减少手牌复杂度）
   c. 保留炸弹和大牌到最后
5. 农民模式特殊规则：
   a. 队友出牌时倾向于过牌（给队友空间）
   b. 地主出牌时积极压牌
```

### 6.4 蒙特卡洛搜索 AI（主力）

```
算法：Flat Monte Carlo（不做树搜索，纯随机模拟）

function MCTS_decide(hand, last_play, context):
    options = get_all_playable(hand, last_play)
    if not options:
        return None  # 必须过牌
    
    # 如果只有一个选择，直接返回
    if len(options) == 1:
        return options[0]
    
    # 对每个合法出牌选项，模拟 N 局
    scores = []
    for play in options:
        wins = 0
        for i in range(N):  # N = 100~500
            sim_result = simulate_game(hand - play, context, play)
            if sim_result == WIN:
                wins += 1
        scores.append(wins / N)
    
    return options[argmax(scores)]

function simulate_game(my_remaining_hand, context, my_play):
    """
    模拟一局随机游戏：
    - 用随机 AI 填充所有对手的决策
    - 模拟直到游戏结束
    - 返回 WIN/LOSE
    """
    sim_context = context.clone()
    sim_context.update_after_play(my_play)
    
    while not game_over(sim_context):
        if current_player == me:
            # 用自己的手牌 + 随机AI策略
            play = RandomAI.decide(my_remaining_hand, ...)
        else:
            play = RandomAI.decide(sim_opponent_hand, ...)
    
    return WIN if winner == me else LOSE
```

**性能优化：**
- 模拟时用规则 AI 替代随机 AI（提高模拟质量）
- 对手剩余牌 ≤ 3 张时，用精确计算替代模拟
- 缓存同手牌+同局面的模拟结果（短期缓存）
- N 的默认值：100（快速），200（均衡），500（精准，适用于关键决策）

### 6.5 AI 难度分级（面向用户）

```
难度 1 - 新手（RandomAI + 高过牌率）
  N/A，随机出牌，过牌率 50%

难度 2 - 普通（RuleAI）
  启发式规则，有基本策略

难度 3 - 高手（MCTSAI, N=100）
  蒙特卡洛 100 次模拟

难度 4 - 大师（MCTSAI, N=500）
  蒙特卡洛 500 次模拟，每手牌延迟约 1-2 秒
```

---

## 7. TUI 界面设计

### 7.1 布局规范

终端最小要求：**120 列 × 30 行**

```
┌────────────────────────────────────────────────────────────┐
│  ♢ 斗地主 ─────────────── 第 3 回合 ───────────────── ♢    │  ← 标题栏
├────────────────────────────────────────────────────────────┤
│                                                            │
│    AI 农民 2 (剩余: 12张)                                   │  ← 对手信息
│    ┌─┐ ┌─┐ ┌─┐ ┌─┐                                        │
│    │?│ │?│ │?│ │?│ ... (隐藏，只显示数量)                   │
│    └─┘ └─┘ └─┘ └─┘                                        │
│                                                            │
│    上一手: ♠ 5 (由 AI 农民 2 出)                             │  ← 上一手牌
│                                                            │
│    AI 农民 1 (剩余: 8张)                                    │  ← 另一对手
│    ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐                       │
│    │?│ │?│ │?│ │?│ │?│ │?│ │?│ │?│                        │
│    └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘ └─┘                       │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  你的手牌 (17张)                                            │  ← 玩家区域
│      1         2         3         4                        │
│   ┌────┐    ┌────┐    ┌────┐    ┌────┐     ...              │
│   │♠ 3 │    │♥ 4 │    │♣ 7 │    │♦ 8 │                      │
│   └────┘    └────┘    └────┘    └────┘                      │
│        ↑ 已选中 (黄底高亮整张牌)                                │
├────────────────────────────────────────────────────────────┤
│  牌型: 单张 ♠ A |  命令: [选牌] 1-17 [Enter]出牌 [P]过牌   │  ← 命令栏
│  选中: ♠ A ♥ K |        [Q]退出                             │
└────────────────────────────────────────────────────────────┘
```

### 7.2 牌面渲染规格

每张牌4行方框格式，序号在上方居中，框线+牌面按花色着色。

```
    1         2         3         4
┌────┐    ┌────┐    ┌────┐    ┌────┐
│♠ A │    │♥ K │    │♣10 │    │ 🃏 │
└────┘    └────┘    └────┘    └────┘
   ↑ 选中时整张黄底高亮（序号+框+牌面）
```

### 7.3 颜色方案

```python
COLORS = {
    "spade":   "white",      # ♠ 黑桃 → 白色
    "heart":   "red",        # ♥ 红心 → 红色
    "club":    "green",      # ♣ 梅花 → 绿色
    "diamond": "yellow",     # ♦ 方块 → 黄色
    "joker_small": "cyan",   # 🃏 小王 → 青色
    "joker_big":   "magenta",# 👑 大王 → 洋红
    "card_border": "dim white",
    "selected_border": "bold yellow",
    "info_text": "dim cyan",
    "player_highlight": "bold green",
}
```

### 7.4 交互设计

```
操作流程：
1. 输入数字选中牌。支持多选：空格分隔 (`1 3 5`)、逗号分隔 (`1,3,5`)、范围 (`1-5`)
2. 选中的牌实时高亮，底部显示当前组合的牌型
3. 按 Enter 确认出牌
4. 如果牌型无效或打不出去 → 显示错误提示，清空选择，重新选牌
5. 按 P 过牌（当前回合有必须接牌时才显示）
6. 按 U 取消最后一张选中
7. 按 S 切换排序方式（按点数 / 按花色）
8. 按 Q 退出游戏

实时反馈：
- 选牌时立即显示牌型名称（如 "顺子 56789"）
- 牌型无效时边框变红，显示 "无效牌型"
- AI 出牌有 0.5s 延迟（看起来像在思考）
- 新回合开始时动画提示 "新回合开始"
```

### 7.5 叫地主界面

```
┌─────────────────────────────────────────────┐
│              叫 地 主                        │
│                                             │
│  你的手牌: ♠ 3 ♥ 4 ♣ 7 ♦ 8 ♠ 9 ...              │
│                                             │
│  请选择:                                     │
│  [1] 不叫                                   │
│  [2] 1 分                                   │
│  [3] 2 分                                   │
│  [4] 3 分                                   │
└─────────────────────────────────────────────┘
```

### 7.6 游戏结束界面

```
┌─────────────────────────────────────────────┐
│            🎉 你 赢 了！ 🎉                   │
│                                             │
│  身份: 地主                                  │
│  回合数: 7                                   │
│  你的出牌历史: 单张×3 对子×2 顺子×1 炸弹×1     │
│  AI1 剩余: 3张                              │
│  AI2 剩余: 5张                              │
│                                             │
│  [R] 再来一局  [Q] 退出                      │
└─────────────────────────────────────────────┘
```

---

## 8. 数据流与模块契约

### 8.1 出牌流程（一次完整交互）

```
用户按键
    │
    ▼
┌─────────┐  get_all_playable(hand, last_play)
│ tui.py  │──────────────────────────────► rules.py
└────┬────┘   返回可选牌组列表
     │
     │ 用户选牌并按 Enter
     ▼
┌─────────┐  game.play(cards)
│ tui.py  │──────────────────────────────► game.py
└────┬────┘                                    │
     │                                  ┌──────▼──────┐
     │                                  │ can_beat()   │
     │                                  └──────┬───────┘
     │                                         │ 合法
     │                                         ▼
     │                                  更新 game_state
     │                                  last_play = cards
     │                                         │
     │    AI 回合                             │
     │    ┌────────────────────────────────────┘
     │    ▼
     │  ┌──────────┐   game.play(ai_cards)
     │  │ mcts_ai  │─────────────────────────► game.py
     │  │ .decide()│
     │  └──────────┘
     │    │
     │    ▼ 渲染
     │  ┌──────────┐
     │  │ display  │  render_game_state()
     │  └──────────┘
     │    │
     └────┘ 循环
```

### 8.2 模块契约清单

| 模块 | 输入 | 输出 | 纯函数 | 副作用 |
|------|------|------|--------|--------|
| `cards.py` | — | Card, Deck | ✅ | 无 |
| `patterns.py` | List[Card] | (Pattern, int) | ✅ | 无 |
| `rules.py` | List[Card], List[Card]|None | bool / List | ✅ | 无 |
| `game.py` | Card[], player_idx | 新 GameState | ❌ | 修改状态 |
| `random_ai.py` | hand, last_play, context | List[Card]|None | ❌ | 随机数 |
| `rule_ai.py` | hand, last_play, context | List[Card]|None | ❌ | 无（确定性） |
| `mcts_ai.py` | hand, last_play, context | List[Card]|None | ❌ | 随机数 |
| `display.py` | GameState | `rich.Table/Panel` | ✅ | 无 |
| `tui.py` | — | — | ❌ | 终端IO |

### 8.3 模块依赖图

```
main.py ──► tui.py ──► game.py ──► rules.py ──► patterns.py ──► cards.py
                │                       │
                ▼                       ▼
            display.py              mcts_ai.py ──► rule_ai.py ──► random_ai.py
```

**关键约束：**
- `engine/` 下所有模块不能导入 `ai/` 或 `ui/`
- `ai/` 只能导入 `engine/` 和 `random`
- `ui/` 可以导入所有模块
- `main.py` 可以导入所有模块

---

## 附录 A：牌型测试用例清单

| 测试用例 | 输入 | 期望 |
|----------|------|------|
| 单张 | [♠3] | (SINGLE, 3) |
| 对子 | [♠A, ♣A] | (PAIR, 14) |
| 顺子 34567 | [♠3,♥4,♣5,♦6,♠7] | (STRAIGHT, 7) |
| 顺子 10JQKA | [各一张] | (STRAIGHT, 14) |
| 顺子含2非法 | [♠Q,♥K,♣A,♦2] | (INVALID, 0) |
| 连对 334455 | [三对] | (STRAIGHT_PAIR, 5) |
| 三带一 | [♠A,♥A,♣A,♦3] | (TRIPLE_ONE, 14) |
| 飞机带单 333444+56 | [六张] | (PLANE_SINGLE, 4) |
| 炸弹 | [♠7,♥7,♣7,♦7] | (BOMB, 7) |
| 火箭 | [🃏, 👑] | (ROCKET, 17) |
| 四带二单 | [♠5×4, ♠3, ♥4] | (FOUR_TWO_SINGLE, 5) |

---

## 附录 B：性能预算

| 操作 | 时间预算 | 说明 |
|------|----------|------|
| 牌型识别 (单次) | <1ms | O(n) n≤20 |
| get_all_playable | <50ms | 最大组合数 ~500 |
| MCTS 100次模拟 | 100-300ms | 每次模拟走完整局 |
| MCTS 500次模拟 | 500-1500ms | |
| TUI 渲染 (刷新) | <10ms | rich 全屏刷新 |
| 玩家操作延迟 | <50ms | 选牌→显示牌型 |
