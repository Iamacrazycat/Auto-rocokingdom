# Auto-rocokingdom 开发手册

本手册旨在指导开发者如何在重构后的架构下扩展功能。项目采用了 **事件总线 (Event Bus)** + **策略模式 (Strategy)** + **集中状态管理 (State Store)** 的架构，实现了检测逻辑与动作执行的完全解耦。

---

## 1. 架构概览

- **State (`src/state.py`)**: 唯一的全局状态源（类似 TS 的 Zustand/Pinia）。存储所有组件共用的可变数据。
- **Events (`src/events.py`)**: 定义系统中发生的“事情”。
- **Detector (`src/detector.py`)**: 感知层。分析画面，修改 `State` 并发布 `Events`。
- **Strategies (`src/strategies/`)**: 执行层。订阅 `Events`，根据 `State` 执行具体动作（按键、点击）。
- **Bot (`src/bot.py`)**: 编排层。负责初始化组件、连接事件总线、启动主循环。

---

## 2. 如何添加新功能？

扩展功能的典型工作流通常涉及以下四个步骤：

### 第一步：定义新事件 (Optional)
如果你需要一个新的信号（例如“血量低”或“任务完成”），在 `src/events.py` 中添加一个 `dataclass`。

```python
# src/events.py
@dataclass
class LowHealthEvent:
    percentage: float
    timestamp: float
```

### 第二步：添加检测逻辑 (New Condition)
在 `src/detector.py` 中识别新的画面特征，并发布事件。

1.  **修改检测逻辑**：在 `BattleDetector.process_frame` 或新增检测类中，分析图像。
2.  **触发事件**：当条件满足时，通过 `self.event_bus.publish()` 发布事件。

```python
# src/detector.py
# 假设你在某一帧检测到了血量低于 20%
if health < 0.2:
    self.event_bus.publish(LowHealthEvent(percentage=health, timestamp=time.time()))
```

### 第三步：创建新的动作策略 (New Strategy)
在 `src/strategies/` 目录下创建一个新文件或在现有模块中添加。

1.  **继承自 `ActionStrategy`**。
2.  **订阅事件**：在 `register` 方法中订阅你感兴趣的事件。
3.  **实现 `on_xxx` 回调**。

```python
# src/strategies/heal.py
from src.strategies.base import ActionStrategy
from src.events import LowHealthEvent

class AutoHealStrategy(ActionStrategy):
    def register(self, event_bus):
        # 除了默认的，还可以订阅特定事件
        super().register(event_bus)
        event_bus.subscribe(LowHealthEvent, self.on_low_health)

    def on_low_health(self, event: LowHealthEvent):
        # 执行加血动作
        print(f"血量过低 ({event.percentage})，正在使用药品...")
```

### 第四步：注册到工厂
为了让用户能选到这个新模式，需要在 `src/strategies/__init__.py` 的工厂函数中进行注册。

```python
# src/strategies/__init__.py
def create_strategy(...):
    if mode == "heal":
        return AutoHealStrategy(state, templates)
    # ...
```

并在 `src/bot.py` 的 `prompt_mode` 中给用户添加一个选项。

---

## 3. 如何管理新的状态？

如果你需要记录一些持久化的运行时数据（比如“已使用的药品数量”），请将其添加到 `src/state.py`。

1.  在 `BotState.__init__` 中添加属性。
2.  添加一个描述性的修改方法（Mutator）。

```python
# src/state.py
class BotState:
    def __init__(self):
        self.medicine_used = 0

    def record_medicine_usage(self):
        self.medicine_used += 1
```

---

## 4. 最佳实践建议

1.  **不要在 Strategy 里写复杂的检测**：Strategy 应该是“盲目”的执行者。它只通过 `Event` 拿数据，通过 `State` 看状态。
2.  **保持 Detector 纯净**：Detector 只负责识别和发信号，永远不要在 Detector 里调用 `press_once`。
3.  **使用 `log_audit`**：在 Strategy 执行动作时，调用 `src.utils.log_audit` 记录事件，方便用户复盘。
4.  **组合优于继承**：如同 `SmartStrategy` 那样，可以通过组合现有的 `BattleStrategy` 和 `EscapeStrategy` 来实现更复杂的行为。

---

## 5. 调试建议

- **事件追踪**：在 `src/events.py` 的 `EventBus.publish` 中增加 `logging.debug` 可以看到所有流转的事件。
- **状态快照**：`BotState` 已经实现了 `__repr__`，你可以在任何地方打印 `self.state` 查看当前所有状态值。
