import logging
from typing import Optional, Tuple
import ctypes
import numpy as np
import cv2
import win32con

try:
    import win32gui
    import win32ui
except ImportError:
    win32gui = None
    win32ui = None

from config import CONFIG

# 尝试启用高 DPI 感知，确保 GetClientRect 返回物理像素尺寸而不是逻辑缩放后的尺寸
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def find_window_by_keyword(keyword: str) -> Optional[int]:
    """ 根据窗口标题关键词查找游戏的HWND句柄 """

    if win32gui is None:
        # Mock for non-Windows testing (e.g. testing logic on Linux)
        return 1
    keyword_lc = keyword.lower()
    result_hwnd: Optional[int] = None

    def _enum_handler(hwnd: int, _ctx: object) -> None:
        nonlocal result_hwnd
        if result_hwnd is not None:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        if keyword_lc in title.lower():
            result_hwnd = hwnd

    win32gui.EnumWindows(_enum_handler, None)
    return result_hwnd


def get_client_rect_on_screen(hwnd: int) -> Tuple[int, int, int, int]:
    """ 获取窗口客户区在屏幕上的物理坐标和尺寸 """

    if win32gui is None:
        # Mock for non-Windows testing
        return 0, 0, CONFIG.ref_width, CONFIG.ref_height
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    client_w = right - left
    client_h = bottom - top
    screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))
    return screen_left, screen_top, client_w, client_h


def capture_window_bgr(hwnd: int) -> np.ndarray:
    """ 抓图：通过 Windows API 获取窗口内容（支持后台/遮挡抓取） """
    if win32gui is None or win32ui is None:
        raise ImportError("需要安装 pywin32 库 (pip install pywin32)")

    # 直接按客户区尺寸抓图，确保识别坐标与 click_at(client 坐标)一致。
    client_rect = win32gui.GetClientRect(hwnd)
    client_w = client_rect[2] - client_rect[0]
    client_h = client_rect[3] - client_rect[1]

    if client_w <= 0 or client_h <= 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    hwndDC = win32gui.GetDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, client_w, client_h)

    saveDC.SelectObject(saveBitMap)

    # 3 = PW_CLIENTONLY(1) | PW_RENDERFULLCONTENT(2)
    # 优先抓客户区完整内容；失败则回退到 BitBlt。
    result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
    
    # 如果 PrintWindow 失败（返回0），回退到 BitBlt
    if result != 1:
        saveDC.BitBlt((0, 0), (client_w, client_h), mfcDC, (0, 0), win32con.SRCCOPY)

    signedIntsArray = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype='uint8')
    
    # 鲁棒性检查：确保数据长度匹配，不符合则补全
    expected_size = client_h * client_w * 4
    if len(img) != expected_size:
        # 如果长度不符，返回一个空图并记录警告
        logging.warning(f"Capture data size mismatch: expected {expected_size}, got {len(img)}")
        img = np.zeros(expected_size, dtype='uint8')

    img.shape = (client_h, client_w, 4)

    # 释放资源
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
