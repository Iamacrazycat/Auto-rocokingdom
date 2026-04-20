from src.utils import setup_logging
from src.bot import AutoRocoBot

def main() -> None:
    """ 程序运行入口 """

    # 启动日志
    setup_logging()
    
    # 启动循环流程
    bot = AutoRocoBot()
    bot.prompt_mode()
    bot.run()

if __name__ == "__main__":
    main()
