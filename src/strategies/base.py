"""
ActionStrategy 抽象基类。

所有动作策略（聚能、逃跑、智能）都实现此接口。
"""
from abc import ABC, abstractmethod
from src.events import EventBus, BattleDetectedEvent


class ActionStrategy(ABC):
    """ 动作策略基类：定义策略的统一注册和回调接口 """

    def register(self, event_bus: EventBus) -> None:
        """ 在事件总线上注册该策略感兴趣的事件 """

        """将自身注册到事件总线，订阅 BattleDetectedEvent。"""
        event_bus.subscribe(BattleDetectedEvent, self.on_battle_detected)

    @abstractmethod
    def on_battle_detected(self, event: BattleDetectedEvent) -> None:
        """ 抽象回调方法：当检测到战斗时触发该策略的具体逻辑 """

        """
        收到战斗检测事件后的处理逻辑。

        由子类实现具体动作（按键、点击等）。
        """
