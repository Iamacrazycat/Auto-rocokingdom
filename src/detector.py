"""
战斗检测器。

只负责分析帧画面、维护检测状态、在状态变化时发布事件。
不包含任何动作/执行逻辑。
"""
import logging
import numpy as np

from config import CONFIG
from src.events import EventBus, BattleDetectedEvent, BattleEndedEvent
from src.state import BotState
from src.vision import Template, best_match_score
from typing import List


class BattleDetector:
    """ 战斗检测器：分析帧画面、维护检测状态并在状态变化时发布事件 """

    def __init__(
        self,
        event_bus: EventBus,
        state: BotState,
        templates: List[Template],
    ) -> None:
        """ 初始化检测器，绑定事件总线、状态源和识别模板 """

        self.event_bus = event_bus
        self.state = state
        self.templates = templates

    def process_frame(
        self,
        frame_processed: np.ndarray,
        scale: float,
        *,
        hwnd: int,
        full_frame: np.ndarray,
        width: int,
        height: int,
    ) -> None:
        """ 处理单个处理后的图像帧，更新 hit/miss 状态并按需触发事件 """
        import time

        score, name, _center_loc = best_match_score(
            frame_processed, self.templates, scale=scale
        )
        is_hit = score >= CONFIG.match_threshold

        if is_hit:
            self.state.record_hit()
            self.state.last_hit_time = time.time()
        else:
            self.state.record_miss()

        # 滞回判断：进入需要连续命中，退出需要连续未命中
        if not self.state.in_battle:
            detected = self.state.hit_streak >= CONFIG.required_hits
        else:
            detected = self.state.miss_streak < CONFIG.release_misses

        logging.info(
            "score=%.3f hit=%s hit_streak=%d miss_streak=%d tpl=%s",
            score, is_hit, self.state.hit_streak, self.state.miss_streak, name,
        )

        # 发布事件
        if detected:
            now = time.time()
            self.event_bus.publish(
                BattleDetectedEvent(
                    hwnd=hwnd,
                    full_frame=full_frame,
                    width=width,
                    height=height,
                    scale=scale,
                    score=score,
                    template_name=name,
                    timestamp=now,
                )
            )

        # 惰性清除决策缓存：只有当距离最后一次匹配命中超过 20 秒时才清除
        # 这可以防止技能动画等导致的短暂视觉丢失重置了“智能模式”的决策
        if (time.time() - self.state.last_hit_time) > 20.0:
            if self.state.current_battle_action is not None:
                 logging.info("Battle session expired (20s gap), clearing action cache")
                 self.state.clear_battle_action()

        # 检测到视觉上的战斗结束通知策略
        if self.state.in_battle and not detected:
            self.event_bus.publish(BattleEndedEvent(timestamp=time.time()))

        self.state.update_battle_flag(detected)
