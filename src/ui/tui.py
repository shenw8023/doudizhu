"""
主 TUI 交互循环。

玩家对抗两个 AI（蒙特卡洛 + 规则 AI）。
"""
import sys
import os
import time
from typing import List, Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.box import ROUNDED

from src.engine.cards import Card, Deck, sort_cards, Rank, RANK_NAMES, SUIT_SYMBOLS
from src.engine.rules import get_all_playable, can_beat
from src.engine.patterns import identify_pattern, Pattern, PATTERN_NAMES
from src.engine.game import Game, GameState, GamePhase
from src.ai.base import GameContext
from src.ai.rule_ai import RuleAI
from src.ai.mcts_ai import MCTSAI
from src.ai.random_ai import RandomAI

console = Console()


def clear_screen():
    """清屏"""
    console.clear()


def show_banner():
    """显示启动画面"""
    clear_screen()
    banner = """
    ╔═══════════════════════════════════╗
    ║          🂡  斗 地 主  🂡          ║
    ║        AI-Powered TUI Game        ║
    ║    玩家 vs AI农民 × 2              ║
    ╚═══════════════════════════════════╝
    """
    console.print(Panel(banner.strip(), style="bold yellow", box=ROUNDED))
    console.print()


def _card_inner(card: Card) -> str:
    """获取牌面核心显示: '♠ A', '♠10', 或 '🃏'"""
    if card.suit is None:
        return RANK_NAMES[card.rank]
    sym = SUIT_SYMBOLS.get(card.suit, "")
    rn = RANK_NAMES[card.rank]
    if len(rn) == 1:
        return f"{sym} {rn}"
    return f"{sym}{rn}"


def show_hand(hand: List[Card], selected: List[int]) -> None:
    """多行方框牌面 — 序号在上，框线包裹花色+数字"""
    CARDS_PER_ROW = 10
    CARD_W = 7       # ┌─────┐ 宽度（防重叠）

    console.print()
    for row_start in range(0, len(hand), CARDS_PER_ROW):
        row_cards = hand[row_start:row_start + CARDS_PER_ROW]

        idx_line = Text()
        top_line = Text()
        face_line = Text()
        bot_line = Text()

        for j, card in enumerate(row_cards):
            i = row_start + j
            sel = i in selected
            color = _get_color(card)
            style = "bold yellow on grey30" if sel else f"bold {color}"
            idx_style = style if sel else "dim"

            # 构建 5 字符内芯（花色+双空格+数字，消除重叠）
            if card.suit is None:
                inner = RANK_NAMES[card.rank]
                inner5 = f" {inner}  "
            else:
                sym = SUIT_SYMBOLS[card.suit]
                rn = RANK_NAMES[card.rank]
                inner5 = f"{sym}  {rn} " if len(rn) == 1 else f"{sym} {rn} "

            idx_line.append(f"{i+1:^{CARD_W+1}}", style=idx_style)
            top_line.append("┌─────┐ ", style=style)
            face_line.append(f"│{inner5}│ ", style=style)
            bot_line.append("└─────┘ ", style=style)

        console.print(idx_line)
        console.print(top_line)
        console.print(face_line)
        console.print(bot_line)
        console.print()  # 行间隔


def _get_color(card: Card) -> str:
    if card.rank in (Rank.SMALL_JOKER, Rank.BIG_JOKER):
        return "bold magenta" if card.rank == Rank.BIG_JOKER else "bold cyan"
    suit_colors = {"♠": "white", "♥": "red", "♣": "green", "♦": "yellow"}
    sym = SUIT_SYMBOLS.get(card.suit, " ")
    return suit_colors.get(sym, "white")


def show_game_info(game: Game, ai1_name: str, ai2_name: str, player_idx: int = 0):
    """显示游戏状态信息"""
    st = game.state
    opp1 = (player_idx + 1) % 3
    opp2 = (player_idx + 2) % 3

    console.print(f"[bold cyan]━━━ 第 {len(st.history)} 手 ━━━[/bold cyan]")

    # 对手信息
    for idx, name in [(opp1, ai1_name), (opp2, ai2_name)]:
        tag = "👑地主" if idx == st.landlord_idx else "🌾农民"
        n = len(st.player_hands[idx])
        bar = "█" * min(n, 20)
        console.print(f"  {tag} {name}: [dim]{bar}[/dim] ({n}张)")

    # 当前牌局
    if st.last_play:
        pat, _ = identify_pattern(st.last_play)
        pat_name = PATTERN_NAMES.get(pat, "?")
        cards_str = " ".join(str(c) for c in sort_cards(st.last_play))
        lp_name = f"玩家{st.last_player}"
        console.print(f"\n[yellow]上一手: {cards_str}  [{pat_name}]  (由 {lp_name})[/yellow]")
    elif st.last_player is not None:
        console.print(f"\n[bold green]新回合！自由出牌[/bold green]")
    else:
        console.print(f"\n[dim]等待出牌...[/dim]")

    console.print()


def _show_hand_counts(game: Game, ai1_name: str, ai2_name: str, player_idx: int = 0):
    """只显示手牌数变化（精简版，用于AI回合后的增量更新）"""
    st = game.state
    opp1 = (player_idx + 1) % 3
    opp2 = (player_idx + 2) % 3
    parts = []
    for idx, name in [(opp1, ai1_name), (opp2, ai2_name)]:
        tag = "👑" if idx == st.landlord_idx else "🌾"
        n = len(st.player_hands[idx])
        parts.append(f"{tag}{name}:{n}张")
    console.print(f"  [dim]{'  |  '.join(parts)}[/dim]")


def show_pattern_info(selected_cards: List[Card]) -> None:
    """显示选中牌的牌型"""
    if not selected_cards:
        console.print("[dim]未选牌[/dim]")
        return

    pat, _ = identify_pattern(selected_cards)
    pat_name = PATTERN_NAMES.get(pat, "无效牌型")
    cards_str = " ".join(str(c) for c in sorted(selected_cards, key=lambda c: c.rank.value))

    if pat == Pattern.INVALID:
        console.print(f"[red]❌ {pat_name}: {cards_str}[/red]")
    else:
        console.print(f"[green]✓ {pat_name}: {cards_str}[/green]")


def run_calling_phase(game: Game, player_idx: int) -> bool:
    """叫地主阶段。返回 True 表示阶段完成且玩家继续。"""
    st = game.state
    current = st.current_caller

    while st.phase == GamePhase.CALLING:
        # 每次循环重新读取手牌（全不叫重新发牌后引用会变）
        hand = st.player_hands[player_idx]

        if current == player_idx:
            # 玩家叫地主
            console.clear()
            console.print("[bold yellow]═══ 叫地主 ═══[/bold yellow]")
            console.print()
            show_hand(hand, [])

            scores_shown = []
            for i, s in enumerate(st.call_scores):
                if s == -1:
                    scores_shown.append("_")
                elif s == 0:
                    scores_shown.append("不叫")
                else:
                    scores_shown.append(f"{s}分")
            console.print(f"  已叫分: {' | '.join(scores_shown)}")
            console.print()
            console.print("  [0] 不叫    [1] 1分    [2] 2分    [3] 3分")

            choice = Prompt.ask("  你的选择", choices=["0", "1", "2", "3"], default="1")
            score = int(choice)
            done = game.call_landlord(player_idx, score)

            if done and st.phase == GamePhase.PLAYING:
                return True
            if done:
                # 重新发牌
                console.print("[yellow]三人都不叫，重新发牌...[/yellow]")
                time.sleep(1)
                continue  # 回到 while 循环顶部，重新读取 hand

            current = st.current_caller
        else:
            # AI 叫地主
            time.sleep(0.5)
            # AI 简单策略：手牌好就叫
            ai_hand = st.player_hands[current]
            ai_score = 0
            # 数大牌
            big_cards = sum(1 for c in ai_hand if c.rank.value >= Rank.TWO.value)
            if big_cards >= 4:
                ai_score = 3
            elif big_cards >= 3:
                ai_score = 2
            elif big_cards >= 2:
                ai_score = 1

            name = f"AI-{current}"
            if ai_score > 0:
                console.print(f"  {name} 叫了 [bold]{ai_score}分[/bold]!")
            else:
                console.print(f"  {name} 不叫")
            time.sleep(0.5)

            done = game.call_landlord(current, ai_score)
            if done and st.phase == GamePhase.CALLING:
                # 重新发牌
                continue
            if done:
                return True
            current = st.current_caller

    return True


def _parse_indices(choice: str, max_idx: int) -> List[int]:
    """解析输入为牌序号列表。支持: '1 3 5', '1,3,5', '1-5'"""
    s = choice.replace(',', ' ').replace('，', ' ')  # 逗号→空格
    parts = s.split()
    result = []
    for part in parts:
        if '-' in part and part.count('-') == 1:
            try:
                a, b = part.split('-', 1)
                start, end = int(a), int(b)
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    idx = i - 1
                    if 0 <= idx < max_idx and idx not in result:
                        result.append(idx)
            except ValueError:
                continue
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < max_idx and idx not in result:
                    result.append(idx)
            except ValueError:
                continue
    return result


def process_player_turn(game: Game, player_idx: int) -> bool:
    """处理玩家回合。返回 True 表示成功出牌/过牌。"""
    st = game.state
    hand = sort_cards(st.player_hands[player_idx])
    last_play = st.last_play

    selected: List[int] = []

    while True:
        clear_screen()
        show_game_info(game, "AI-1", "AI-2", player_idx)
        show_hand(hand, selected)
        show_pattern_info([hand[i] for i in selected])

        # 提示
        if last_play is None:
            prompt_text = "[选牌] 1-17 (可多选 如 1 3 5 或 1-5) [出牌] Enter [退出] Q"
        else:
            prompt_text = "[选牌] 1-17 (可多选 如 1 3 5 或 1-5) [出牌] Enter [过牌] P [退出] Q"

        console.print(f"[dim]{prompt_text}[/dim]")

        choice = Prompt.ask(">", default="")

        if choice.upper() == "Q":
            return False
        elif choice.upper() == "P":
            if last_play is not None:
                if game.play(player_idx, None):
                    return True
                else:
                    console.print("[red]现在不能过牌！[/red]")
                    time.sleep(0.8)
            else:
                console.print("[red]自由出牌不能过牌！[/red]")
                time.sleep(0.8)
        elif choice == "":
            # 确认出牌
            if not selected:
                console.print("[red]请先选牌！[/red]")
                time.sleep(0.8)
                continue

            play_cards = [hand[i] for i in selected]
            pat, _ = identify_pattern(play_cards)
            if pat == Pattern.INVALID:
                console.print("[red]无效牌型！请重新选牌[/red]")
                selected.clear()
                time.sleep(1.2)
                continue

            if not can_beat(play_cards, last_play):
                pat_name = PATTERN_NAMES.get(pat, "?")
                if last_play:
                    lp_pat, _ = identify_pattern(last_play)
                    lp_name = PATTERN_NAMES.get(lp_pat, "?")
                    console.print(f"[red]{pat_name} 压不过上家的 {lp_name}！请重新选牌[/red]")
                else:
                    console.print("[red]这手牌打不出去！请重新选牌[/red]")
                selected.clear()
                time.sleep(1.5)
                continue

            if game.play(player_idx, play_cards):
                game.remove_cards(player_idx, play_cards)
                return True
            else:
                console.print("[red]出牌失败！[/red]")
                time.sleep(0.8)
        else:
            # 选牌/取消选牌 — 支持多张: "1 3 5", "1,3,5", "1-5"
            indices = _parse_indices(choice, len(hand))
            if not indices:
                console.print(f"[red]无效输入！请输入牌序号，如 1 3 5 或 1-5（范围 1-{len(hand)}）[/red]")
                time.sleep(0.8)
                continue
            for idx in indices:
                if idx in selected:
                    selected.remove(idx)
                else:
                    selected.append(idx)
            selected.sort()

    return True


def run_ai_turn(game: Game, player_idx: int, ai: object, ai1_name: str = "AI-1", ai2_name: str = "AI-2", human_idx: int = 0) -> None:
    """AI 回合"""
    st = game.state
    hand = sort_cards(st.player_hands[player_idx])

    ctx = GameContext(
        position=game.get_player_role(player_idx),
        players_hand_count=[len(h) for h in st.player_hands],
        history=st.history,
        bottom_cards=st.bottom_cards,
        landlord_idx=st.landlord_idx,
        my_idx=player_idx,
        pass_count=st.pass_count,
    )

    # 短延迟模拟思考
    time.sleep(0.3)

    decision = ai.decide(hand, st.last_play, ctx)

    if decision is None:
        game.play(player_idx, None)
        console.print(f"  {ai.name} 过牌")
    else:
        game.play(player_idx, decision)
        game.remove_cards(player_idx, decision)
        pat, _ = identify_pattern(decision)
        pat_name = PATTERN_NAMES.get(pat, "?")
        cards_str = " ".join(str(c) for c in sort_cards(decision))
        console.print(f"  {ai.name} 出牌: {cards_str}  [{pat_name}]")

    # 简洁手牌变化提示，避免连续AI回合时手牌数"跳变"
    if not game.is_game_over():
        _show_hand_counts(game, ai1_name, ai2_name, human_idx)

    time.sleep(1.2)  # 留足够时间看清本轮AI出牌


def show_result(game: Game, player_idx: int) -> None:
    """显示游戏结果"""
    st = game.state
    won = (st.winner_role.value == game.get_player_role(player_idx))

    clear_screen()
    if won:
        msg = "🎉  你 赢 了！ 🎉"
        style = "bold green"
    else:
        msg = "😞  你 输 了  😞"
        style = "bold red"

    console.print(Panel(
        Align.center(Text(msg, style=style)),
        box=ROUNDED,
        style=style,
    ))

    console.print()
    console.print(f"  身份: {'👑 地主' if player_idx == st.landlord_idx else '🌾 农民'}")
    console.print(f"  回合数: {len([r for r in st.history if r.action == 'play'])}")
    for i in range(3):
        if i == player_idx:
            continue
        name = f"AI-{i}" if i != player_idx else "你"
        remaining = len(st.player_hands[i])
        console.print(f"  {name} 剩余: {remaining}张")


def main():
    """主入口"""
    try:
        # 初始化
        game = Game()
        player_idx = 0

        # AI 设置（支持 --seed 参数）
        seed_env = os.environ.get("DOUDIZHU_SEED")
        seed = int(seed_env) if seed_env else 42
        mcts_sims_env = os.environ.get("DOUDIZHU_MCTS_SIMS")
        mcts_sims = int(mcts_sims_env) if mcts_sims_env else 100
        mcts_ai = MCTSAI(num_simulations=mcts_sims, seed=seed)
        rule_ai = RuleAI()
        # 两个AI，一个MCTS一个规则（交替用）
        ai_players = {1: mcts_ai, 2: rule_ai}

        show_banner()
        console.print("按 Enter 开始新游戏...")
        input()

        while True:
            # 开始新游戏
            game.start()
            clear_screen()
            console.print("[yellow]发牌中...[/yellow]")
            time.sleep(0.5)

            # 叫地主
            if not run_calling_phase(game, player_idx):
                break

            # 确定身份
            role = game.get_player_role(player_idx)
            clear_screen()
            if role == "landlord":
                console.print("[bold yellow]你是 👑 地主！[/bold yellow]")
                console.print(f"底牌: {' '.join(str(c) for c in game.state.bottom_cards)}")
            else:
                console.print("[bold green]你是 🌾 农民！[/bold green]")
            console.print()
            console.print("按 Enter 开始出牌...")
            input()

            # 出牌循环
            playing = True
            while playing and not game.is_game_over():
                current = game.state.current_player

                if current == player_idx:
                    # 玩家回合
                    playing = process_player_turn(game, player_idx)
                else:
                    # AI 回合
                    run_ai_turn(game, current, ai_players[current])

            if not playing:
                break

            # 游戏结束
            show_result(game, player_idx)

            console.print()
            again = Prompt.ask("再来一局? [Y/n]", default="Y")
            if again.upper() != "Y" and again != "":
                break

        console.print("\n[dim]再见！[/dim]")

    except KeyboardInterrupt:
        console.print("\n[dim]已退出[/dim]")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
