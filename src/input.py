import time
import logging
import win32api
import win32con

try:
    import win32gui
except ImportError:
    win32gui = None


def press_once(hwnd: int, key: str) -> None:
    """ 向指定窗口发送一次单次的按键按下和弹起消息 """

    if win32gui is None:
        logging.info("Mocking key press for non-Windows environment: %s", key)
        return
    
    # Handle special keys or length > 1
    if key.lower() == "esc":
        vk_code = win32con.VK_ESCAPE
    elif len(key) == 1:
        vk_code = win32api.VkKeyScan(key) & 0xFF
    else:
        logging.warning("Unsupported key string: %s", key)
        return

    # Map virtual key to scan code
    scan_code = win32api.MapVirtualKey(vk_code, 0)
    
    # Use PostMessage for more reliable background input
    lparam_down = 1 | (scan_code << 16)
    lparam_up = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)
    
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
    time.sleep(0.05)  # Brief delay to simulate human press duration
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam_up)


def click_at(hwnd: int, x: int, y: int) -> bool:
    """ 映射坐标并执行物理鼠标左键点击 """

    if win32gui is None:
        logging.info("Mocking click at (%d, %d)", x, y)
        return True
    
    # Convert client (x, y) to screen coordinates and do a physical click.
    try:
        screen_pos = win32gui.ClientToScreen(hwnd, (x, y))
        # Use win32api to perform a physical mouse click
        win32api.SetCursorPos(screen_pos)
        time.sleep(0.1)
        # mouse_event uses specific flags for down and up
        # LEFTDOWN = 0x0002, LEFTUP = 0x0004
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        logging.info("Performed physical click at screen pos %s", screen_pos)
        return True
    except Exception as e:
        logging.warning("Failed to perform physical click: %s", e)
        return False
