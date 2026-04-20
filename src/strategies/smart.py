"""
智能挂机模式策略。

根据 HP 血条颜色自动判断：
- 粉色 (#ff3fa1) → 有效战斗（委托 BattleStrategy）
- 绿色 (#73c615) → 意外遭遇（委托 EscapeStrategy）

仅在每场新战斗的首帧进行颜色检测，后续帧复用缓存的决策。
"""
import logging

from config import CONFIG
from src.events import BattleDetectedEvent
from src.state import BotState
from src.strategies.base import ActionStrategy
from src.strategies.battle import BattleStrategy
from src.strategies.escape import EscapeStrategy
from src.vision import Template, detect_hp_bar_color
from src.utils import log_audit
from typing import List


class SmartStrategy(ActionStrategy):
    """ 智能策略：根据 HP 血条颜色自动决策 (粉色聚能 / 绿色逃跑) """

    def __init__(self, state: BotState, templates: List[Template]) -> None:
        """ 初始化智能策略并组装内部的战斗/逃跑子策略 """
        self.state = state
        self.templates = templates
        self._battle = BattleStrategy(state)
        self._escape = EscapeStrategy(state, templates)

    def on_battle_detected(self, event: BattleDetectedEvent) -> None:
        """ 战斗检测回调：首帧检测 HP 颜色决策，后续帧复用缓存 """
        if not self.state.can_trigger(CONFIG.trigger_cooldown_sec):
            return

        # 首帧：进行 HP 血条颜色检测
        if self.state.is_new_battle():
            action = detect_hp_bar_color(
                event.full_frame,
                self.templates,
                event.scale,
                valid_bgr=CONFIG.hp_valid_battle_bgr,
                escape_bgr=CONFIG.hp_escape_bgr,
                tolerance=CONFIG.hp_color_tolerance,
            )

            if action is None:
                # HP 血条未找到或颜色不匹配目标，不做决策，等待下一帧
                logging.debug("Smart Mode: HP bar uncertain, waiting for clearer frame...")
                return 

            if action == "battle":
                logging.info("Smart Mode: Pink HP bar -> Valid Battle (Battle Mode)")
            else:
                logging.info("Smart Mode: Green HP bar -> Wild Encounter (Escape Mode)")

            self.state.set_battle_action(action)

            log_audit(
                "SMART_MODE_HP_CHECK",
                action_decided=action,
            )

        # 使用缓存的决策
        current_action = self.state.current_battle_action

        if current_action == "battle":
            self._battle.on_battle_detected(event)
        else:
            self._escape.on_battle_detected(event)
