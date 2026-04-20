"""
策略模块。

提供 create_strategy() 工厂函数，根据模式名创建对应的 ActionStrategy 并注册到 EventBus。
"""
from src.strategies.base import ActionStrategy
from src.strategies.battle import BattleStrategy
from src.strategies.escape import EscapeStrategy
from src.strategies.smart import SmartStrategy
from src.events import EventBus
from src.state import BotState
from src.vision import Template
from typing import List


def create_strategy(
    mode: str,
    event_bus: EventBus,
    state: BotState,
    templates: List[Template],
) -> ActionStrategy:
    """ 策略工厂：根据运行模式创建 Strategy 并注册到 EventBus """
    if mode == "escape":
        strategy = EscapeStrategy(state, templates)
    elif mode == "smart":
        strategy = SmartStrategy(state, templates)
    else:
        strategy = BattleStrategy(state)

    strategy.register(event_bus)
    return strategy
