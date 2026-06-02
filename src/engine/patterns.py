"""
斗地主牌型识别引擎。

识别 15 种牌型，返回 (Pattern枚举, 主点数value)。
主点数用于比较同牌型大小。
"""
from enum import IntEnum
from typing import List, Tuple, Dict
from collections import Counter
from src.engine.cards import Card, Rank, STRAIGHT_VALID_RANKS


class Pattern(IntEnum):
    INVALID = 0
    SINGLE = 1           # 单张
    PAIR = 2             # 对子
    TRIPLE = 3           # 三不带
    TRIPLE_ONE = 4       # 三带一
    TRIPLE_TWO = 5       # 三带二
    STRAIGHT = 6         # 顺子 (≥5)
    STRAIGHT_PAIR = 7    # 连对 (≥3连对)
    PLANE = 8            # 飞机不带 (≥2连三)
    PLANE_SINGLE = 9     # 飞机带单
    PLANE_PAIR = 10      # 飞机带双
    FOUR_TWO_SINGLE = 11 # 四带二单
    FOUR_TWO_PAIR = 12   # 四带二对
    BOMB = 13            # 炸弹
    ROCKET = 14          # 火箭（大王+小王）


PATTERN_NAMES = {
    Pattern.INVALID: "无效",
    Pattern.SINGLE: "单张",
    Pattern.PAIR: "对子",
    Pattern.TRIPLE: "三不带",
    Pattern.TRIPLE_ONE: "三带一",
    Pattern.TRIPLE_TWO: "三带二",
    Pattern.STRAIGHT: "顺子",
    Pattern.STRAIGHT_PAIR: "连对",
    Pattern.PLANE: "飞机",
    Pattern.PLANE_SINGLE: "飞机带单",
    Pattern.PLANE_PAIR: "飞机带双",
    Pattern.FOUR_TWO_SINGLE: "四带二单",
    Pattern.FOUR_TWO_PAIR: "四带二对",
    Pattern.BOMB: "炸弹",
    Pattern.ROCKET: "火箭",
}


def identify_pattern(cards: List[Card]) -> Tuple[Pattern, int]:
    """
    识别牌型，返回 (Pattern, 主点数value)。
    main_rank_value 用于比较同牌型大小（火箭返回17，炸弹返回炸弹点数）。
    """
    if not cards:
        return Pattern.INVALID, 0

    n = len(cards)
    counter: Dict[Rank, int] = Counter(c.rank for c in cards)
    counts = sorted(counter.values(), reverse=True)

    # 火箭：大王 + 小王
    if n == 2 and Rank.BIG_JOKER in counter and Rank.SMALL_JOKER in counter:
        return Pattern.ROCKET, Rank.BIG_JOKER.value

    # 炸弹：4张同点数（不是火箭）
    if n == 4 and counts == [4]:
        rank = next(r for r, cnt in counter.items() if cnt == 4)
        return Pattern.BOMB, rank.value

    # 单张
    if n == 1:
        return Pattern.SINGLE, cards[0].rank.value

    # 对子
    if n == 2 and counts == [2]:
        return Pattern.PAIR, cards[0].rank.value

    # 三不带
    if n == 3 and counts == [3]:
        return Pattern.TRIPLE, cards[0].rank.value

    # --- 复杂牌型 ---
    return _identify_complex(cards, counter, n)


def _identify_complex(
    cards: List[Card], counter: Dict[Rank, int], n: int
) -> Tuple[Pattern, int]:
    """识别复杂牌型"""
    counts = sorted(counter.values(), reverse=True)

    # 三带一：数量分布 [3, 1]
    if n == 4 and counts == [3, 1]:
        main_rank = _find_rank_with_count(counter, 3)
        return Pattern.TRIPLE_ONE, main_rank.value

    # 三带二：数量分布 [3, 2]
    if n == 5 and counts == [3, 2]:
        main_rank = _find_rank_with_count(counter, 3)
        return Pattern.TRIPLE_TWO, main_rank.value

    # 四带二单：n=6, [4,1,1]
    if n == 6 and counts == [4, 1, 1]:
        main_rank = _find_rank_with_count(counter, 4)
        return Pattern.FOUR_TWO_SINGLE, main_rank.value

    # 四带二对：n=8, [4,2,2]
    if n == 8 and counts == [4, 2, 2]:
        main_rank = _find_rank_with_count(counter, 4)
        return Pattern.FOUR_TWO_PAIR, main_rank.value

    # 顺子 / 连对 / 飞机系列（需要检测连续段）
    return _identify_sequential(cards, counter, n)


def _find_rank_with_count(counter: Dict[Rank, int], target: int) -> Rank:
    for rank, cnt in counter.items():
        if cnt == target:
            return rank
    raise ValueError(f"No rank with count {target}")


def _identify_sequential(
    cards: List[Card], counter: Dict[Rank, int], n: int
) -> Tuple[Pattern, int]:
    """
    识别顺子 / 连对 / 飞机（需要点数连续段的牌型）。

    返回 (Pattern, main_value)
    """
    # 收集所有出现的 rank（排序）
    all_present = sorted(
        [r for r in counter.keys()],
        key=lambda r: r.value
    )

    # --- 顺子 (STRAIGHT) ---
    # 条件：每张牌 rank 不同，全是单张，≥5 张，连续，不含 2/W
    if n >= 5 and all(cnt == 1 for cnt in counter.values()):
        ranks_only = [r.value for r in all_present]
        if _is_consecutive(ranks_only) and _all_valid_for_straight(all_present):
            return Pattern.STRAIGHT, max(ranks_only)

    # --- 连对 (STRAIGHT_PAIR) ---
    # 条件：每个 rank 有 2 张，≥3 连对，连续，不含 2/W
    if n >= 6 and n % 2 == 0 and all(cnt == 2 for cnt in counter.values()):
        ranks_only = [r.value for r in all_present]
        if (len(ranks_only) >= 3 and _is_consecutive(ranks_only)
                and _all_valid_for_straight(all_present)):
            return Pattern.STRAIGHT_PAIR, max(ranks_only)

    # --- 飞机 / 飞机带牌 ---
    plane_result = _find_plane(counter, all_present, n)
    if plane_result[0] != Pattern.INVALID:
        return plane_result

    return Pattern.INVALID, 0


def _is_consecutive(ranks: List[int]) -> bool:
    """判断 rank 值列表是否连续递增"""
    if len(ranks) < 2:
        return len(ranks) == 1
    for i in range(1, len(ranks)):
        if ranks[i] - ranks[i-1] != 1:
            return False
    return True


def _all_valid_for_straight(ranks: List[Rank]) -> bool:
    """检查所有 rank 是否在顺子合法范围内（3-14，不含2和王）"""
    return all(r.value in STRAIGHT_VALID_RANKS for r in ranks)


def _find_plane(
    counter: Dict[Rank, int], all_present: List[Rank], n: int
) -> Tuple[Pattern, int]:
    """
    在牌中查找飞机组合。
    - 至少 2 组连续的三张
    - 不能包含 2 和王的三张部分
    - 带牌方式：不带 / 带单 / 带双
    """
    # 找出所有数量 ≥3 的 rank
    triple_ranks = sorted(
        [r for r, cnt in counter.items() if cnt >= 3],
        key=lambda r: r.value
    )

    # 对每个可能的连续段尝试
    for seg_len in range(len(triple_ranks), 1, -1):  # 从最长开始
        for start in range(len(triple_ranks) - seg_len + 1):
            end = start + seg_len
            segment = triple_ranks[start:end]
            seg_values = [r.value for r in segment]

            if not _is_consecutive(seg_values):
                continue
            if not _all_valid_for_straight(segment):
                continue

            # 这个连续三张段是合法的飞机核心
            # 计算带牌数量
            triple_card_count = seg_len * 3
            remaining = n - triple_card_count

            if remaining == 0:
                return Pattern.PLANE, segment[-1].value
            elif remaining == seg_len:
                return Pattern.PLANE_SINGLE, segment[-1].value
            elif remaining == seg_len * 2:
                return Pattern.PLANE_PAIR, segment[-1].value

    return Pattern.INVALID, 0
