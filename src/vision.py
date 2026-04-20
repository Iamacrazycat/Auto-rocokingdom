import os
import glob
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np

from config import CONFIG


@dataclass
class Template:
    """ 识别模板数据类，包含预处理后的图像矩阵 """

    name: str
    image: np.ndarray


def preprocess(image_bgr: np.ndarray) -> np.ndarray:
    """ 图像预处理：灰度化 + (可选)边缘检测/滤波 """

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    
    # 如果开启边缘匹配则执行 Canny，否则简单高斯模糊即可
    if CONFIG.use_edge_match:
        return cv2.Canny(gray, 100, 200)

    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return gray


def load_templates() -> List[Template]:
    """ 从磁盘加载所有识别模板并执行预处理 """

    pattern = os.path.join(CONFIG.template_dir, CONFIG.template_pattern)
    paths = sorted(glob.glob(pattern))
    templates: List[Template] = []

    for path in paths:
        raw = cv2.imread(path)
        if raw is None:
            logging.warning("skip unreadable template: %s", path)
            continue
        # yes.png 和 HP.png 用简单灰度处理（不做边缘检测）
        if "yes" in path.lower() or "hp" in path.lower():
             processed = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
        else:
             processed = preprocess(raw)
        templates.append(Template(name=os.path.basename(path), image=processed))

    if not templates:
        raise FileNotFoundError(
            "No template images found. Put PNG files into templates/ first."
        )

    logging.info("Loaded %d templates", len(templates))
    return templates


def best_match_score(frame_processed: np.ndarray, templates: List[Template], scale: float = 1.0) -> Tuple[float, str, Tuple[int, int]]:
    """ 在画面中查找最匹配的模板并返回最高分及位置 """

    best_score = -1.0
    best_name = ""
    best_loc = (0, 0)
    fh, fw = frame_processed.shape[:2]

    for tpl in templates:
        # 排除 yes.png 和 HP.png，它们不是战斗界面检测模板
        if "yes" in tpl.name.lower() or "hp" in tpl.name.lower():
            continue
        tpl_img = tpl.image
        # 如果运行分辨率与参考分辨率不同，动态缩放模板
        if abs(scale - 1.0) > 0.01:
            new_w = max(1, int(tpl_img.shape[1] * scale))
            new_h = max(1, int(tpl_img.shape[0] * scale))
            tpl_img = cv2.resize(tpl_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        th, tw = tpl_img.shape[:2]
        if th > fh or tw > fw:
            continue
        result = cv2.matchTemplate(frame_processed, tpl_img, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = float(max_val)
            best_name = tpl.name
            best_loc = (max_loc[0] + tw // 2, max_loc[1] + th // 2)

    return best_score, best_name, best_loc


def best_yes_score_and_loc(frame_bgr: np.ndarray, templates: List[Template], scale: float) -> Tuple[float, Tuple[int, int]]:
    """ 专门用于识别并定位“是”确认按钮的函数 """

    frame_edge = preprocess(frame_bgr)
    frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    fh, fw = frame_gray.shape[:2]

    best_score = -1.0
    best_loc = (0, 0)

    for tpl in templates:
        if "yes" not in tpl.name.lower():
            continue
        t_img = tpl.image
        if abs(scale - 1.0) > 0.01:
            t_img = cv2.resize(
                t_img,
                (max(1, int(t_img.shape[1] * scale)), max(1, int(t_img.shape[0] * scale))),
                interpolation=cv2.INTER_AREA,
            )

        th, tw = t_img.shape[:2]
        if th > fh or tw > fw:
            continue

        res_edge = cv2.matchTemplate(frame_edge, t_img, cv2.TM_CCOEFF_NORMED)
        res_gray = cv2.matchTemplate(frame_gray, t_img, cv2.TM_CCOEFF_NORMED)
        _, max_v_edge, _, max_l_edge = cv2.minMaxLoc(res_edge)
        _, max_v_gray, _, max_l_gray = cv2.minMaxLoc(res_gray)

        cur_v, cur_l = (max_v_edge, max_l_edge) if max_v_edge > max_v_gray else (max_v_gray, max_l_gray)
        if cur_v > best_score:
            best_score = float(cur_v)
            best_loc = (cur_l[0] + tw // 2, cur_l[1] + th // 2)

    return best_score, best_loc


def detect_hp_bar_color(
    frame_bgr: np.ndarray,
    templates: List[Template],
    scale: float,
    valid_bgr: Tuple[int, int, int],
    escape_bgr: Tuple[int, int, int],
    tolerance: float,
) -> Optional[str]:
    """ 智能模式：使用 SIFT 特征匹配定位 HP 血条并判断战斗类型 """

    # 从模板列表中加载原始 HP 图像（需要原图做 SIFT）
    hp_path = os.path.join(CONFIG.template_dir, "HP.png")
    hp_raw = cv2.imread(hp_path)
    if hp_raw is None:
        logging.warning("HP.png not found at %s", hp_path)
        return None

    hp_gray = cv2.cvtColor(hp_raw, cv2.COLOR_BGR2GRAY)

    # 只取画面右上角 1/3 区域进行匹配，减少干扰
    fh, fw = frame_bgr.shape[:2]
    roi_x = fw * 2 // 3
    roi_bgr = frame_bgr[0:fh // 2, roi_x:]
    roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

    # SIFT 特征提取
    sift = cv2.SIFT_create()
    kp_frame, des_frame = sift.detectAndCompute(roi_gray, None)
    kp_hp, des_hp = sift.detectAndCompute(hp_gray, None)

    if des_hp is None or len(des_hp) < 2 or des_frame is None or len(des_frame) < 2:
        logging.info("HP bar: insufficient SIFT features")
        return _fallback_template_match(roi_bgr, roi_gray, templates, scale, valid_bgr, escape_bgr, tolerance)

    # FLANN 匹配
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des_hp, des_frame, k=2)

    # Lowe's ratio test (更宽松的值 0.8，允许更多候选点)
    good_matches = []
    for m, n in matches:
        if m.distance < 0.8 * n.distance:
            good_matches.append(m)

    MIN_MATCH_COUNT = 4
    logging.info("HP bar SIFT: %d good matches (need %d)", len(good_matches), MIN_MATCH_COUNT)

    if len(good_matches) < MIN_MATCH_COUNT:
        return _fallback_template_match(roi_bgr, roi_gray, templates, scale, valid_bgr, escape_bgr, tolerance)

    # 计算单应性矩阵，定位血条在画面中的位置
    src_pts = np.float32([kp_hp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if M is None:
        logging.warning("HP bar: homography failed")
        return _fallback_template_match(roi_bgr, roi_gray, templates, scale, valid_bgr, escape_bgr, tolerance)

    # 通过单应性矩阵映射血条边界
    h_hp, w_hp = hp_gray.shape
    pts = np.float32([[0, 0], [w_hp, 0], [w_hp, h_hp], [0, h_hp]]).reshape(-1, 1, 2)
    dst = cv2.perspectiveTransform(pts, M)

    # 获取包围矩形
    rect = cv2.boundingRect(np.int32(dst))
    rx, ry, rw, rh = rect

    # 边界检查（基于 ROI 区域）
    roi_h, roi_w = roi_bgr.shape[:2]
    rx = max(0, rx)
    ry = max(0, ry)
    rw = min(rw, roi_w - rx)
    rh = min(rh, roi_h - ry)

    if rw <= 0 or rh <= 0:
        logging.warning("HP bar: mapped region out of bounds")
        return None

    bar_bgr = roi_bgr[ry:ry + rh, rx:rx + rw]

    return _analyze_bar_color(bar_bgr, valid_bgr, escape_bgr, tolerance, source="SIFT")


def _fallback_template_match(
    frame_bgr: np.ndarray,
    frame_gray: np.ndarray,
    templates: List[Template],
    scale: float,
    valid_bgr: Tuple[int, int, int],
    escape_bgr: Tuple[int, int, int],
    tolerance: float,
) -> Optional[str]:
    """ 回退方案：当 SIFT 匹配失败时使用常规模板匹配查找 HP 血条 """
    fh, fw = frame_gray.shape[:2]
    best_score = -1.0
    best_loc = (0, 0)
    best_tw, best_th = 0, 0

    for tpl in templates:
        if "hp" not in tpl.name.lower():
            continue
        t_img = tpl.image
        if abs(scale - 1.0) > 0.01:
            t_img = cv2.resize(
                t_img,
                (max(1, int(t_img.shape[1] * scale)), max(1, int(t_img.shape[0] * scale))),
                interpolation=cv2.INTER_AREA,
            )
        th, tw = t_img.shape[:2]
        if th > fh or tw > fw:
            continue
        result = cv2.matchTemplate(frame_gray, t_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = float(max_val)
            best_loc = max_loc
            best_tw, best_th = tw, th

    # 对血条匹配使用更低的阈值 (0.35)，减少漏检
    if best_score < 0.35:
        logging.info("HP bar fallback: not found (score=%.4f, threshold=0.35)", best_score)
        return None

    x, y = best_loc
    bar_bgr = frame_bgr[y:y + best_th, x:x + best_tw]
    return _analyze_bar_color(bar_bgr, valid_bgr, escape_bgr, tolerance, source="template")


def _analyze_bar_color(
    bar_bgr: np.ndarray,
    valid_bgr: Tuple[int, int, int],
    escape_bgr: Tuple[int, int, int],
    tolerance: float,
    source: str = "",
) -> Optional[str]:
    """ 分析血条区域的中心颜色，返回 'battle' 或 'escape' """
    h, w = bar_bgr.shape[:2]
    margin_y = max(1, h // 4)
    margin_x = max(1, w // 6)
    center_region = bar_bgr[margin_y:h - margin_y, margin_x:w - margin_x]

    if center_region.size == 0:
        logging.warning("HP bar center region is empty")
        return None

    # 使用中位数 (median) 代替平均值 (mean)，对异常像素更鲁棒
    avg_color = np.median(center_region, axis=(0, 1))  # BGR

    dist_valid = float(np.linalg.norm(avg_color - np.array(valid_bgr, dtype=np.float64)))
    dist_escape = float(np.linalg.norm(avg_color - np.array(escape_bgr, dtype=np.float64)))

    logging.info(
        "HP bar [%s]: avg_bgr=(%.0f,%.0f,%.0f) dist_valid=%.1f dist_escape=%.1f",
        source, avg_color[0], avg_color[1], avg_color[2], dist_valid, dist_escape,
    )

    if dist_valid <= tolerance and dist_valid < dist_escape:
        return "battle"
    elif dist_escape <= tolerance and dist_escape < dist_valid:
        return "escape"
    else:
        # 如果两个目标的距离都超过了容差，说明识别结果不可信 (Uncertain)
        logging.warning(
            "HP bar color uncertain: dist_valid=%.1f dist_escape=%.1f (tolerance=%.1f)",
            dist_valid, dist_escape, tolerance
        )
        return None
