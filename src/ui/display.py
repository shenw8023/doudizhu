"""
TUI 牌面渲染器 — 用 rich 库在终端渲染扑克牌和游戏界面。

注意：当前版本中 tui.py 自行实现了渲染逻辑，此模块暂未使用。
保留以备将来需要 Layout-based 渲染时使用。
"""
from typing import List, Optional, Tuple
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.console import Console
from rich.align import Align
from rich.box import ROUNDED
from src.engine.cards import Card, Rank, SUIT_SYMBOLS, RANK_NAMES, sort_cards
from src.engine.patterns import identify_pattern, PATTERN_NAMES, Pattern

# 颜色方案
SUIT_COLORS = {
    "♠": "white",
    "♥": "red",
    "♣": "green",
    "♦": "yellow",
}
JOKER_COLORS = {
    Rank.SMALL_JOKER: "cyan",
    Rank.BIG_JOKER: "bright_magenta",
}

def _card_display_str(card: Card) -> str:
    """统一的牌面显示字符串，固定宽度（4字符）。"""
    if card.suit is None:
        # Joker: emoji 表情 + 2个空格凑到4字符视觉宽度
        return f"{RANK_NAMES[card.rank]}  "
    sym = SUIT_SYMBOLS.get(card.suit, "?")
    rn = RANK_NAMES[card.rank]
    if len(rn) == 1:
        # ♠ A (3 chars) → pad to 4
        return f"{sym} {rn} "
    else:
        # ♠10 (4 chars) → no padding needed
        return f"{sym}{rn} "


def _card_color(card: Card) -> str:
    """获取牌的颜色"""
    if card.suit is None:
        return JOKER_COLORS.get(card.rank, "white")
    sym = SUIT_SYMBOLS.get(card.suit, "")
    return SUIT_COLORS.get(sym, "white")


def _card_symbol(card: Card) -> str:
    """获取牌的花色符号"""
    if card.suit is None:
        return "  "
    return str(SUIT_SYMBOLS.get(card.suit, " "))


def _card_rank_name(card: Card) -> str:
    """获取牌的点数名称（对齐用）"""
    name = RANK_NAMES[card.rank]
    if len(name) == 1:
        return f" {name}"
    return name  # "10" 是两个字符


def render_card(card: Card, selected: bool = False) -> Text:
    """渲染单张牌为 rich Text（4行卡片）"""
    color = _card_color(card)
    sym = _card_symbol(card)
    rn_display = _card_display_str(card).strip()  # "♠ A" or "♠10" or "🃏"

    style = f"bold {color}" if not selected else f"bold {color} on grey30"

    lines = [
        f"{rn_display}   ",
        f"  {sym}  ",
        f"   {rn_display}",
    ]

    return Text("\n".join(lines), style=style)


def render_card_compact(card: Card, selected: bool = False) -> str:
    """渲染单张牌——紧凑单行模式"""
    return _card_display_str(card).rstrip()


def render_hand(hand: List[Card], selected_indices: List[int] = None) -> str:
    """
    渲染一手牌为带序号的文本表。
    选中的牌以高亮显示。
    返回 str（用于终端输出）。
    """
    if selected_indices is None:
        selected_indices = []

    lines = ["", "", ""]
    for i, card in enumerate(hand):
        sel = i in selected_indices
        card_str = _card_display_str(card)  # 固定4字符
        prefix = ">" if sel else " "
        idx_str = f"{i+1:<3}"

        header = f" {idx_str}{prefix} "
        if sel:
            lines[0] += f"\033[43;30m{header}\033[0m"
            lines[1] += f"\033[43;30m{card_str}\033[0m"
            lines[2] += f"\033[43;30m     \033[0m"
        else:
            lines[0] += f"{header}"
            lines[1] += f"{card_str}"
            lines[2] += f"     "

    return "\n".join(lines) + "\n"


def render_hand_rich(hand: List[Card], selected_indices: List[int] = None) -> Table:
    """
    用 rich Table 渲染一手牌。
    每列一张牌，选中的牌边框高亮。
    """
    if selected_indices is None:
        selected_indices = []

    table = Table(
        show_header=False,
        show_edge=False,
        show_lines=False,
        padding=(0, 1),
        box=None,
    )

    # 序号行
    idx_row: List[Text] = []
    card_row: List[Text] = []
    for i, card in enumerate(hand):
        color = _card_color(card)
        card_str = _card_display_str(card).rstrip()  # "♠ A" or "♠10"

        if i in selected_indices:
            # 选中：高亮
            idx_text = Text(f"[{i+1:^5}]", style="bold yellow on grey30")
            card_text = Text(f"{card_str}", style=f"bold {color} on grey30")
        else:
            idx_text = Text(f"[{i+1:^3}]", style=f"dim {color}")
            # 简洁卡片
            card_text = Text(f"{card_str}", style=f"bold {color}")

        idx_row.append(idx_text)
        card_row.append(card_text)

    table.add_row(*idx_row)
    table.add_row(*card_row)

    return table


def render_game_state(
    game_state,
    player_idx: int = 0,
    ai1_name: str = "AI-1",
    ai2_name: str = "AI-2",
) -> Layout:
    """
    渲染完整游戏界面。
    返回 rich Layout 对象。
    """
    layout = Layout()

    hands = game_state.player_hands
    landlord = game_state.landlord_idx

    # 计算对手索引
    opp1 = (player_idx + 1) % 3
    opp2 = (player_idx + 2) % 3

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=5),
    )

    # Header
    phase_text = "叫地主" if game_state.phase.value == "calling" else "出牌中"
    header = Panel(
        Align.center(
            Text(f"🂡  斗 地 主  🂡    |    {phase_text}",
                 style="bold yellow")
        ),
        box=ROUNDED,
        style="yellow",
    )
    layout["header"].update(header)

    # Body
    body = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 2),
    )

    # 对手2（上方）
    opp2_tag = "👑 地主" if opp2 == landlord else "🌾 农民"
    opp2_cards = _render_opponent(hands[opp2], opp2, ai1_name if opp2 == 1 else ai2_name, opp2_tag)
    body.add_row(opp2_cards)

    # 上一手牌
    last_play_info = _render_last_play(game_state)
    body.add_row(last_play_info)

    # 对手1
    opp1_tag = "👑 地主" if opp1 == landlord else "🌾 农民"
    opp1_cards = _render_opponent(hands[opp1], opp1, ai1_name if opp1 == 1 else ai2_name, opp1_tag)
    body.add_row(opp1_cards)

    layout["body"].update(
        Panel(body, box=ROUNDED, style="dim white", title="牌桌")
    )

    # Footer — 玩家手牌
    player_tag = "👑 地主" if player_idx == landlord else "🌾 农民"
    player_hand_table = render_hand_rich(
        sort_cards(hands[player_idx]),
        []
    )
    footer = Panel(
        player_hand_table,
        box=ROUNDED,
        style="bold green",
        title=f"你的手牌 ({len(hands[player_idx])}张) [{player_tag}]",
    )
    layout["footer"].update(footer)

    return layout


def _render_opponent(hand: List[Card], idx: int, name: str, tag: str) -> Panel:
    """渲染对手信息（隐藏手牌内容）"""
    n = len(hand)
    # 显示背面牌
    backs = "🂠 " * min(n, 20)
    if n > 20:
        backs += f"... (+{n-20})"

    text = Text(f"{backs}\n", style="dim")
    text.append(f"{name} ({n}张)", style="bold white")

    return Panel(
        Align.center(text),
        box=ROUNDED,
        style="dim blue",
        title=f"{tag}",
    )


def _render_last_play(game_state) -> Panel:
    """渲染上一手出牌信息"""
    if game_state.last_play is None:
        if game_state.last_player is not None:
            text = Text("新回合开始！自由出牌", style="bold green")
        else:
            text = Text("等待出牌...", style="dim")
    else:
        pat, _ = identify_pattern(game_state.last_play)
        pat_name = PATTERN_NAMES.get(pat, "?")
        cards_str = " ".join(
            str(c) for c in sort_cards(game_state.last_play)
        )
        player_name = f"玩家{game_state.last_player}"
        text = Text(f"上一手: {cards_str}", style="bold yellow")
        text.append(f"\n牌型: {pat_name}  |  由 {player_name} 出", style="dim")

    return Panel(
        Align.center(text),
        box=ROUNDED,
        style="yellow",
        title="当前牌局",
    )


def render_pattern_preview(hand: List[Card], selected: List[Card]) -> Tuple[Pattern, str, bool]:
    """
    预览选中牌的牌型。
    返回 (Pattern, 描述, is_valid)
    """
    if not selected:
        return Pattern.INVALID, "", False

    pat, main_val = identify_pattern(selected)
    pat_name = PATTERN_NAMES.get(pat, "无效")
    is_valid = pat != Pattern.INVALID

    cards_str = " ".join(str(c) for c in selected)
    desc = f"{pat_name}: {cards_str}"

    return pat, desc, is_valid
