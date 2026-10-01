# -*- coding: utf-8 -*-
"""从 docs/icon_src.jpg（猪头军师那只猪）生成 docs/icon.ico + docs/icon.png。

抠图只靠这张图自身的性质，不引额外依赖：
  - 背景 = 「中性色且亮」的像素里**与画面四边连通**的那一片（形态学重建）。
    眼睛的纯白、笑脸的纯黑都在画面内部，是洞不是背景，所以原样留住。
  - 裁到猪的外接框、按比例留边、补成正方形，各尺寸独立重采样；
  - 重采样走**预乘 alpha**，再把边缘颜色往透明区渗一圈（bleed），
    这样 Windows 拿 256 那帧自己缩放时也不会拉出白边。

图标已经提交进仓库，只有想换图时才需要重跑：python tools/make_icon.py
"""
import os
import struct

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "icon_src.jpg")
OUT_ICO = os.path.join(ROOT, "docs", "icon.ico")
OUT_PNG = os.path.join(ROOT, "docs", "icon.png")

SIZES = [16, 24, 32, 48, 64, 128, 256]
SAT_MAX = 12      # 彩度（max-min）低于它就是中性色：白底、灰边、黑线都在里面
BRIGHT_MIN = 140  # 但只有够亮的才算背景，纯黑的笑脸因此被排除
PAD = 1.06        # 外接框留 6% 余量再补成正方形
BLEED = 4         # 透明区渗色圈数


def _background(rgb: np.ndarray) -> np.ndarray:
    """背景遮罩：从四边灌进去的中性亮色区。"""
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    neutral = (sat < SAT_MAX) & (rgb.max(axis=2) > BRIGHT_MIN)
    cur = np.zeros_like(neutral)
    cur[0, :] = cur[-1, :] = True
    cur[:, 0] = cur[:, -1] = True
    cur &= neutral
    while True:  # 4 邻域膨胀 + 与 neutral 相交 = 形态学重建，直到不再长
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]
        nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= cur[:, :-1]
        nxt[:, :-1] |= cur[:, 1:]
        nxt &= neutral
        if nxt.sum() == cur.sum():
            return cur
        cur = nxt


def _bleed(rgb: np.ndarray, cur: np.ndarray, rounds: int) -> np.ndarray:
    """把不透明像素的颜色一圈圈渗进透明区，透明像素的 RGB 就不再是白底那套。"""
    out = rgb.astype(np.float32)
    known = cur.copy()
    for _ in range(rounds):
        if known.all():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(known.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = np.roll(known, (dy, dx), (0, 1))
            acc += np.roll(out, (dy, dx), (0, 1)) * k[..., None]
            cnt += k
        fill = (~known) & (cnt > 0)
        out[fill] = acc[fill] / cnt[fill][..., None]
        known |= fill
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def _resize_premul(rgba: Image.Image, size: int) -> Image.Image:
    """按预乘 alpha 缩到 size×size：不预乘的话，透明的白底会被平均进边缘。"""
    a = np.asarray(rgba).astype(np.float32)
    af = a[:, :, 3:4] / 255.0
    pre = np.concatenate([a[:, :, :3] * af, a[:, :, 3:4]], axis=2)
    small = Image.fromarray(np.clip(pre + 0.5, 0, 255).astype(np.uint8), "RGBA") \
        .resize((size, size), Image.LANCZOS)
    s = np.asarray(small).astype(np.float32)
    sf = s[:, :, 3:4] / 255.0
    rgb = np.divide(s[:, :, :3], np.maximum(sf, 1e-6), out=np.zeros_like(s[:, :, :3]), where=sf > 0)
    rgb = _bleed(np.clip(rgb + 0.5, 0, 255).astype(np.uint8), (sf[:, :, 0] > 0.5), 2)
    return Image.fromarray(np.concatenate([rgb, s[:, :, 3:4].astype(np.uint8)], axis=2), "RGBA")


def master() -> Image.Image:
    """原图 → 抠好的正方形 RGBA 母版。"""
    rgb = np.asarray(Image.open(SRC).convert("RGB"))
    fg = ~_background(rgb)
    ys, xs = np.nonzero(fg)
    if xs.size == 0:
        raise SystemExit(f"{SRC}: 一个前景像素都没抠出来，改 SAT_MAX / BRIGHT_MIN")
    h, w = rgb.shape[:2]
    side = int(round(max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1) * PAD))
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    x0, y0 = int(round(cx - side / 2)), int(round(cy - side / 2))
    alpha = (fg * 255).astype(np.uint8)
    rgba = _bleed(rgb, fg, BLEED)
    canvas = np.zeros((side, side, 4), np.uint8)
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, w), min(y0 + side, h)
    canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = np.dstack([rgba, alpha])[sy0:sy1, sx0:sx1]
    return Image.fromarray(canvas, "RGBA")


def main():
    big = master()
    frames = {s: _resize_premul(big, s) for s in SIZES}
    frames[256].save(OUT_ICO, format="ICO", sizes=[(s, s) for s in SIZES],
                     append_images=[frames[s] for s in SIZES if s != 256])
    frames[256].save(OUT_PNG)
    raw = open(OUT_ICO, "rb").read()
    assert raw[:4] == b"\x00\x00\x01\x00", OUT_ICO
    assert struct.unpack("<H", raw[4:6])[0] == len(SIZES), "尺寸数不对，写出去的 ico 不完整"
    assert os.path.getsize(OUT_ICO) > 1024, OUT_ICO
    print(f"{OUT_ICO}  {len(raw)} bytes  {len(SIZES)} sizes 母版 {big.size[0]}px")


if __name__ == "__main__":
    main()
