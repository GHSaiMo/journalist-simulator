#!/usr/bin/env python3
"""
Generate high-detail procedural & art-directed zero-text PBR textures for the
Press Reception Hall 3D scene.
All textures are saved as PNGs so both Blender Cycles and exported glTF (.glb)
preserve 100% of visual richness.
"""

import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures")
os.makedirs(OUT_DIR, exist_ok=True)


def load_cjk_font(size: int):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_carpet_texture():
    """Great Hall crimson wool carpet with golden meander (回纹) & floral border."""
    w, h = 1600, 1280
    rng = np.random.default_rng(20001027)

    # Base deep crimson wool with directional pile micro-texture
    noise_fine = rng.normal(0, 6.0, (h, w, 1))
    noise_weave_x = (np.sin(np.linspace(0, w * 0.9, w))[None, :, None]) * 2.5
    noise_weave_y = (np.cos(np.linspace(0, h * 0.9, h))[:, None, None]) * 2.5

    base = np.zeros((h, w, 3), dtype=np.float32)
    base[:, :, 0] = 122.0  # Deep Imperial Great Hall Crimson R
    base[:, :, 1] = 11.0   # Rich Low G
    base[:, :, 2] = 15.0   # Rich Low B

    # Subtle radial warmth toward center
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt(((xx - cx) / (w * 0.55)) ** 2 + ((yy - cy) / (h * 0.55)) ** 2)
    vignette = np.clip(1.06 - 0.18 * dist, 0.82, 1.06)[:, :, None]
    arr = np.clip(base * vignette + noise_fine + noise_weave_x + noise_weave_y, 0, 255).astype(np.uint8)

    img = Image.fromarray(arr, mode="RGB")
    draw = ImageDraw.Draw(img)

    gold_bright = (206, 158, 58)
    gold_mid = (172, 122, 38)
    burgundy_dark = (68, 6, 10)
    crimson_light = (148, 22, 26)

    # Outer dark burgundy edge frame
    m1 = 34
    draw.rectangle([m1, m1, w - m1, h - m1], outline=burgundy_dark, width=14)
    m2 = 54
    draw.rectangle([m2, m2, w - m2, h - m2], outline=gold_bright, width=6)

    # Traditional floral scrolling band between m2+10 and m3
    m3 = 126
    draw.rectangle([m2 + 8, m2 + 8, w - m2 - 8, h - m2 - 8], outline=burgundy_dark, width=56)
    draw.rectangle([m3, m3, w - m3, h - m3], outline=gold_bright, width=6)
    draw.rectangle([m3 + 12, m3 + 12, w - m3 - 12, h - m3 - 12], outline=gold_mid, width=3)

    # Draw stylized lotus/peony medallions along the border band
    band_mid_offset = 90
    step = 64
    for x in range(band_mid_offset, w - band_mid_offset + 1, step):
        for y in (band_mid_offset, h - band_mid_offset):
            draw.ellipse([x - 16, y - 16, x + 16, y + 16], outline=gold_bright, width=3)
            draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=gold_mid)
            draw.line([x - 26, y, x - 17, y], fill=gold_mid, width=2)
            draw.line([x + 17, y, x + 26, y], fill=gold_mid, width=2)

    for y in range(band_mid_offset + step, h - band_mid_offset, step):
        for x in (band_mid_offset, w - band_mid_offset):
            draw.ellipse([x - 16, y - 16, x + 16, y + 16], outline=gold_bright, width=3)
            draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=gold_mid)

    # Corner auspicious medallions
    for cx_c in (band_mid_offset, w - band_mid_offset):
        for cy_c in (band_mid_offset, h - band_mid_offset):
            draw.rectangle([cx_c - 28, cy_c - 28, cx_c + 28, cy_c + 28], fill=burgundy_dark, outline=gold_bright, width=4)
            draw.ellipse([cx_c - 18, cy_c - 18, cx_c + 18, cy_c + 18], outline=gold_bright, width=3)
            draw.ellipse([cx_c - 6, cy_c - 6, cx_c + 6, cy_c + 6], fill=gold_bright)

    # Subtle inner woven tone-on-tone Chinese lattice medallion in center
    for r in (210, 192, 145):
        draw.ellipse([cx - r, cy - r * 0.78, cx + r, cy + r * 0.78], outline=crimson_light, width=2)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.45))
    img.save(os.path.join(OUT_DIR, "carpet_albedo.png"))


def make_screen_panels_texture():
    """7-panel gilded Chinese landscape & harbor radiance folding screen."""
    w, h = 2100, 1050
    yy, xx = np.mgrid[0:h, 0:w]
    t_y = yy / float(h)
    t_x = xx / float(w)

    # Rich antique gold-leaf sky transitioning to mineral jade & deep harbor blue
    r = np.interp(t_y, [0.0, 0.34, 0.65, 1.0], [196, 178, 56, 20])
    g = np.interp(t_y, [0.0, 0.34, 0.65, 1.0], [154, 138, 96, 46])
    b = np.interp(t_y, [0.0, 0.34, 0.65, 1.0], [74, 68, 76, 54])

    # Layered Chinese blue-green & gold mountains (青绿金碧山水)
    layers = [
        (0.34, 0.09, 2.8, 0.4, 0.04, 7.5, (64, 98, 88), (208, 168, 76)),
        (0.46, 0.11, 3.6, 1.7, 0.05, 9.2, (36, 84, 66), (216, 174, 74)),
        (0.58, 0.09, 4.4, 3.1, 0.04, 12.0, (22, 66, 48), (198, 152, 58)),
        (0.73, 0.06, 5.5, 0.9, 0.03, 15.0, (16, 46, 36), (182, 136, 52)),
    ]

    img_arr = np.stack([r, g, b], axis=-1).astype(np.float32)

    for base_y, a1, f1, p1, a2, f2, col, rim in layers:
        ridge = base_y - a1 * np.abs(np.sin(t_x * math.pi * f1 + p1)) - a2 * np.sin(t_x * math.pi * f2 + p1 * 2)
        mask = t_y > ridge
        rim_mask = (t_y >= ridge) & (t_y < ridge + 0.009)
        mist = np.clip((t_y - ridge) * 5.0, 0.0, 1.0)
        # Mist at base of each mountain layer
        mist_glow = np.exp(-np.maximum(0.0, (t_y - (ridge + 0.09))) ** 2 / 0.004) * 0.35
        for c_i in range(3):
            layer_c = col[c_i] * (0.78 + 0.22 * (1.0 - mist)) + 215.0 * mist_glow
            img_arr[:, :, c_i] = np.where(mask, layer_c, img_arr[:, :, c_i])
            img_arr[:, :, c_i] = np.where(rim_mask, rim[c_i], img_arr[:, :, c_i])

    # Subtle golden harbor / water shimmer ribbons in lower third
    rng = np.random.default_rng(19970701)
    water_mask = t_y > 0.74
    ripples = (np.sin(yy * 0.45 + xx * 0.03) * 0.5 + 0.5) * (np.cos(xx * 0.09 - yy * 0.2) * 0.5 + 0.5)
    shimmer = water_mask * (ripples ** 3) * 75.0
    img_arr[:, :, 0] += shimmer * 1.15
    img_arr[:, :, 1] += shimmer * 0.92
    img_arr[:, :, 2] += shimmer * 0.42

    # Fine silk canvas grain
    grain = rng.normal(0, 3.5, (h, w, 1))
    img_arr = np.clip(img_arr + grain, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_arr, mode="RGB")
    draw = ImageDraw.Draw(img)

    # Stylized classical pine silhouettes & golden clouds on panels
    pine_positions = [210, 520, 1560, 1860]
    for px in pine_positions:
        py = int(h * 0.72)
        draw.line([px, py + 110, px + 8, py - 55], fill=(38, 26, 20), width=7)
        for dy, rx, ry in [(-65, 58, 18), (-38, 72, 20), (-10, 54, 16)]:
            draw.ellipse([px - rx, py + dy - ry, px + rx, py + dy + ry], fill=(24, 58, 42), outline=(176, 146, 72), width=2)

    # 7-panel vertical division borders + ornate gilded inner frames
    panel_w = w // 7
    rosewood = (54, 22, 16)
    gold_frame = (208, 168, 78)
    for i in range(7):
        x0 = i * panel_w
        x1 = (i + 1) * panel_w - 1
        # Rosewood outer panel stiles
        draw.rectangle([x0, 0, x1, h - 1], outline=rosewood, width=10)
        # Gilded inner brocade border
        draw.rectangle([x0 + 14, 18, x1 - 14, h - 18], outline=gold_frame, width=3)
        # Upper carved lattice header band & lower apron band
        draw.rectangle([x0 + 10, 10, x1 - 10, 96], fill=(64, 24, 18), outline=gold_frame, width=3)
        draw.rectangle([x0 + 22, 24, x1 - 22, 82], outline=gold_frame, width=2)
        cx_p = (x0 + x1) // 2
        draw.ellipse([cx_p - 28, 33, cx_p + 28, 73], outline=gold_frame, width=2)

        draw.rectangle([x0 + 10, h - 115, x1 - 10, h - 10], fill=(64, 24, 18), outline=gold_frame, width=3)
        draw.rectangle([x0 + 24, h - 98, x1 - 24, h - 26], outline=gold_frame, width=2)

    # Red artist seal stamp on far-left panel
    draw.rectangle([panel_w - 62, h - 190, panel_w - 36, h - 152], fill=(168, 28, 24))

    img.save(os.path.join(OUT_DIR, "screen_panels.png"))


def make_wall_silk_texture():
    """Warm champagne-cream silk brocade wallpaper with subtle damask pattern."""
    w, h = 512, 512
    yy, xx = np.mgrid[0:h, 0:w]
    rng = np.random.default_rng(102)

    # Subtle silk horizontal slub threads
    slub = np.sin(yy * 1.7) * 2.2 + rng.normal(0, 1.8, (h, w))
    damask = (np.cos(xx * 2 * math.pi / 128.0) * np.cos(yy * 2 * math.pi / 128.0)) * 4.5

    r = np.clip(234 + slub + damask, 0, 255)
    g = np.clip(223 + slub + damask * 0.9, 0, 255)
    b = np.clip(198 + slub + damask * 0.7, 0, 255)
    img = Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), mode="RGB")
    img.save(os.path.join(OUT_DIR, "wall_silk_albedo.png"))


def make_rosewood_texture():
    """Rich dark Chinese rosewood / mahogany grain."""
    w, h = 512, 512
    yy, xx = np.mgrid[0:h, 0:w]
    grain = np.sin(xx * 0.35 + np.sin(yy * 0.04) * 4.5) * 0.5 + 0.5
    fine = np.sin(xx * 1.9 + yy * 0.05) * 0.25
    val = np.clip(grain * 0.75 + fine + 0.2, 0.0, 1.0)

    r = np.clip(48 + val * 44, 0, 255)
    g = np.clip(17 + val * 18, 0, 255)
    b = np.clip(13 + val * 12, 0, 255)
    img = Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), mode="RGB")
    img.save(os.path.join(OUT_DIR, "wood_rosewood_albedo.png"))


def make_armchair_fabric_texture():
    """Warm cream-beige jacquard upholstery fabric for Great Hall armchairs."""
    w, h = 512, 512
    yy, xx = np.mgrid[0:h, 0:w]
    rng = np.random.default_rng(303)
    weave = (np.sin(xx * 1.4) * np.cos(yy * 1.4)) * 4.0
    floral = (np.sin(xx * 2 * math.pi / 96.0) * np.sin(yy * 2 * math.pi / 96.0)) * 5.0
    noise = rng.normal(0, 2.0, (h, w))

    r = np.clip(226 + weave + floral + noise, 0, 255)
    g = np.clip(213 + weave + floral * 0.9 + noise, 0, 255)
    b = np.clip(184 + weave + floral * 0.7 + noise, 0, 255)
    img = Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), mode="RGB")
    img.save(os.path.join(OUT_DIR, "fabric_armchair_albedo.png"))


def make_lace_antimacassar_texture():
    """White openwork crochet lace cloth (RGBA) for armchair headrests/armrests & tea tables."""
    w, h = 512, 512
    img = Image.new("RGBA", (w, h), (250, 248, 242, 0))
    draw = ImageDraw.Draw(img)

    white = (250, 249, 245, 245)
    cream = (238, 235, 226, 225)

    # Main woven lace body with grid openwork
    margin = 26
    draw.rectangle([margin, margin, w - margin, h - margin], fill=(248, 246, 240, 175), outline=white, width=5)

    step = 32
    for x in range(margin + 16, w - margin, step):
        for y in range(margin + 16, h - margin, step):
            # Cut out tiny diamond eyelets for authentic crochet lace transparency
            draw.polygon([(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)], fill=(250, 248, 242, 35))
            draw.ellipse([x - 12, y - 12, x + 12, y + 12], outline=white, width=2)

    # Scalloped floral crochet border around all 4 edges
    for pos in range(margin, w - margin + 1, 28):
        draw.ellipse([pos - 14, margin - 14, pos + 14, margin + 14], fill=cream, outline=white, width=2)
        draw.ellipse([pos - 14, h - margin - 14, pos + 14, h - margin + 14], fill=cream, outline=white, width=2)
        draw.ellipse([margin - 14, pos - 14, margin + 14, pos + 14], fill=cream, outline=white, width=2)
        draw.ellipse([w - margin - 14, pos - 14, w - margin + 14, pos + 14], fill=cream, outline=white, width=2)

    img.save(os.path.join(OUT_DIR, "lace_antimacassar.png"))


def make_porcelain_cup_texture():
    """Blue-and-white Great Hall porcelain teacup wrap texture."""
    w, h = 512, 512
    img = Image.new("RGB", (w, h), (246, 247, 250))
    draw = ImageDraw.Draw(img)
    cobalt = (32, 68, 148)
    gold = (196, 162, 74)

    # Rim bands (top and bottom)
    for y_band in (38, 440):
        draw.rectangle([0, y_band - 14, w, y_band + 14], outline=cobalt, width=3)
        draw.line([0, y_band - 20, w, y_band - 20], fill=gold, width=2)
        for x in range(16, w, 32):
            draw.arc([x - 12, y_band - 10, x + 12, y_band + 10], 0, 270, fill=cobalt, width=3)

    # Delicate central cloud/lotus motif
    for x in range(64, w, 128):
        draw.ellipse([x - 26, 210, x + 26, 262], outline=cobalt, width=3)
        draw.ellipse([x - 12, 224, x + 12, 248], fill=cobalt)

    img.save(os.path.join(OUT_DIR, "porcelain_cup.png"))


def make_mic_flags_atlas():
    """2x2 texture atlas for year-2000 broadcast microphone cube flags (pure geometric emblems, zero text)."""
    w, h = 512, 512
    img = Image.new("RGB", (w, h), (240, 240, 245))
    draw = ImageDraw.Draw(img)

    # Quadrant 0 (Top-Left): Red / Navy / White split broadcast emblem (zero text)
    draw.rectangle([0, 0, 255, 255], fill=(242, 244, 248), outline=(25, 45, 95), width=8)
    draw.rectangle([20, 26, 235, 116], fill=(204, 24, 34))
    draw.polygon([(46, 96), (92, 44), (132, 44), (86, 96)], fill=(255, 255, 255))
    draw.ellipse([150, 46, 202, 98], outline=(255, 255, 255), width=7)
    draw.rectangle([20, 128, 235, 228], fill=(22, 46, 104))
    draw.rectangle([46, 162, 208, 176], fill=(235, 240, 248))
    draw.rectangle([46, 188, 168, 200], fill=(180, 196, 224))

    # Quadrant 1 (Top-Right): Blue / Green / Red three-color bar emblem (zero text)
    draw.rectangle([256, 0, 511, 255], fill=(245, 246, 248), outline=(40, 44, 52), width=8)
    draw.rectangle([286, 36, 346, 148], fill=(0, 98, 204))
    draw.rectangle([354, 36, 414, 148], fill=(0, 164, 88))
    draw.rectangle([422, 36, 482, 148], fill=(218, 36, 36))
    draw.ellipse([362, 70, 406, 114], fill=(255, 255, 255))
    draw.rectangle([286, 170, 482, 212], fill=(36, 40, 48))

    # Quadrant 2 (Bottom-Left): Burgundy & Gold circular crest emblem (zero text)
    draw.rectangle([0, 256, 255, 511], fill=(138, 20, 32), outline=(216, 174, 72), width=8)
    draw.ellipse([66, 294, 190, 418], outline=(232, 188, 78), width=8)
    draw.ellipse([92, 320, 164, 392], outline=(244, 212, 124), width=5)
    draw.rectangle([48, 440, 208, 462], fill=(216, 174, 72))

    # Quadrant 3 (Bottom-Right): Warm Orange / Crimson diagonal wave emblem (zero text)
    draw.rectangle([256, 256, 511, 511], fill=(248, 245, 240), outline=(218, 88, 24), width=8)
    draw.polygon([(276, 396), (348, 286), (412, 286), (340, 396)], fill=(226, 84, 22))
    draw.polygon([(356, 396), (428, 286), (488, 286), (416, 396)], fill=(198, 36, 28))
    draw.rectangle([280, 422, 488, 468], fill=(48, 48, 54))

    img.save(os.path.join(OUT_DIR, "mic_flags_atlas.png"))


if __name__ == "__main__":
    make_carpet_texture()
    make_screen_panels_texture()
    make_wall_silk_texture()
    make_rosewood_texture()
    make_armchair_fabric_texture()
    make_lace_antimacassar_texture()
    make_porcelain_cup_texture()
    make_mic_flags_atlas()
    print("Generated all 8 PBR textures in:", OUT_DIR)
