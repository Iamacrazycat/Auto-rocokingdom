import os
import json
import logging
from datetime import datetime

STATS_FILE = "logs/daily_stats.json"

def get_today_date_str() -> str:
    """ 获取当前日期的字符串表示 """

    return datetime.now().strftime("%Y-%m-%d")

def load_stats() -> dict:
    """ 从文件加载累计战斗统计数据 """

    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning("读取战斗统计文件失败: %s", e)
        return {}

def save_stats(data: dict) -> None:
    """ 将更新后的统计数据保存到磁盘文件 """

    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.warning("保存战斗统计文件失败: %s", e)

def increment_daily_battle() -> int:
    """ 增加当天的战斗计数并保存 """

    data = load_stats()
    today = get_today_date_str()
    count = data.get(today, 0) + 1
    data[today] = count
    save_stats(data)
    return count

def get_daily_battle_count() -> int:
    """ 查询当天的有效战斗总次数 """

    data = load_stats()
    return data.get(get_today_date_str(), 0)
