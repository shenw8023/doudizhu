"""
出牌规则引擎。

can_beat(): 判断一手牌能否压过目标牌
get_all_playable(): 枚举手牌中所有合法出牌组合
"""
from typing import List, Optional, Set, Tuple
from collections import Counter
from itertools import combinations
from src.engine.cards import Card, Rank, sort_cards, STRAIGHT_VALID_RANKS
from src.engine.patterns import identify_pattern, Pattern


def can_beat(my_cards: List[Card], last_play: Optional[List[Card]]) -> bool:
    """
    判断 my_cards 能否压过 last_play。

    规则：
    - last_play 为 None → 任意有效牌型都可出（自由出牌）
    - 火箭 > 一切
    - 炸弹 > 非炸弹/非火箭
    - 炸弹 vs 炸弹 → 点数大者胜
    - 同牌型 + 同张数 → 点数大者胜
    - 否则不可出

    返回 True 表示可以出牌。
    """
    if not last_play:
        pat, _ = identify_pattern(my_cards)
        return pat != Pattern.INVALID

    my_pat, my_main = identify_pattern(my_cards)
    tar_pat, tar_main = identify_pattern(last_play)

    if my_pat == Pattern.INVALID:
        return False

    # 火箭最大
    if my_pat == Pattern.ROCKET:
        return True

    # 炸弹可压非炸弹/非火箭
    if my_pat == Pattern.BOMB and tar_pat not in (Pattern.BOMB, Pattern.ROCKET):
        return True

    # 炸弹压炸弹
    if my_pat == Pattern.BOMB and tar_pat == Pattern.BOMB:
        return my_main > tar_main

    # 同牌型、同张数比大小
    if my_pat == tar_pat and len(my_cards) == len(last_play):
        return my_main > tar_main

    return False


def get_all_playable(
    hand: List[Card], last_play: Optional[List[Card]]
) -> List[List[Card]]:
    """
    从 hand 中找出所有能压过 last_play 的出牌组合。

    如果 last_play 为 None（自由出牌），返回所有可能的出牌组合。
    按出牌数量升序排列（优先出小牌组）。

    优化策略：
    1. 火箭和炸弹直接检查
    2. 同牌型枚举（如果 last_play 非空）
    3. 全枚举（如果 last_play 为空）
    """
    hand_sorted = sort_cards(hand)
    options: List[List[Card]] = []
    seen: Set[Tuple] = set()  # 去重
    counter = Counter(c.rank for c in hand_sorted)

    if not last_play:
        # 自由出牌：枚举所有可能
        return _enumerate_all(hand_sorted, counter, seen)

    # 必须压 last_play
    tar_pat, tar_main = identify_pattern(last_play)

    # 火箭：总是可出
    rockets = _find_rocket(hand_sorted)
    if rockets:
        _add_option(options, rockets, seen)

    # 炸弹：大于 last_play 的炸弹
    if tar_pat == Pattern.ROCKET:
        return options  # 只有火箭能压火箭

    if tar_pat == Pattern.BOMB:
        # 需要更大的炸弹
        for bomb in _find_bombs(hand_sorted, counter):
            _, bm = identify_pattern(bomb)
            if bm > tar_main:
                _add_option(options, bomb, seen)
        return options

    # 普通牌型：先找同牌型更大的组合
    _find_same_pattern_beats(hand_sorted, last_play, tar_pat, tar_main, options, seen, counter)

    # 炸弹也能压普通牌
    for bomb in _find_bombs(hand_sorted, counter):
        _add_option(options, bomb, seen)

    # 火箭也能压
    # (already added above)

    return options


def _add_option(options: List[List[Card]], cards: List[Card], seen: Set[Tuple]):
    key = tuple(sorted(c.rank.value for c in cards))
    if key not in seen:
        seen.add(key)
        options.append(sort_cards(cards))


def _find_rocket(hand: List[Card]) -> Optional[List[Card]]:
    """检查手牌中是否有火箭"""
    has_small = any(c.rank == Rank.SMALL_JOKER for c in hand)
    has_big = any(c.rank == Rank.BIG_JOKER for c in hand)
    if has_small and has_big:
        return [c for c in hand if c.rank in (Rank.SMALL_JOKER, Rank.BIG_JOKER)]
    return None


def _find_bombs(hand: List[Card], counter: Counter) -> List[List[Card]]:
    """找出所有炸弹"""
    bombs = []
    for rank, cnt in counter.items():
        if cnt == 4:
            bombs.append([c for c in hand if c.rank == rank])
    return bombs


def _find_same_pattern_beats(
    hand: List[Card],
    last_play: List[Card],
    tar_pat: Pattern,
    tar_main: int,
    options: List[List[Card]],
    seen: Set[Tuple],
    counter: Counter,
):
    """找同牌型且更大的组合"""
    if tar_pat == Pattern.SINGLE:
        _find_beating_singles(hand, tar_main, options, seen)
    elif tar_pat == Pattern.PAIR:
        _find_beating_pairs(hand, tar_main, options, seen, counter)
    elif tar_pat in (Pattern.TRIPLE, Pattern.TRIPLE_ONE, Pattern.TRIPLE_TWO):
        _find_beating_triples(hand, last_play, tar_pat, tar_main, options, seen, counter)
    elif tar_pat == Pattern.STRAIGHT:
        _find_beating_straights(hand, len(last_play), tar_main, options, seen)
    elif tar_pat == Pattern.STRAIGHT_PAIR:
        _find_beating_straight_pairs(hand, len(last_play), tar_main, options, seen, counter)
    elif tar_pat in (Pattern.PLANE, Pattern.PLANE_SINGLE, Pattern.PLANE_PAIR):
        _find_beating_planes(hand, last_play, tar_pat, tar_main, options, seen, counter)
    elif tar_pat in (Pattern.FOUR_TWO_SINGLE, Pattern.FOUR_TWO_PAIR):
        _find_beating_four_twos(hand, tar_pat, tar_main, options, seen, counter)


def _find_beating_singles(hand, tar_main, options, seen):
    for c in hand:
        if c.rank.value > tar_main:
            _add_option(options, [c], seen)


def _find_beating_pairs(hand, tar_main, options, seen, counter):
    for rank, cnt in counter.items():
        if cnt >= 2 and rank.value > tar_main:
            pair_cards = [c for c in hand if c.rank == rank][:2]
            _add_option(options, pair_cards, seen)


def _find_beating_triples(hand, last_play, tar_pat, tar_main, options, seen, counter):
    """三带X：找出更大的三带X组合"""
    kicker_count = len(last_play) - 3  # 带牌数量

    for rank, cnt in counter.items():
        if cnt >= 3 and rank.value > tar_main:
            triple_cards = [c for c in hand if c.rank == rank][:3]
            remaining = [c for c in hand if c.rank != rank]

            if kicker_count == 0:
                _add_option(options, triple_cards, seen)
            elif kicker_count == 1:
                # 三带一：任选一张其他牌
                for k in remaining:
                    _add_option(options, triple_cards + [k], seen)
            elif kicker_count == 2:
                # 三带二：需要一对
                kick_counter = Counter(c.rank for c in remaining)
                for kr, kc in kick_counter.items():
                    if kc >= 2:
                        kickers = [c for c in remaining if c.rank == kr][:2]
                        _add_option(options, triple_cards + kickers, seen)


def _find_beating_straights(hand, length, tar_main, options, seen):
    """找更大的顺子"""
    valid_ranks = [r for r in STRAIGHT_VALID_RANKS]
    hand_by_rank: dict = {}
    for c in hand:
        if c.rank.value in STRAIGHT_VALID_RANKS:
            hand_by_rank.setdefault(c.rank.value, []).append(c)

    for start in range(3, 15 - length + 2):  # 3 到 A-长度+1
        end = start + length
        if end - 1 <= tar_main:  # 不比目标大
            continue
        seg_ranks = list(range(start, end))
        if all(r in hand_by_rank for r in seg_ranks):
            # 每种取一张
            combo = [hand_by_rank[r][0] for r in seg_ranks]
            _add_option(options, combo, seen)


def _find_beating_straight_pairs(hand, length, tar_main, options, seen, counter):
    """找更大的连对"""
    pair_count = length // 2
    valid_ranks = sorted(
        [r for r, cnt in counter.items() if cnt >= 2 and r.value in STRAIGHT_VALID_RANKS],
        key=lambda r: r.value
    )

    for i in range(len(valid_ranks) - pair_count + 1):
        seg = valid_ranks[i:i + pair_count]
        if _is_consecutive_ranks(seg) and seg[-1].value > tar_main:
            combo = []
            for r in seg:
                combo.extend([c for c in hand if c.rank == r][:2])
            _add_option(options, combo, seen)


def _find_beating_planes(hand, last_play, tar_pat, tar_main, options, seen, counter):
    """找更大的飞机组合"""
    # 先确定目标飞机的连三数量和带牌数
    tar_counter = Counter(c.rank for c in last_play)
    tar_triples = sorted(
        [r for r, cnt in tar_counter.items() if cnt >= 3],
        key=lambda r: r.value
    )
    seg_len = len(tar_triples)
    kicker_per_triple = 0
    if tar_pat == Pattern.PLANE_SINGLE:
        kicker_per_triple = 1
    elif tar_pat == Pattern.PLANE_PAIR:
        kicker_per_triple = 2

    available_triples = sorted(
        [r for r, cnt in counter.items() if cnt >= 3 and r.value in STRAIGHT_VALID_RANKS],
        key=lambda r: r.value
    )

    for i in range(len(available_triples) - seg_len + 1):
        seg = available_triples[i:i + seg_len]
        if not _is_consecutive_ranks(seg):
            continue
        if seg[-1].value <= tar_main:
            continue

        # 构建飞机核心
        core = []
        for r in seg:
            core.extend([c for c in hand if c.rank == r][:3])

        remaining = [c for c in hand if c not in core]
        kicker_needed = seg_len * kicker_per_triple

        if kicker_needed == 0:
            _add_option(options, core, seen)
        elif kicker_per_triple == 1:
            # 任选 k 张牌作为带牌（限制组合数避免爆炸）
            max_combos = 50
            count = 0
            for kickers in combinations(remaining, kicker_needed):
                _add_option(options, core + list(kickers), seen)
                count += 1
                if count >= max_combos:
                    break
        elif kicker_per_triple == 2:
            # 需要 k 对
            rem_counter = Counter(c.rank for c in remaining)
            avail_pairs = [r for r, cnt in rem_counter.items() if cnt >= 2]
            if len(avail_pairs) >= seg_len:
                max_combos = 50
                count = 0
                for pk in combinations(avail_pairs, seg_len):
                    kickers = []
                    for r in pk:
                        kickers.extend([c for c in remaining if c.rank == r][:2])
                    _add_option(options, core + kickers, seen)
                    count += 1
                    if count >= max_combos:
                        break


def _find_beating_four_twos(hand, tar_pat, tar_main, options, seen, counter):
    """找更大的四带二组合"""
    kicker_is_pair = (tar_pat == Pattern.FOUR_TWO_PAIR)

    for rank, cnt in counter.items():
        if cnt >= 4 and rank.value > tar_main:
            four_cards = [c for c in hand if c.rank == rank][:4]
            remaining = [c for c in hand if c.rank != rank]

            if not kicker_is_pair:
                # 四带二单：任选2张
                for k in combinations(remaining, 2):
                    _add_option(options, four_cards + list(k), seen)
            else:
                # 四带二对：需要2对
                rem_counter = Counter(c.rank for c in remaining)
                pairs = [r for r, cnt in rem_counter.items() if cnt >= 2]
                for pk in combinations(pairs, 2):
                    kickers = []
                    for r in pk:
                        kickers.extend([c for c in remaining if c.rank == r][:2])
                    _add_option(options, four_cards + kickers, seen)


def _is_consecutive_ranks(ranks: List[Rank]) -> bool:
    if len(ranks) < 2:
        return len(ranks) == 1
    for i in range(1, len(ranks)):
        if ranks[i].value - ranks[i-1].value != 1:
            return False
    return True


def _enumerate_all(hand: List[Card], counter: Counter, seen: Set[Tuple]) -> List[List[Card]]:
    """枚举所有可能的出牌组合（自由出牌时用）"""
    options: List[List[Card]] = []

    ranks = sorted(set(c.rank for c in hand), key=lambda r: r.value)
    hand_sorted = hand  # already sorted by caller

    # 火箭
    rocket = _find_rocket(hand_sorted)
    if rocket:
        _add_option(options, rocket, seen)

    # 炸弹
    for bomb in _find_bombs(hand_sorted, counter):
        _add_option(options, bomb, seen)

    # 单张
    for c in hand_sorted:
        _add_option(options, [c], seen)

    # 对子
    for r, cnt in counter.items():
        if cnt >= 2:
            pair = [c for c in hand_sorted if c.rank == r][:2]
            _add_option(options, pair, seen)

    # 三张（不带）
    for r, cnt in counter.items():
        if cnt >= 3:
            triple = [c for c in hand_sorted if c.rank == r][:3]
            _add_option(options, triple, seen)
            # 三带一
            remaining = [c for c in hand_sorted if c.rank != r]
            for k in remaining:
                _add_option(options, triple + [k], seen)
            # 三带二
            rem_counter = Counter(c.rank for c in remaining)
            for kr, kc in rem_counter.items():
                if kc >= 2:
                    kickers = [c for c in remaining if c.rank == kr][:2]
                    _add_option(options, triple + kickers, seen)

    # 四带二
    for r, cnt in counter.items():
        if cnt >= 4:
            four = [c for c in hand_sorted if c.rank == r][:4]
            remaining = [c for c in hand_sorted if c.rank != r]
            # 四带二单
            for k in combinations(remaining, 2):
                _add_option(options, four + list(k), seen)
            # 四带二对
            rem_counter = Counter(c.rank for c in remaining)
            pair_ranks = [rr for rr, cc in rem_counter.items() if cc >= 2]
            for pk in combinations(pair_ranks, 2):
                kickers = []
                for rr in pk:
                    kickers.extend([c for c in remaining if c.rank == rr][:2])
                _add_option(options, four + kickers, seen)

    # 顺子
    _enumerate_straights_all(hand_sorted, counter, ranks, seen, options)

    # 连对
    _enumerate_straight_pairs_all(hand_sorted, counter, ranks, seen, options)

    # 飞机
    _enumerate_planes_all(hand_sorted, counter, ranks, seen, options)

    return options


def _enumerate_straights_all(hand, counter, ranks, seen, options):
    """枚举所有顺子"""
    valid_rank_values = [r.value for r in ranks if r.value in STRAIGHT_VALID_RANKS]
    for start_idx in range(len(valid_rank_values)):
        for end_idx in range(start_idx + 4, len(valid_rank_values)):
            seg = valid_rank_values[start_idx:end_idx + 1]
            if not _is_consecutive_values(seg):
                break
            if all(Rank(v) in counter for v in seg):
                combo = []
                for v in seg:
                    combo.append([c for c in hand if c.rank == Rank(v)][0])
                _add_option(options, combo, seen)


def _enumerate_straight_pairs_all(hand, counter, ranks, seen, options):
    """枚举所有连对（≥3连）"""
    valid_pair_ranks = sorted([
        r for r in ranks
        if r.value in STRAIGHT_VALID_RANKS and counter[r] >= 2
    ], key=lambda r: r.value)
    for start_idx in range(len(valid_pair_ranks)):
        for end_idx in range(start_idx + 2, len(valid_pair_ranks)):
            seg = valid_pair_ranks[start_idx:end_idx + 1]
            if not _is_consecutive_ranks(seg):
                break
            combo = []
            for r in seg:
                combo.extend([c for c in hand if c.rank == r][:2])
            _add_option(options, combo, seen)


def _enumerate_planes_all(hand, counter, ranks, seen, options):
    """枚举所有飞机组合"""
    valid_triple_ranks = sorted([
        r for r in ranks
        if r.value in STRAIGHT_VALID_RANKS and counter[r] >= 3
    ], key=lambda r: r.value)

    for seg_len in range(2, len(valid_triple_ranks) + 1):
        for start in range(len(valid_triple_ranks) - seg_len + 1):
            seg = valid_triple_ranks[start:start + seg_len]
            if not _is_consecutive_ranks(seg):
                continue
            core = []
            for r in seg:
                core.extend([c for c in hand if c.rank == r][:3])
            _add_option(options, core, seen)  # 飞机不带

            remaining = [c for c in hand if c not in core]
            # 飞机带单（限制组合数避免爆炸）
            max_combos = 50
            count = 0
            for kickers in combinations(remaining, seg_len):
                _add_option(options, core + list(kickers), seen)
                count += 1
                if count >= max_combos:
                    break

            # 飞机带双
            rem_counter = Counter(c.rank for c in remaining)
            pair_ranks = [r for r, cnt in rem_counter.items() if cnt >= 2]
            if len(pair_ranks) >= seg_len:
                count = 0
                for pk in combinations(pair_ranks, seg_len):
                    kickers = []
                    for r in pk:
                        kickers.extend([c for c in remaining if c.rank == r][:2])
                    _add_option(options, core + kickers, seen)
                    count += 1
                    if count >= max_combos:
                        break


def _is_consecutive_values(vals: List[int]) -> bool:
    for i in range(1, len(vals)):
        if vals[i] - vals[i-1] != 1:
            return False
    return True
