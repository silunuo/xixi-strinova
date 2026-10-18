# -*- coding: utf-8 -*-
"""
汐汐桌宠 —— 人物抠图 + 裁剪脚本
流程：
1. u2net 蒙版为基底（人物完整、边缘清晰，但会带上蓝紫背景面板）
2. 颜色洪水填充：从透明边框出发，剔除与面板颜色相近的连通区域（背景面板）
3. 清理残留小噪点（星星点）、填充内部孔洞（防止误食深色衣领）
4. 边缘抗锯齿 + 裁剪到内容边界
"""
import os

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source.jpeg")
MASK = os.path.join(HERE, "xixi_raw.png")   # u2net 输出（含面板）
OUT = os.path.join(HERE, "xixi.png")

for path in (SRC, MASK):
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"缺少抠图输入文件：{path}。请将原图 source.jpeg 和 u2net 输出的 "
            "xixi_raw.png 放在项目目录后再运行。"
        )

src = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
u2 = np.array(Image.open(MASK).convert("RGBA"))
ua = u2[..., 3]

# ---------- 1. 基底蒙版 ----------
opaque = ua > 128

# ---------- 2. 颜色洪水填充剔除背景面板 ----------
R, G, B = src[..., 0], src[..., 1], src[..., 2]
# 面板特征：蓝紫色（B 明显大于 R/G），保护角色（红发/皮肤/白衣/深色帽/青色配饰）
panel_like = (B > R + 25) & (B > G + 20) & opaque

# 把「已透明区域」和「面板色区域」合并为待剔除区域，
# 取与透明边框相连通的最大组件（即白色外框 + 蓝紫面板）
to_remove = panel_like | (ua < 10)
lab, n = ndimage.label(to_remove)          # 8连通
border_labels = {lab[2, 2], lab[2, -3], lab[-3, 2], lab[-3, -3],
                 lab[src.shape[0] // 2, 2], lab[src.shape[0] // 2, -3]}
bg_label = lab[2, 2]
remove = lab == bg_label
print("剔除背景像素:", remove.sum())

character = opaque & ~remove

# ---------- 3. 清理与修复 ----------
# 3a. 去除小噪点连通块（面板上的白色星星点）
lab2, n2 = ndimage.label(character)
sizes = ndimage.sum(np.ones_like(character), lab2, range(1, n2 + 1))
keep = np.zeros(n2 + 1, bool)
keep[1:][sizes > 1500] = True
character = keep[lab2]
print("移除小噪点块:", n2 - keep[1:].sum())

# 3b. 填充内部孔洞（防止深色区域被误判成背景而掏空）
character = ndimage.binary_fill_holes(character)

# ---------- 4. 边缘抗锯齿 ----------
alpha = (character.astype(np.float32) * 255)
alpha_img = Image.fromarray(alpha.astype(np.uint8), "L").filter(
    ImageFilter.GaussianBlur(1.0))
alpha = np.array(alpha_img)

# ---------- 5. 合成 + 裁剪 ----------
rgba = np.dstack([src.astype(np.uint8), alpha]).astype(np.uint8)
result = Image.fromarray(rgba, "RGBA")

bbox = result.getbbox()
if bbox:
    pad = 10
    l, t, r, b = bbox
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(result.width, r + pad); b = min(result.height, b + pad)
    result = result.crop((l, t, r, b))

result.save(OUT)
print("saved:", OUT, result.size, result.mode)

# 校验关键区域是否保留
chk = np.array(result)[..., 3]
h, w = chk.shape
print("帽子区域(y~12%):", round(chk[int(h*0.12), w//2]), 
      " 脸部(y~45%):", round(chk[int(h*0.45), w//2]),
      " 衣领(y~80%):", round(chk[int(h*0.80), w//2]),
      " 左上角:", round(chk[5, 5]))
