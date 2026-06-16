import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "video_assets"
FRAME_DIR = OUT_DIR / "tool_video_frames"
OUT_VIDEO = OUT_DIR / "SoulChord_MuseCut_tool_preview.mp4"
MUSIC = ROOT / "backend" / "generated" / "f222212b-df8d-4140-afde-60640a536986_bgm_full.mp3"
SHOWCASE = ROOT / "frontend" / "public" / "showcase"

W, H = 1920, 1080
FPS = 24
DURATION = 78

COLORS = {
    "bg": (247, 243, 235),
    "ink": (31, 45, 57),
    "muted": (98, 114, 128),
    "teal": (45, 137, 125),
    "teal_dark": (28, 67, 75),
    "coral": (195, 88, 76),
    "blue": (36, 158, 224),
    "yellow": (242, 215, 107),
    "pink": (237, 161, 190),
    "white": (255, 255, 255),
    "sand": (235, 225, 209),
    "line": (221, 214, 204),
}


def font(size, bold=False):
    return ImageFont.truetype("NotoSansCJK-Bold.ttc" if bold else "NotoSansCJK-Regular.ttc", size)


F = {
    "hero": font(86, True),
    "h1": font(68, True),
    "h2": font(46, True),
    "body": font(32),
    "body_b": font(32, True),
    "small": font(24),
    "tiny": font(19),
    "sub": font(30, True),
}


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def blend(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def measure(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def text_center(draw, xy, text, fnt, fill):
    x, y, w, h = xy
    tw, th = measure(draw, text, fnt)
    draw.text((x + (w - tw) / 2, y + (h - th) / 2 - 4), text, font=fnt, fill=fill)


def rounded(draw, xy, r=28, fill=None, outline=None, width=3):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def subtitle(draw, text):
    box_w, box_h = 1180, 76
    x, y = (W - box_w) // 2, H - 128
    rounded(draw, (x, y, x + box_w, y + box_h), r=38, fill=(255, 255, 255), outline=(230, 224, 216), width=2)
    text_center(draw, (x, y + 3, box_w, box_h), text, F["sub"], COLORS["ink"])


def draw_bg(draw, t):
    draw.rectangle((0, 0, W, H), fill=COLORS["bg"])
    blobs = [
        (260, 180, 95, COLORS["blue"], 0.18, 0.4),
        (1650, 240, 128, COLORS["yellow"], 0.22, 0.9),
        (1500, 880, 95, COLORS["pink"], 0.20, 1.5),
        (460, 850, 76, COLORS["teal"], 0.15, 2.1),
    ]
    for cx, cy, r, color, alpha, phase in blobs:
        dx = math.sin(t * 0.55 + phase) * 28
        dy = math.cos(t * 0.46 + phase) * 24
        fill = blend(COLORS["bg"], color, alpha)
        draw.ellipse((cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r), fill=fill)


def draw_logo(draw, x, y, scale=1.0):
    size = int(96 * scale)
    rounded(draw, (x, y, x + size, y + size), r=int(24 * scale), fill=COLORS["teal"], outline=COLORS["teal"])
    text_center(draw, (x, y - 4, size, size), "♡", font(int(54 * scale), True), COLORS["white"])


def draw_avatar(draw, cx, cy, name, color, delay_t):
    r = 56
    pop = 0.88 + 0.12 * ease(delay_t)
    rr = int(r * pop)
    draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=color, outline=COLORS["white"], width=8)
    text_center(draw, (cx - rr, cy - rr - 5, rr * 2, rr * 2), name[0], font(48, True), COLORS["white"])


def draw_character(draw, x, y, mood="happy", scale=1.0):
    # Simple original flat character, intentionally schematic.
    s = scale
    draw.ellipse((x + 40*s, y + 0*s, x + 150*s, y + 110*s), fill=(246, 198, 174), outline=COLORS["ink"], width=int(4*s))
    draw.arc((x + 50*s, y - 16*s, x + 142*s, y + 70*s), 180, 360, fill=COLORS["coral"], width=int(16*s))
    draw.line((x + 94*s, y + 108*s, x + 94*s, y + 168*s), fill=COLORS["ink"], width=int(4*s))
    rounded(draw, (x + 22*s, y + 160*s, x + 168*s, y + 310*s), r=int(34*s), fill=(255, 255, 255), outline=COLORS["ink"], width=int(4*s))
    draw.ellipse((x + 66*s, y + 48*s, x + 78*s, y + 60*s), fill=COLORS["ink"])
    draw.ellipse((x + 112*s, y + 48*s, x + 124*s, y + 60*s), fill=COLORS["ink"])
    if mood == "sad":
        draw.arc((x + 77*s, y + 76*s, x + 116*s, y + 108*s), 200, 340, fill=COLORS["ink"], width=int(4*s))
    else:
        draw.arc((x + 76*s, y + 62*s, x + 116*s, y + 95*s), 20, 160, fill=COLORS["ink"], width=int(4*s))
    draw.line((x + 22*s, y + 190*s, x - 42*s, y + 146*s), fill=COLORS["ink"], width=int(5*s))
    draw.line((x + 168*s, y + 190*s, x + 225*s, y + 132*s), fill=COLORS["ink"], width=int(5*s))
    draw.line((x + 64*s, y + 310*s, x + 35*s, y + 392*s), fill=COLORS["ink"], width=int(5*s))
    draw.line((x + 126*s, y + 310*s, x + 155*s, y + 392*s), fill=COLORS["ink"], width=int(5*s))


def draw_title(draw, title, kicker=None, x=130, y=118, color=None):
    if kicker:
        draw.text((x, y - 58), kicker.upper(), font=font(24, True), fill=color or COLORS["teal"])
    draw.text((x, y), title, font=F["h1"], fill=COLORS["ink"])


def card(draw, xy, title, body, accent=COLORS["teal"], icon=None):
    rounded(draw, xy, r=32, fill=COLORS["white"], outline=COLORS["line"], width=3)
    x1, y1, x2, y2 = xy
    if icon:
        rounded(draw, (x1 + 34, y1 + 34, x1 + 102, y1 + 102), r=18, fill=blend(COLORS["white"], accent, 0.18), outline=None)
        text_center(draw, (x1 + 34, y1 + 31, 68, 68), icon, font(34, True), accent)
        tx = x1 + 128
    else:
        tx = x1 + 38
    draw.text((tx, y1 + 38), title, font=F["body_b"], fill=COLORS["ink"])
    draw.text((tx, y1 + 92), body, font=F["small"], fill=COLORS["muted"])


def fit_image(path, size):
    img = Image.open(path).convert("RGB")
    img.thumbnail(size)
    canvas = Image.new("RGB", size, COLORS["white"])
    canvas.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    return canvas


def scene_intro(draw, t):
    draw_bg(draw, t)
    local = t
    draw_logo(draw, 135, 128, 1.1)
    x = 290
    draw.text((x, 142), "心声纪 SoulChord", font=F["hero"], fill=COLORS["teal_dark"])
    draw.text((x, 248), "MuseCut AI 情感创作平台", font=F["h2"], fill=COLORS["teal"])
    members = [("陶毅远", COLORS["teal"]), ("晁兴启", COLORS["coral"]), ("杨子田", COLORS["blue"])]
    for i, (name, c) in enumerate(members):
        p = ease((local - 1.0 - i * 0.28) / 0.65)
        y = int(478 + (1 - p) * 80)
        x0 = 325 + i * 390
        rounded(draw, (x0, y, x0 + 305, y + 156), r=34, fill=COLORS["white"], outline=COLORS["line"], width=3)
        draw_avatar(draw, x0 + 82, y + 78, name, c, p)
        draw.text((x0 + 152, y + 48), name, font=F["body_b"], fill=COLORS["ink"])
        draw.text((x0 + 152, y + 94), "SoulChord 队员", font=F["tiny"], fill=COLORS["muted"])
    draw_character(draw, 1500, 468, "happy", 0.9)
    subtitle(draw, "大家好，我们是心声纪 SoulChord，项目叫 MuseCut。")


def scene_problem(draw, t):
    draw_bg(draw, t)
    draw_title(draw, "普通人有故事，却很难做成作品", "Problem")
    draw_character(draw, 1320, 360, "sad", 1.1)
    labels = [("视频", COLORS["blue"], 260, 350), ("照片", COLORS["yellow"], 520, 520), ("录音", COLORS["pink"], 340, 690), ("文字", COLORS["teal"], 720, 340), ("音乐", COLORS["coral"], 800, 645)]
    for i, (txt, c, x, y) in enumerate(labels):
        p = ease((t - 9 - i * 0.18) / 0.7)
        angle = math.sin(t * 0.8 + i) * 0.08
        xx = x + math.sin(t + i) * 8
        yy = y + math.cos(t * 0.7 + i) * 8 + (1 - p) * 80
        rounded(draw, (xx, yy, xx + 200, yy + 125), r=26, fill=COLORS["white"], outline=COLORS["line"], width=3)
        draw.ellipse((xx + 24, yy + 24, xx + 78, yy + 78), fill=blend(COLORS["white"], c, 0.35))
        draw.text((xx + 95, yy + 34), txt, font=F["body_b"], fill=COLORS["ink"])
        draw.text((xx + 28, yy + 88), "零散素材", font=F["tiny"], fill=COLORS["muted"])
    subtitle(draw, "素材、情绪和声音分散在不同地方，创作很容易中断。")


def scene_position(draw, t):
    draw_bg(draw, t)
    draw_title(draw, "MuseCut 不只是配乐工具", "Positioning")
    draw_logo(draw, 835, 300, 1.35)
    draw.text((710, 455), "AI 情感创作平台", font=F["h2"], fill=COLORS["teal_dark"])
    items = [("影像", 430, 310, COLORS["blue"]), ("文字", 1170, 310, COLORS["yellow"]), ("声音", 430, 650, COLORS["pink"]), ("社区", 1170, 650, COLORS["teal"])]
    for i, (txt, cx, cy, c) in enumerate(items):
        p = ease((t - 18.2 - i * 0.18) / 0.7)
        r = 104 + 10 * math.sin(t * 1.7 + i)
        draw.line((cx, cy, 960, 510), fill=blend(COLORS["bg"], c, 0.55), width=8)
        draw.ellipse((cx - r * p, cy - r * p, cx + r * p, cy + r * p), fill=blend(COLORS["white"], c, 0.22), outline=c, width=4)
        text_center(draw, (cx - 100, cy - 28, 200, 58), txt, F["body_b"], COLORS["ink"])
    subtitle(draw, "它把影像、文字、声音和社区连接成一次完整表达。")


def scene_flow(draw, t):
    draw_bg(draw, t)
    draw_title(draw, "把复杂创作压缩成 4 步", "Workflow")
    steps = [("上传素材", "视频 + 情绪描述", "1", COLORS["teal"]), ("AI 编排", "生成声音时间轴", "2", COLORS["blue"]), ("预览成片", "试听并微调", "3", COLORS["yellow"]), ("发布导出", "MP4 + 社区", "4", COLORS["coral"])]
    for i, (title, body, num, c) in enumerate(steps):
        x = 170 + i * 430
        p = ease((t - 27 - i * 0.22) / 0.65)
        y = int(408 + (1 - p) * 80)
        rounded(draw, (x, y, x + 330, y + 210), r=34, fill=COLORS["white"], outline=c, width=4)
        rounded(draw, (x + 34, y + 36, x + 108, y + 110), r=22, fill=blend(COLORS["white"], c, 0.22), outline=None)
        text_center(draw, (x + 34, y + 33, 74, 74), num, font(36, True), c)
        draw.text((x + 132, y + 48), title, font=F["body_b"], fill=COLORS["ink"])
        draw.text((x + 132, y + 104), body, font=F["small"], fill=COLORS["muted"])
        if i < 3:
            draw.text((x + 360, y + 76), "→", font=font(52, True), fill=COLORS["teal"])
    subtitle(draw, "用户只要给出素材和表达方向，AI 先完成整体方案。")


def scene_timeline(draw, t):
    draw_bg(draw, t)
    draw_title(draw, "AI 配乐导演：声音应该在何时出现", "Music Timeline")
    x0, y0, w = 230, 330, 1460
    lanes = [("BGM", COLORS["teal"], 1.0), ("Beat", COLORS["blue"], 0.76), ("SFX", COLORS["coral"], 0.42), ("人声避让", COLORS["yellow"], 0.58)]
    for i, (name, c, ratio) in enumerate(lanes):
        y = y0 + i * 120
        draw.text((x0 - 120, y + 10), name, font=F["small"], fill=COLORS["muted"])
        rounded(draw, (x0, y, x0 + w, y + 64), r=20, fill=(255, 255, 255), outline=COLORS["line"], width=2)
        progress = ease((t - 40 - i * 0.25) / 1.6)
        draw.rounded_rectangle((x0 + 10, y + 10, x0 + 10 + int((w - 20) * ratio * progress), y + 54), radius=16, fill=c)
        if name == "Beat":
            for k in range(9):
                xx = x0 + 120 + k * 140
                if xx < x0 + 10 + int((w - 20) * ratio * progress):
                    draw.ellipse((xx - 8, y + 24, xx + 8, y + 40), fill=COLORS["white"])
        if name == "SFX":
            for k, sym in enumerate(["✦", "↗", "✦", "Hit"]):
                xx = x0 + 150 + k * 245
                if xx < x0 + 10 + int((w - 20) * ratio * progress):
                    draw.text((xx, y + 12), sym, font=F["tiny"], fill=COLORS["white"])
    play_x = x0 + int((w - 20) * ((t - 40) % 13) / 13)
    draw.line((play_x, y0 - 38, play_x, y0 + 430), fill=COLORS["ink"], width=5)
    draw.polygon([(play_x - 14, y0 - 38), (play_x + 14, y0 - 38), (play_x, y0 - 12)], fill=COLORS["ink"])
    subtitle(draw, "核心不是盲目生成音乐，而是编排 BGM、节奏、音效和人声避让。")


def scene_demo(draw, t, images):
    draw_bg(draw, t)
    draw_title(draw, "当前原型已经能跑通完整闭环", "Prototype")
    # Browser frame
    rounded(draw, (210, 250, 1140, 790), r=34, fill=(22, 29, 34), outline=COLORS["ink"], width=4)
    rounded(draw, (235, 285, 1115, 760), r=14, fill=COLORS["white"], outline=None)
    idx = int(((t - 53) / 3.2)) % len(images)
    img = images[idx]
    img2 = img.resize((820, 510))
    draw.bitmap((265, 300), img2.convert("1"), fill=COLORS["teal"]) if False else None
    # Paste is done by caller using alpha-friendly layer.
    return idx


def draw_demo_overlay(frame, draw, t, images):
    idx = scene_demo(draw, t, images)
    img = images[idx].resize((820, 510))
    frame.paste(img, (265, 300))
    draw = ImageDraw.Draw(frame)
    labels = ["平台首页", "创作实验室", "故事社区", "声音时间轴"]
    pill_x = 1225
    for i, label in enumerate(labels):
        c = COLORS["teal"] if i == idx else COLORS["sand"]
        rounded(draw, (pill_x, 320 + i * 88, pill_x + 330, 382 + i * 88), r=25, fill=c, outline=None)
        text_center(draw, (pill_x, 320 + i * 88, 330, 62), label, F["small"], COLORS["white"] if i == idx else COLORS["muted"])
    subtitle(draw, "上传、编排、预览、导出和社区分享，已经形成 MVP 闭环。")


def scene_arch(draw, t):
    draw_bg(draw, t)
    draw_title(draw, "技术架构：让 AI 从素材生成走向辅助表达", "Architecture")
    layers = [
        ("React / Vite", "前端交互"),
        ("FastAPI", "后端服务"),
        ("Music Timeline JSON", "编排协议"),
        ("ACE-Step", "音乐生成"),
        ("FFmpeg", "视频合成"),
    ]
    for i, (a, b) in enumerate(layers):
        p = ease((t - 65 - i * 0.2) / 0.75)
        x = 250 + i * 295
        y = int(398 + (1 - p) * 70)
        rounded(draw, (x, y, x + 245, y + 170), r=32, fill=COLORS["white"], outline=COLORS["teal"], width=3)
        draw.text((x + 28, y + 42), a, font=F["small"], fill=COLORS["teal_dark"])
        draw.text((x + 28, y + 92), b, font=F["tiny"], fill=COLORS["muted"])
        if i < len(layers) - 1:
            draw.text((x + 263, y + 58), "→", font=font(42, True), fill=COLORS["coral"])
    subtitle(draw, "AI 降低技术门槛，真正的故事和情感仍然来自用户。")


def scene_ending(draw, t):
    draw.rectangle((0, 0, W, H), fill=COLORS["teal_dark"])
    for i in range(18):
        x = (i * 137 + int(t * 30)) % W
        y = 150 + (i * 71) % 760
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=blend(COLORS["teal_dark"], COLORS["yellow"], 0.7))
    draw_logo(draw, 860, 230, 1.8)
    text_center(draw, (0, 460, W, 100), "MuseCut", F["hero"], COLORS["white"])
    text_center(draw, (0, 570, W, 58), "用 AI 帮普通人把真实情绪变成作品", F["h2"], (218, 238, 233))
    text_center(draw, (0, 690, W, 50), "心声纪 SoulChord · 陶毅远 / 晁兴启 / 杨子田", F["body"], COLORS["white"])


def render():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if FRAME_DIR.exists():
        shutil.rmtree(FRAME_DIR)
    FRAME_DIR.mkdir(parents=True)

    images = [
        fit_image(SHOWCASE / "musecut-hero.png", (820, 510)),
        fit_image(SHOWCASE / "creative-lab.png", (820, 510)),
        fit_image(SHOWCASE / "community-stories.png", (820, 510)),
        fit_image(SHOWCASE / "timeline-studio.png", (820, 510)),
    ]

    total = DURATION * FPS
    for n in range(total):
        t = n / FPS
        frame = Image.new("RGB", (W, H), COLORS["bg"])
        draw = ImageDraw.Draw(frame)
        if t < 9:
            scene_intro(draw, t)
        elif t < 18:
            scene_problem(draw, t)
        elif t < 27:
            scene_position(draw, t)
        elif t < 40:
            scene_flow(draw, t)
        elif t < 53:
            scene_timeline(draw, t)
        elif t < 65:
            draw_demo_overlay(frame, draw, t, images)
        elif t < 74:
            scene_arch(draw, t)
        else:
            scene_ending(draw, t)
        # Subtle vignette.
        if n % 120 == 0:
            print(f"render frame {n}/{total}")
        frame.save(FRAME_DIR / f"frame_{n:05d}.jpg", quality=88, optimize=False)

    audio_input = str(MUSIC) if MUSIC.exists() else "anullsrc=r=44100:cl=stereo"
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAME_DIR / "frame_%05d.jpg"),
    ]
    if MUSIC.exists():
        cmd += ["-stream_loop", "-1", "-i", audio_input, "-t", str(DURATION)]
        cmd += [
            "-filter_complex",
            f"[1:a]volume=0.16,afade=t=in:st=0:d=1,afade=t=out:st={DURATION-2}:d=2[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
        ]
    else:
        cmd += ["-f", "lavfi", "-i", audio_input, "-t", str(DURATION), "-map", "0:v", "-map", "1:a"]
    cmd += [
        "-c:v",
        "mpeg4",
        "-q:v",
        "3",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        str(OUT_VIDEO),
    ]
    subprocess.run(cmd, check=True)
    print(OUT_VIDEO)


if __name__ == "__main__":
    render()
