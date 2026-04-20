"""
事件总线（Observer 模式）。

定义事件数据类型，以及同步发布/订阅的 EventBus。
Detector 发布事件，Strategy 订阅事件，两者不直接依赖。
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Type
import numpy as np


# ────────────────────────────────────────────────────────────
#  事件类型
# ────────────────────────────────────────────────────────────

@dataclass
class BattleDetectedEvent:
    """ 匹配到战斗状态时的事件数据类 """
    hwnd: int
    full_frame: np.ndarray
    width: int
    height: int
    scale: float
    score: float
    template_name: str
    timestamp: float


@dataclass
class BattleEndedEvent:
    """ 战斗结束时的事件数据类 """
    timestamp: float


# ────────────────────────────────────────────────────────────
#  EventBus — 同步发布 / 订阅
# ────────────────────────────────────────────────────────────

class EventBus:
    """ 同步事件总线：用于组件间的发布/订阅解耦 """

    def __init__(self) -> None:
        """ 初始化事件处理订阅列表 """

        self._subscribers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, handler: Callable) -> None:
        """ 订阅特定类型的事件（一个事件可有多个处理器） """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logging.debug(
            "EventBus: %s subscribed to %s",
            getattr(handler, "__qualname__", repr(handler)),
            event_type.__name__,
        )

    def unsubscribe(self, event_type: Type, handler: Callable) -> None:
        """ 取消订阅特定类型的事件 """

        """取消注册事件处理器。"""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: object) -> None:
        """ 发布事件并同步调用所有已订阅的处理器 """
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logging.debug("EventBus: no subscribers for %s", event_type.__name__)
            return
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logging.exception(
                    "EventBus: handler %s raised an exception for %s",
                    getattr(handler, "__qualname__", repr(handler)),
                    event_type.__name__,
                )
