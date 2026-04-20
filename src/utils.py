import os
import logging
import json

AUDIT_LOGGER_NAME = "audit"


def setup_logging() -> None:
    """ 配置全局运行时日志和审计日志的格式与存放路径 """

    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/runtime.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # Dedicated audit log for action traceability.
    audit_logger = logging.getLogger(AUDIT_LOGGER_NAME)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    # Clear any existing handlers in case setup_logging is called multiple times
    if audit_logger.hasHandlers():
        audit_logger.handlers.clear()
    audit_handler = logging.FileHandler("logs/audit.log", encoding="utf-8")
    audit_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    audit_logger.addHandler(audit_handler)


def log_audit(event: str, **payload: object) -> None:
    """ 记录一次业务审计日志并以此持久化重要动作 """

    data = {"event": event, **payload}
    logging.getLogger(AUDIT_LOGGER_NAME).info(
        json.dumps(data, ensure_ascii=False, sort_keys=True)
    )


def normalize_poll_interval(interval: float) -> float:
    """ 对轮询间隔时间进行合法性检查和范围归一化 """

    if interval <= 0:
        logging.warning("poll_interval_sec <= 0, fallback to 5.0")
        return 5.0
    if interval > 5.0:
        logging.warning("poll_interval_sec > 5.0, clamped to 5.0")
        return 5.0
    return interval
