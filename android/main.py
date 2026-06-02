"""
斗地主 Android App — Kivy UI 入口。
复用 src/engine 和 src/ai 的游戏逻辑。
"""
import os
import sys
import time
from typing import List, Optional, Set

# 确保 src 在路径中（兼容桌面测试和 Android 打包）
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# 桌面测试：APP_DIR=android/，ROOT_DIR=项目根
# Android 打包：APP_DIR=项目根/android/ 或 项目根/
ROOT_DIR = os.path.dirname(APP_DIR)
if os.path.exists(os.path.join(ROOT_DIR, 'src')):
    sys.path.insert(0, ROOT_DIR)
elif os.path.exists(os.path.join(APP_DIR, 'src')):
    sys.path.insert(0, APP_DIR)
else:
    # Android 打包后 src 在同一级
    sys.path.insert(0, APP_DIR)

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp

from src.engine.cards import Card, Rank, Suit, sort_cards, SUIT_SYMBOLS, RANK_NAMES
from src.engine.patterns import identify_pattern, Pattern, PATTERN_NAMES
from src.engine.rules import can_beat, get_all_playable
from src.engine.game import Game, GamePhase
from src.ai.base import GameContext
from src.ai.mcts_ai import MCTSAI
from src.ai.rule_ai import RuleAI

# ========== 颜色定义 ==========
SUIT_COLORS = {
    '♠': [1, 1, 1, 1],       # 白色
    '♥': [1, 0.2, 0.2, 1],   # 红色
    '♣': [0.3, 1, 0.3, 1],   # 绿色
    '♦': [1, 1, 0.2, 1],     # 黄色
}
JOKER_COLORS = {
    Rank.SMALL_JOKER: [0, 1, 1, 1],      # 青色
    Rank.BIG_JOKER: [1, 0.3, 1, 1],      # 洋红
}
BG_COLOR = [0.12, 0.12, 0.15, 1]
CARD_BG = [0.2, 0.2, 0.25, 1]
CARD_SELECTED_BG = [0.9, 0.8, 0.2, 1]
CARD_SELECTED_TEXT = [0.1, 0.1, 0.1, 1]


def card_text(card: Card) -> str:
    """获取牌面文字"""
    if card.suit is None:
        return RANK_NAMES[card.rank]
    sym = SUIT_SYMBOLS[card.suit]
    rn = RANK_NAMES[card.rank]
    return f"{sym}{rn}"


def card_color(card: Card) -> list:
    """获取牌面颜色"""
    if card.rank in (Rank.SMALL_JOKER, Rank.BIG_JOKER):
        return JOKER_COLORS.get(card.rank, [1, 1, 1, 1])
    if card.suit is None:
        return [1, 1, 1, 1]
    sym = SUIT_SYMBOLS.get(card.suit, '')
    return SUIT_COLORS.get(sym, [1, 1, 1, 1])


# ========== 牌面按钮 ==========
class CardButton(Button):
    """单张牌的按钮"""
    def __init__(self, card: Card, index: int, on_tap_callback, **kwargs):
        super().__init__(**kwargs)
        self.card = card
        self.index = index
        self.on_tap_callback = on_tap_callback
        self.is_selected = False

        self.text = card_text(card)
        self.font_size = sp(18)
        self.bold = True
        self.size_hint = (None, None)
        self.size = (dp(55), dp(75))
        self.background_color = CARD_BG
        self.color = card_color(card)
        self.background_normal = ''
        self.border = (2, 2, 2, 2)

    def on_press(self):
        self.is_selected = not self.is_selected
        if self.is_selected:
            self.background_color = CARD_SELECTED_BG
            self.color = CARD_SELECTED_TEXT
        else:
            self.background_color = CARD_BG
            self.color = card_color(self.card)
        self.on_tap_callback(self.index, self.is_selected)


# ========== 游戏主界面 ==========
class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game = Game()
        self.player_idx = 0
        self.mcts_ai = MCTSAI(num_simulations=50, seed=None)
        self.rule_ai = RuleAI()
        self.ai_players = {1: self.mcts_ai, 2: self.rule_ai}
        self.selected_indices: Set[int] = set()
        self.card_buttons: List[CardButton] = []
        self.is_ai_turn = False

        self._build_ui()
        self._start_new_game()

    def _build_ui(self):
        """构建界面布局"""
        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))
        root.canvas.before.clear()
        from kivy.graphics import Color, Rectangle
        with root.canvas.before:
            Color(*BG_COLOR)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        # ---- 顶部：对手信息 ----
        self.opp_label = Label(
            text='', font_size=sp(14), size_hint_y=None, height=dp(50),
            halign='left', valign='middle', color=[0.8, 0.8, 0.8, 1]
        )
        self.opp_label.bind(size=self.opp_label.setter('text_size'))
        root.add_widget(self.opp_label)

        # ---- 中部：上一手牌 + 状态 ----
        self.status_label = Label(
            text='', font_size=sp(16), size_hint_y=None, height=dp(60),
            halign='center', valign='middle', color=[1, 1, 0.6, 1],
            bold=True
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        root.add_widget(self.status_label)

        # ---- 中部：牌型提示 ----
        self.pattern_label = Label(
            text='', font_size=sp(13), size_hint_y=None, height=dp(30),
            halign='center', valign='middle', color=[0.6, 1, 0.6, 1]
        )
        self.pattern_label.bind(size=self.pattern_label.setter('text_size'))
        root.add_widget(self.pattern_label)

        # ---- 牌桌区域（对手出牌显示） ----
        self.table_label = Label(
            text='', font_size=sp(15), size_hint_y=None, height=dp(50),
            halign='center', valign='middle', color=[0.9, 0.9, 0.5, 1]
        )
        self.table_label.bind(size=self.table_label.setter('text_size'))
        root.add_widget(self.table_label)

        # ---- 手牌区域（可横向滚动） ----
        scroll = ScrollView(
            do_scroll_x=True, do_scroll_y=False,
            size_hint_y=None, height=dp(90),
            bar_color=[0.5, 0.5, 0.5, 0.5],
            scroll_type=['bars', 'content'],
        )
        self.hand_layout = GridLayout(
            rows=1, size_hint_x=None, spacing=dp(4),
            padding=[dp(4), dp(4)],
        )
        self.hand_layout.bind(minimum_width=self.hand_layout.setter('width'))
        scroll.add_widget(self.hand_layout)
        root.add_widget(scroll)

        # ---- 底部按钮栏 ----
        btn_bar = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(50),
            spacing=dp(8), padding=[dp(4), dp(4)],
        )

        self.play_btn = Button(
            text='出 牌', font_size=sp(16), bold=True,
            background_color=[0.2, 0.7, 0.3, 1],
            background_normal='',
        )
        self.play_btn.bind(on_press=self._on_play)

        self.pass_btn = Button(
            text='过 牌', font_size=sp(16), bold=True,
            background_color=[0.5, 0.5, 0.5, 1],
            background_normal='',
        )
        self.pass_btn.bind(on_press=self._on_pass)

        self.hint_btn = Button(
            text='提示', font_size=sp(14),
            background_color=[0.3, 0.4, 0.6, 1],
            background_normal='',
        )
        self.hint_btn.bind(on_press=self._on_hint)

        btn_bar.add_widget(self.pass_btn)
        btn_bar.add_widget(self.hint_btn)
        btn_bar.add_widget(self.play_btn)
        root.add_widget(btn_bar)

        self.add_widget(root)
        self._root = root

    def _update_bg(self, instance, value):
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def _start_new_game(self):
        """开始新游戏"""
        self.game.start()
        self.selected_indices.clear()
        self._update_all()

        # 叫地主
        self._run_calling_phase()

    def _run_calling_phase(self):
        """叫地主阶段"""
        st = self.game.state
        if st.phase != GamePhase.CALLING:
            return

        current = st.current_caller
        if current == self.player_idx:
            self._show_call_dialog()
        else:
            # AI 叫地主
            Clock.schedule_once(lambda dt: self._ai_call(current), 0.5)

    def _show_call_dialog(self):
        """显示叫地主对话框"""
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))

        st = self.game.state
        scores = []
        for s in st.call_scores:
            if s == -1:
                scores.append('_')
            elif s == 0:
                scores.append('不叫')
            else:
                scores.append(f'{s}分')

        content.add_widget(Label(
            text=f'已叫分: {" | ".join(scores)}',
            font_size=sp(14), color=[0.8, 0.8, 0.8, 1]
        ))

        btn_grid = GridLayout(cols=4, spacing=dp(8), size_hint_y=None, height=dp(50))
        for score in range(4):
            text = '不叫' if score == 0 else f'{score}分'
            btn = Button(text=text, font_size=sp(14))
            btn.score = score
            btn.bind(on_press=lambda b: self._on_call(b.score))
            btn_grid.add_widget(btn)
        content.add_widget(btn_grid)

        self._call_popup = Popup(
            title='叫地主', content=content,
            size_hint=(0.8, 0.4), auto_dismiss=False,
        )
        self._call_popup.open()

    def _on_call(self, score):
        """玩家叫地主"""
        if hasattr(self, '_call_popup'):
            self._call_popup.dismiss()
        done = self.game.call_landlord(self.player_idx, score)
        st = self.game.state

        if done and st.phase == GamePhase.PLAYING:
            self._update_all()
            if st.current_player != self.player_idx:
                Clock.schedule_once(lambda dt: self._run_ai_turn(), 0.5)
        elif done and st.phase == GamePhase.CALLING:
            # 全不叫，重新发牌
            self.game.start()
            self._update_all()
            self._run_calling_phase()
        else:
            # 继续叫地主
            self._run_calling_phase()

    def _ai_call(self, ai_idx):
        """AI 叫地主"""
        st = self.game.state
        ai_hand = st.player_hands[ai_idx]
        big_cards = sum(1 for c in ai_hand if c.rank.value >= Rank.TWO.value)
        ai_score = 0
        if big_cards >= 4:
            ai_score = 3
        elif big_cards >= 3:
            ai_score = 2
        elif big_cards >= 2:
            ai_score = 1

        name = f'AI-{ai_idx}'
        self._show_message(f'{name} {"叫了" + str(ai_score) + "分" if ai_score > 0 else "不叫"}')

        done = self.game.call_landlord(ai_idx, ai_score)
        if done and st.phase == GamePhase.PLAYING:
            self._update_all()
            if st.current_player != self.player_idx:
                Clock.schedule_once(lambda dt: self._run_ai_turn(), 0.8)
        elif done and st.phase == GamePhase.CALLING:
            self.game.start()
            self._update_all()
            Clock.schedule_once(lambda dt: self._run_calling_phase(), 0.5)
        else:
            Clock.schedule_once(lambda dt: self._run_calling_phase(), 0.5)

    def _update_all(self):
        """刷新整个界面"""
        self._update_opponents()
        self._update_hand()
        self._update_status()
        self._update_buttons()

    def _update_opponents(self):
        """更新对手信息"""
        st = self.game.state
        opp1 = (self.player_idx + 1) % 3
        opp2 = (self.player_idx + 2) % 3

        lines = []
        for idx, name in [(opp1, 'AI-1'), (opp2, 'AI-2')]:
            tag = '👑地主' if idx == st.landlord_idx else '🌾农民'
            n = len(st.player_hands[idx])
            bar = '█' * min(n, 20)
            lines.append(f'{tag} {name}: {bar} ({n}张)')

        role = '👑地主' if self.player_idx == st.landlord_idx else '🌾农民'
        n = len(st.player_hands[self.player_idx])
        lines.append(f'你({role}): {n}张')

        self.opp_label.text = '\n'.join(lines)

    def _update_hand(self):
        """更新手牌显示"""
        self.hand_layout.clear_widgets()
        self.card_buttons.clear()
        self.selected_indices.clear()

        st = self.game.state
        hand = sort_cards(st.player_hands[self.player_idx])

        for i, card in enumerate(hand):
            btn = CardButton(card, i, self._on_card_tap)
            self.card_buttons.append(btn)
            self.hand_layout.add_widget(btn)

    def _update_status(self):
        """更新状态信息"""
        st = self.game.state

        if st.phase == GamePhase.CALLING:
            self.status_label.text = '叫地主阶段...'
            self.table_label.text = ''
            return

        if st.phase == GamePhase.GAME_OVER:
            won = (st.winner_role and
                   st.winner_role.value == self.game.get_player_role(self.player_idx))
            self.status_label.text = '🎉 你赢了！' if won else '😞 你输了'
            self.table_label.text = f'共 {len(st.history)} 手'
            return

        if st.current_player == self.player_idx:
            if st.last_play is None:
                self.status_label.text = '[ 你的回合 — 自由出牌 ]'
            else:
                self.status_label.text = '[ 你的回合 — 需要压牌 ]'
        else:
            self.status_label.text = f'AI-{st.current_player} 思考中...'

        if st.last_play:
            pat, _ = identify_pattern(st.last_play)
            pat_name = PATTERN_NAMES.get(pat, '?')
            cards_str = ' '.join(card_text(c) for c in sort_cards(st.last_play))
            lp_name = f'玩家{st.last_player}' if st.last_player is not None else '?'
            self.table_label.text = f'上一手: {cards_str}  [{pat_name}]  ({lp_name})'
        elif st.last_player is not None:
            self.table_label.text = '新回合 — 自由出牌'
        else:
            self.table_label.text = ''

    def _update_buttons(self):
        """更新按钮状态"""
        st = self.game.state
        is_my_turn = (st.current_player == self.player_idx and
                      st.phase == GamePhase.PLAYING)
        self.play_btn.disabled = not is_my_turn
        self.pass_btn.disabled = not is_my_turn or st.last_play is None
        self.hint_btn.disabled = not is_my_turn

    def _on_card_tap(self, index, is_selected):
        """牌被点击"""
        if is_selected:
            self.selected_indices.add(index)
        else:
            self.selected_indices.discard(index)
        self._update_pattern_preview()

    def _update_pattern_preview(self):
        """更新选中牌的牌型提示"""
        if not self.selected_indices:
            self.pattern_label.text = ''
            return

        st = self.game.state
        hand = sort_cards(st.player_hands[self.player_idx])
        selected_cards = [hand[i] for i in sorted(self.selected_indices)
                          if i < len(hand)]

        if not selected_cards:
            self.pattern_label.text = ''
            return

        pat, _ = identify_pattern(selected_cards)
        pat_name = PATTERN_NAMES.get(pat, '无效牌型')
        cards_str = ' '.join(card_text(c) for c in selected_cards)

        if pat == Pattern.INVALID:
            self.pattern_label.text = f'❌ {pat_name}: {cards_str}'
            self.pattern_label.color = [1, 0.3, 0.3, 1]
        else:
            self.pattern_label.text = f'✓ {pat_name}: {cards_str}'
            self.pattern_label.color = [0.3, 1, 0.3, 1]

    def _on_play(self, instance):
        """出牌按钮"""
        if not self.selected_indices:
            self._show_message('请先选牌')
            return

        st = self.game.state
        hand = sort_cards(st.player_hands[self.player_idx])
        selected_cards = [hand[i] for i in sorted(self.selected_indices)
                          if i < len(hand)]

        pat, _ = identify_pattern(selected_cards)
        if pat == Pattern.INVALID:
            self._show_message('无效牌型')
            self._clear_selection()
            return

        if not can_beat(selected_cards, st.last_play):
            pat_name = PATTERN_NAMES.get(pat, '?')
            self._show_message(f'{pat_name} 压不过上家')
            self._clear_selection()
            return

        if self.game.play(self.player_idx, selected_cards):
            self.game.remove_cards(self.player_idx, selected_cards)
            self._update_all()

            if self.game.is_game_over():
                return

            # AI 回合
            Clock.schedule_once(lambda dt: self._run_ai_turn(), 0.8)

    def _on_pass(self, instance):
        """过牌按钮"""
        st = self.game.state
        if st.last_play is None:
            self._show_message('自由出牌不能过牌')
            return

        if self.game.play(self.player_idx, None):
            self._clear_selection()
            self._update_all()
            Clock.schedule_once(lambda dt: self._run_ai_turn(), 0.8)

    def _on_hint(self, instance):
        """提示按钮 — 选中第一组可出的牌"""
        st = self.game.state
        hand = sort_cards(st.player_hands[self.player_idx])
        options = get_all_playable(hand, st.last_play)

        if not options:
            self._show_message('没有可出的牌')
            return

        # 选第一个选项
        hint_cards = options[0]
        self.selected_indices.clear()
        for i, card in enumerate(hand):
            if card in hint_cards:
                self.selected_indices.add(i)

        # 更新按钮高亮
        for btn in self.card_buttons:
            btn.is_selected = btn.index in self.selected_indices
            if btn.is_selected:
                btn.background_color = CARD_SELECTED_BG
                btn.color = CARD_SELECTED_TEXT
            else:
                btn.background_color = CARD_BG
                btn.color = card_color(btn.card)

        self._update_pattern_preview()

    def _clear_selection(self):
        """清除选中状态"""
        self.selected_indices.clear()
        for btn in self.card_buttons:
            btn.is_selected = False
            btn.background_color = CARD_BG
            btn.color = card_color(btn.card)
        self.pattern_label.text = ''

    def _run_ai_turn(self):
        """执行 AI 回合"""
        st = self.game.state
        if self.game.is_game_over() or st.phase != GamePhase.PLAYING:
            return

        current = st.current_player
        if current == self.player_idx:
            self._update_all()
            return

        self.is_ai_turn = True
        hand = sort_cards(st.player_hands[current])
        ai = self.ai_players[current]

        ctx = GameContext(
            position=self.game.get_player_role(current),
            players_hand_count=[len(h) for h in st.player_hands],
            history=st.history,
            bottom_cards=st.bottom_cards,
            landlord_idx=st.landlord_idx,
            my_idx=current,
            pass_count=st.pass_count,
        )

        decision = ai.decide(hand, st.last_play, ctx)

        if decision is None:
            self.game.play(current, None)
            self._show_message(f'AI-{current} 过牌')
        else:
            self.game.play(current, decision)
            self.game.remove_cards(current, decision)
            pat, _ = identify_pattern(decision)
            pat_name = PATTERN_NAMES.get(pat, '?')
            cards_str = ' '.join(card_text(c) for c in sort_cards(decision))
            self._show_message(f'AI-{current}: {cards_str} [{pat_name}]')

        self._update_all()

        if self.game.is_game_over():
            return

        # 继续下一个 AI 回合
        if st.current_player != self.player_idx:
            Clock.schedule_once(lambda dt: self._run_ai_turn(), 1.0)
        else:
            self.is_ai_turn = False

    def _show_message(self, msg, duration=2.0):
        """显示临时消息"""
        self.status_label.text = msg
        Clock.schedule_once(lambda dt: self._update_status(), duration)

    def restart_game(self):
        """重新开始"""
        self.game = Game()
        self.selected_indices.clear()
        self._start_new_game()


# ========== 主应用 ==========
class DoudizhuApp(App):
    title = '斗地主'

    def build(self):
        # 设置窗口大小（桌面测试用，手机上自动全屏）
        Window.size = (400, 700)
        Window.clearcolor = BG_COLOR

        sm = ScreenManager()
        self.game_screen = GameScreen(name='game')
        sm.add_widget(self.game_screen)
        return sm

    def on_start(self):
        pass


if __name__ == '__main__':
    DoudizhuApp().run()
