"""
逃跑模式策略。

检测到战斗后按 ESC 键逃跑，并自动查找"是"确认按钮点击。
"""
import time
import logging

from config import CONFIG
from src.events import BattleDetectedEvent
from src.state import BotState
from src.strategies.base import ActionStrategy
from src.input import press_once, click_at
from src.vision import Template, best_yes_score_and_loc
from src.window import capture_window_bgr
from src.utils import log_audit
from typing import List


class EscapeStrategy(ActionStrategy):
    """ 逃跑策略：进入战斗后自动执行 按ESC -> 找确认按钮 -> 点击 的逃跑流程 """

    def __init__(self, state: BotState, templates: List[Template]) -> None:
        """ 初始化逃跑策略，加载识别所需的模板 """

        self.state = state
        self.templates = templates

    def on_battle_detected(self, event: BattleDetectedEvent) -> None:
        """ 战斗检测回调：触发逃跑动作逻辑 """

        if not self.state.can_trigger(CONFIG.trigger_cooldown_sec):
            return

        self._execute_escape(event)

    def _execute_escape(self, event: BattleDetectedEvent) -> None:
        """ 私有方法：执行具体的按键模拟和按钮匹配逻辑 """

        hwnd = event.hwnd
        width = event.width
        height = event.height
        scale = event.scale

        # 按下 ESC 键
        press_once(hwnd, "esc")
        logging.info("Triggered Escape")
        log_audit(
            "TRIGGER_ESCAPE_KEY",
            mode=self.state.selected_mode,
            decided_action="escape",
            key="esc",
            hwnd=hwnd,
            score=round(event.score, 4),
            template=event.template_name,
            hit_streak=self.state.hit_streak,
            miss_streak=self.state.miss_streak,
            cooldown_sec=CONFIG.trigger_cooldown_sec,
        )

        # 查找并点击确认按钮
        button_clicked = False
        yes_best_score = -1.0
        yes_best_loc = (0, 0)
        yes_threshold = CONFIG.match_threshold * 0.8

        for i in range(10):
            time.sleep(0.3)
            full_shot = capture_window_bgr(hwnd)
            best_score_this_round, best_loc_this_round = best_yes_score_and_loc(
                full_shot, self.templates, scale
            )

            if best_score_this_round > yes_best_score:
                yes_best_score = best_score_this_round
                yes_best_loc = best_loc_this_round

            if best_score_this_round >= yes_threshold:
                cap_h, cap_w = full_shot.shape[:2]
                click_x = best_loc_this_round[0]
                click_y = best_loc_this_round[1]
                if cap_w > 0 and cap_h > 0 and (cap_w != width or cap_h != height):
                    click_x = int(round(best_loc_this_round[0] * width / cap_w))
                    click_y = int(round(best_loc_this_round[1] * height / cap_h))
                    click_x = max(0, min(width - 1, click_x))
                    click_y = max(0, min(height - 1, click_y))

                click_ok = click_at(hwnd, click_x, click_y)
                button_clicked = click_ok
                if click_ok:
                    log_audit(
                        "ESCAPE_YES_CLICK_SUCCESS",
                        mode=self.state.selected_mode,
                        hwnd=hwnd,
                        score=round(event.score, 4),
                        template=event.template_name,
                        yes_score=round(best_score_this_round, 4),
                        threshold=round(yes_threshold, 4),
                        click_x=click_x,
                        click_y=click_y,
                        click_method="physical",
                        attempt=i + 1,
                    )
                    break

        if not button_clicked:
            logging.warning("Could not find confirmation button 'yes.png' after ESC")
            log_audit(
                "ESCAPE_YES_CLICK_FAILED",
                mode=self.state.selected_mode,
                hwnd=hwnd,
                score=round(event.score, 4),
                template=event.template_name,
                best_yes_score=round(yes_best_score, 4),
                best_yes_x=yes_best_loc[0],
                best_yes_y=yes_best_loc[1],
                threshold=round(yes_threshold, 4),
                click_method="physical",
            )

        # 逃跑有额外冷却
        self.state.mark_triggered(extra_cooldown=3.0)
