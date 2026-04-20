"""
集中式状态管理模块。

所有可变运行时状态集中在 BotState 中维护，
其他组件（Detector、Strategy）通过同一个 BotState 实例读写状态。
类似 TS 中的 Zustand / Pinia store 思路。
"""
import time
import logging


class BotState:
    """ 全局状态存储类 (Store)：保存机器人运行时的各项动态数据 """

    def __init__(self) -> None:
        """ 初始化所有运行时状态变量 """

        # ── 检测状态 ──
        self.hit_streak: int = 0
        self.miss_streak: int = 0
        self.in_battle: bool = False

        # ── 动作状态 ──
        self.last_trigger_time: float = 0.0
        self.last_hit_time: float = 0.0  # 最近一次模板命中的时间点


        # ── 战斗决策缓存（智能模式用）──
        # None=未决策, "battle"=有效战斗, "escape"=逃跑
        self.current_battle_action: str = None

        # ── 运行模式 ──
        self.selected_mode: str = "battle"

    # ── 检测状态操作 ──

    def record_hit(self) -> None:
        """ 记录模板命中：增加命中计数，重置未命中计数 """
        self.hit_streak += 1
        self.miss_streak = 0

    def record_miss(self) -> None:
        """ 记录模板未命中：增加未命中计数，重置命中计数 """
        self.hit_streak = 0
        self.miss_streak += 1

    def update_battle_flag(self, detected: bool) -> None:
        """ 更新战斗状态标记 """
        self.in_battle = detected

    def reset_detection(self) -> None:
        """ 异常恢复：重置所有检测相关的计数器 """
        self.hit_streak = 0
        self.miss_streak = 0
        self.in_battle = False

    # ── 动作冷却 ──

    def can_trigger(self, cooldown: float) -> bool:
        """ 判断当前是否已过冷却期 """
        return (time.time() - self.last_trigger_time) >= cooldown

    def mark_triggered(self, extra_cooldown: float = 0.0) -> None:
        """ 标记动作已执行，记录当前触发时间点（可叠加额外冷却时间） """
        self.last_trigger_time = time.time() + extra_cooldown

    def set_battle_action(self, action: str) -> None:
        """ 缓存当前战斗的决策结果（仅首帧设置，后续复用） """
        self.current_battle_action = action

    def clear_battle_action(self) -> None:
        """ 战斗结束时清除决策缓存 """
        self.current_battle_action = None

    def is_new_battle(self) -> bool:
        """ 判断是否为新战斗：缓存为空，或者距离上次命中已过去太久(20s) """
        if self.current_battle_action is None:
            return True
        # 如果缓存不为空，但距离上次真实命中已超过 20 秒，视为新会话
        if (time.time() - self.last_hit_time) > 20.0:
            return True
        return False

    def __repr__(self) -> str:
        return (
            f"BotState(mode={self.selected_mode}, in_battle={self.in_battle}, "
            f"hits={self.hit_streak}, misses={self.miss_streak})"
        )
