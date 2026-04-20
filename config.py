from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """ 全局配置项：包含窗口名、分辨率缩放、识别阈值及颜色参数 """

    # A visible window title keyword for your game client.
    window_title_keyword: str = "洛克王国：世界"

    # Reference resolution for template matching.
    # 2560x1600 is recommended for best matching accuracy.
    ref_width: int = 2560
    ref_height: int = 1600
    require_exact_resolution: bool = False

    # Polling interval must be <= 5.0 seconds per user requirement.
    poll_interval_sec: float = 3.0

    # Trigger exactly one key press on state transition.
    press_key: str = "x"
    # User requirement: If in battle, keep pressing X with 1.0s interval.
    trigger_cooldown_sec: float = 1.0

    # Escape mode uses physical mouse click only.
    # Keep game window and confirmation button visible when triggering escape.
    escape_click_method: str = "physical"

    # Detection settings.
    match_threshold: float = 0.50
    required_hits: int = 1
    release_misses: int = 2
    use_edge_match: bool = True

    # Smart Mode (Mode 3) — HP 血条颜色判断
    # BGR 格式的目标颜色
    hp_valid_battle_bgr: tuple = (161, 63, 255)   # #ff3fa1 粉色 → 有效战斗
    hp_escape_bgr: tuple = (21, 198, 115)          # #73c615 绿色 → 逃跑
    hp_color_tolerance: float = 80.0               # 颜色欧氏距离容差

    # Templates.
    template_dir: str = "templates"
    template_pattern: str = "*.png"

    # Runtime controls.
    stop_hotkey: str = "f8"


CONFIG = AppConfig()
