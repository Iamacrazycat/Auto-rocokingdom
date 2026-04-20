"""
聚能模式策略。

检测到战斗后自动按下 X 键进行聚能。
"""
import logging

from config import CONFIG
from src.events import BattleDetectedEvent
from src.state import BotState
from src.strategies.base import ActionStrategy
from src.input import press_once
from src.stats import increment_daily_battle
from src.utils import log_audit


class BattleStrategy(ActionStrategy):
    """ 聚能策略：进入战斗后循环键入指定动作键 (X) """

    def __init__(self, state: BotState) -> None:
        """ 初始化战斗策略，绑定全局状态 """

        self.state = state

    def on_battle_detected(self, event: BattleDetectedEvent) -> None:
        """ 战斗检测回调：执行按键、检查冷却是以及统计战斗次数 """

        if not self.state.can_trigger(CONFIG.trigger_cooldown_sec):
            return

        # 判断是否为新战斗（首帧），更新统计
        if self.state.is_new_battle():
            new_count = increment_daily_battle()
            logging.info("=== 确认进入新战斗！今日累计战斗次数: %d ===", new_count)
            self.state.set_battle_action("battle")

        # 执行按键
        press_once(event.hwnd, CONFIG.press_key)
        logging.info("Triggered key: %s (Continuous)", CONFIG.press_key)

        log_audit(
            "TRIGGER_BATTLE_KEY",
            mode=self.state.selected_mode,
            decided_action="battle",
            key=CONFIG.press_key,
            hwnd=event.hwnd,
            score=round(event.score, 4),
            template=event.template_name,
            hit_streak=self.state.hit_streak,
            miss_streak=self.state.miss_streak,
            cooldown_sec=CONFIG.trigger_cooldown_sec,
        )

        self.state.mark_triggered()
