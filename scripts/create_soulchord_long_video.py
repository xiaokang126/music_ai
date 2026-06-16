import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from create_soulchord_tool_video import (
    W,
    H,
    COLORS,
    F,
    font,
    ease,
    smooth,
    blend,
    rounded,
    text_center,
    draw_bg,
    draw_logo,
    draw_avatar,
    draw_character,
    draw_title,
    card,
    fit_image,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "video_assets"
FRAME_DIR = OUT_DIR / "long_video_frames"
OUT_VIDEO = OUT_DIR / "SoulChord_MuseCut_long_preview.mp4"
BGM = OUT_DIR / "bgm" / "《传说之下》His Theme【Hi-Res百万级录音棚试听】_音频.mp4"
SCREEN = OUT_DIR / "app_screenshots"
SHOWCASE = ROOT / "frontend" / "public" / "showcase"

FPS = 20
DURATION = 210


def draw_caption(draw, text):
    x, y, w, h = 280, 952, 1360, 78
    rounded(draw, (x, y, x + w, y + h), r=38, fill=COLORS["white"], outline=(232, 225, 216), width=2)
    text_center(draw, (x + 22, y + 3, w - 44, h), text, F["sub"], COLORS["ink"])


def draw_time_tag(draw, tag):
    # Time tags were useful while editing, but they distract in the final cut.
    return


def shadow_card(frame, xy, r=34, fill=COLORS["white"], outline=COLORS["line"]):
    x1, y1, x2, y2 = map(int, xy)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius=r, fill=(38, 45, 55, 34))
    layer = layer.filter(ImageFilter.GaussianBlur(10)) if False else layer
    frame.paste(Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB"))
    d = ImageDraw.Draw(frame)
    rounded(d, (x1, y1, x2, y2), r=r, fill=fill, outline=outline, width=3)


def paste_in_frame(frame, image, xy, size, label=None, accent=COLORS["teal"]):
    x, y = xy
    w, h = size
    d = ImageDraw.Draw(frame)
    rounded(d, (x, y, x + w, y + h), r=32, fill=(24, 31, 38), outline=(24, 31, 38), width=3)
    rounded(d, (x + 18, y + 48, x + w - 18, y + h - 18), r=18, fill=COLORS["white"], outline=None)
    for i, c in enumerate([COLORS["coral"], COLORS["yellow"], COLORS["teal"]]):
        d.ellipse((x + 32 + i * 24, y + 20, x + 46 + i * 24, y + 34), fill=c)
    img = image.copy()
    img.thumbnail((w - 36, h - 68))
    frame.paste(img, (x + 18 + (w - 36 - img.width) // 2, y + 52 + (h - 70 - img.height) // 2))
    if label:
        rounded(d, (x + w - 205, y + 16, x + w - 30, y + 48), r=16, fill=accent, outline=None)
        text_center(d, (x + w - 205, y + 15, 175, 32), label, font(17, True), COLORS["white"])


def load_assets():
    assets = {
        "home": fit_image(SCREEN / "home.png", (1200, 675)),
        "upload": fit_image(SCREEN / "upload.png", (1200, 675)),
        "community": fit_image(SCREEN / "community.png", (1200, 675)),
        "learn": fit_image(SCREEN / "learn.png", (1200, 675)),
        "export": fit_image(SCREEN / "export_public.png", (1200, 675)),
        "show_home": fit_image(SHOWCASE / "musecut-hero.png", (1200, 675)),
        "show_timeline": fit_image(SHOWCASE / "timeline-studio.png", (1200, 675)),
        "show_lab": fit_image(SHOWCASE / "creative-lab.png", (1200, 675)),
        "show_comm": fit_image(SHOWCASE / "community-stories.png", (1200, 675)),
    }
    return assets


def scene_intro(frame, draw, t):
    draw_bg(draw, t)
    draw_time_tag(draw, "0:00")
    draw_logo(draw, 130, 178, 1.18)
    draw.text((282, 184), "心声纪 SoulChord", font=F["hero"], fill=COLORS["teal_dark"])
    draw.text((286, 292), "MuseCut AI 情感创作平台", font=F["h2"], fill=COLORS["teal"])
    draw.text((290, 362), "让普通人把真实情绪变成可以观看、可以聆听、可以分享的作品", font=F["body"], fill=COLORS["muted"])
    members = [("陶毅远", COLORS["teal"]), ("晁兴启", COLORS["coral"]), ("杨子田", COLORS["blue"])]
    for i, (name, color) in enumerate(members):
        p = ease((t - 3 - i * 0.45) / 1.0)
        x = 280 + i * 410
        y = 556 + int((1 - p) * 75)
        rounded(draw, (x, y, x + 330, y + 158), r=34, fill=COLORS["white"], outline=COLORS["line"], width=3)
        draw_avatar(draw, x + 82, y + 79, name, color, p)
        draw.text((x + 154, y + 48), name, font=F["body_b"], fill=COLORS["ink"])
        draw.text((x + 154, y + 96), "SoulChord 队员", font=F["tiny"], fill=COLORS["muted"])
    draw_character(draw, 1530, 510, "happy", 0.9)
    draw_caption(draw, "大家好，我们是心声纪 SoulChord，项目叫 MuseCut。")


def scene_problem(frame, draw, t):
    draw_bg(draw, t)
    draw_time_tag(draw, "0:20")
    draw_title(draw, "为什么普通人很难完成情感创作？", "Problem", x=130, y=142)
    problems = [
        ("素材很多", "视频、照片、录音和文字分散", COLORS["blue"], "1"),
        ("声音难做", "BGM、转场、人声避让都要经验", COLORS["coral"], "2"),
        ("流程不清", "不知道下一步该按哪个按钮", COLORS["yellow"], "3"),
        ("情绪易散", "模板很快，却不一定真诚", COLORS["teal"], "4"),
    ]
    for i, (title, body, color, icon) in enumerate(problems):
        x = 175 + (i % 2) * 760
        y = 330 + (i // 2) * 230
        p = ease((t - 22 - i * 0.35) / 0.9)
        y += int((1 - p) * 60)
        rounded(draw, (x, y, x + 640, y + 170), r=34, fill=COLORS["white"], outline=COLORS["line"], width=3)
        rounded(draw, (x + 38, y + 42, x + 110, y + 114), r=20, fill=blend(COLORS["white"], color, 0.22), outline=None)
        text_center(draw, (x + 38, y + 40, 72, 72), icon, font(34, True), color)
        draw.text((x + 140, y + 42), title, font=F["body_b"], fill=COLORS["ink"])
        draw.text((x + 140, y + 96), body, font=F["small"], fill=COLORS["muted"])
    draw_character(draw, 1510, 185, "sad", 0.76)
    draw_caption(draw, "最难的不是有没有素材，而是怎样组织成完整表达。")


def scene_position(frame, draw, t):
    draw_bg(draw, t)
    draw_time_tag(draw, "0:45")
    draw_title(draw, "MuseCut 的定位", "Positioning", x=130, y=142)
    nodes = [("影像", 455, 350, COLORS["blue"]), ("文字", 1330, 350, COLORS["yellow"]), ("声音", 455, 690, COLORS["pink"]), ("社区", 1330, 690, COLORS["teal"])]
    for i, (name, cx, cy, color) in enumerate(nodes):
        p = ease((t - 47 - i * 0.22) / 0.9)
        draw.line((cx, cy, 960, 535), fill=blend(COLORS["bg"], color, 0.35), width=7)
        r = max(2, int(92 * p + 4 * math.sin(t * 2 + i)))
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=blend(COLORS["white"], color, 0.24), outline=color, width=4)
        text_center(draw, (cx - 100, cy - 30, 200, 60), name, F["body_b"], COLORS["ink"])
    rounded(draw, (705, 315, 1215, 635), r=42, fill=COLORS["white"], outline=COLORS["line"], width=3)
    draw_logo(draw, 890, 348, 1.28)
    text_center(draw, (705, 492, 510, 74), "AI 情感创作平台", F["h1"], COLORS["teal_dark"])
    text_center(draw, (705, 570, 510, 40), "连接影像、文字、声音和社区", F["small"], COLORS["muted"])
    draw_caption(draw, "AI 降低制作难度，故事和情感仍然属于用户自己。")


def scene_workflow(frame, draw, t):
    draw_bg(draw, t)
    draw_time_tag(draw, "1:05")
    draw_title(draw, "MVP 把创作压缩成 4 步", "Workflow", x=130, y=142)
    steps = [
        ("1", "上传素材", "选择表达方向\n补充故事描述", COLORS["teal"]),
        ("2", "AI 编排", "分析视频节点\n生成声音时间轴", COLORS["blue"]),
        ("3", "预览微调", "点击片段跳转\n试听声音情绪", COLORS["yellow"]),
        ("4", "导出分享", "生成 MP4 成片\n发布故事社区", COLORS["coral"]),
    ]
    for i, (num, title, body, color) in enumerate(steps):
        p = ease((t - 67 - i * 0.55) / 1.1)
        x = 115 + i * 445
        y = 382 + int((1 - p) * 80)
        rounded(draw, (x, y, x + 365, y + 278), r=38, fill=COLORS["white"], outline=color, width=4)
        rounded(draw, (x + 36, y + 40, x + 112, y + 116), r=24, fill=blend(COLORS["white"], color, 0.24), outline=None)
        text_center(draw, (x + 36, y + 37, 76, 76), num, font(38, True), color)
        draw.text((x + 36, y + 140), title, font=F["body_b"], fill=COLORS["ink"])
        draw.multiline_text((x + 36, y + 196), body, font=F["tiny"], fill=COLORS["muted"], spacing=10)
        if i < 3:
            draw.text((x + 385, y + 96), "→", font=font(52, True), fill=COLORS["teal"])
    draw_caption(draw, "用户顺着流程走，AI 先给出完整方案，再允许局部微调。")


def scene_home_upload(frame, draw, t, assets):
    draw_bg(draw, t)
    draw_time_tag(draw, "1:32")
    draw_title(draw, "页面操作：从首页进入创作", "Operation 1", x=130, y=118)
    p = smooth((t - 92) / 33)
    if p < 0.48:
        paste_in_frame(frame, assets["home"], (145, 268), (980, 610), "首页")
        card(draw, (1215, 320, 1690, 468), "选择表达入口", "校园记忆 / 亲情故事 / 旅行日常", COLORS["teal"], "1")
        card(draw, (1215, 500, 1690, 648), "降低理解成本", "用户先选情绪，不先学软件", COLORS["blue"], "2")
        card(draw, (1215, 680, 1690, 828), "进入创作", "从故事方向自然过渡到上传", COLORS["coral"], "3")
    else:
        paste_in_frame(frame, assets["upload"], (145, 268), (980, 610), "上传")
        card(draw, (1215, 305, 1710, 460), "上传视频素材", "支持短视频素材作为创作起点", COLORS["teal"], "1")
        card(draw, (1215, 492, 1710, 647), "补充故事描述", "让 AI 理解这段素材想表达什么", COLORS["blue"], "2")
        card(draw, (1215, 679, 1710, 834), "生成声音方案", "点击一次进入 AI 声音编排", COLORS["coral"], "3")
    draw_caption(draw, "从首页到上传页，用户只需要提供素材和表达意图。")


def scene_timeline(frame, draw, t, assets):
    draw_bg(draw, t)
    draw_time_tag(draw, "2:05")
    draw_title(draw, "核心页面：Music Timeline 声音时间轴", "Operation 2", x=130, y=118)
    paste_in_frame(frame, assets["show_timeline"], (106, 265), (820, 575), "声音编排")
    x0, y0, w = 1015, 330, 710
    lanes = [("BGM", COLORS["teal"], 0.95), ("Beat", COLORS["blue"], 0.82), ("SFX", COLORS["coral"], 0.55), ("人声避让", COLORS["yellow"], 0.68)]
    for i, (name, color, ratio) in enumerate(lanes):
        y = y0 + i * 110
        draw.text((x0, y + 8), name, font=F["tiny"], fill=COLORS["muted"])
        rounded(draw, (x0 + 120, y, x0 + w, y + 58), r=18, fill=COLORS["white"], outline=COLORS["line"], width=2)
        prog = ease((t - 128 - i * 0.35) / 1.4)
        draw.rounded_rectangle((x0 + 132, y + 10, x0 + 132 + int((w - 144) * ratio * prog), y + 48), radius=15, fill=color)
        if name == "Beat":
            for k in range(7):
                xx = x0 + 170 + k * 68
                if xx < x0 + 132 + int((w - 144) * ratio * prog):
                    draw.ellipse((xx - 6, y + 23, xx + 6, y + 35), fill=COLORS["white"])
    play_x = x0 + 132 + int(((t - 125) % 12) / 12 * 560)
    draw.line((play_x, y0 - 40, play_x, y0 + 400), fill=COLORS["ink"], width=5)
    card(draw, (1015, 748, 1725, 900), "点击片段即可跳转播放", "用户能直接检查某一段声音和画面是否匹配", COLORS["teal"], "▶")
    draw_caption(draw, "它不是贴一首歌，而是编排不同声音在不同时间出现。")


def scene_export(frame, draw, t, assets):
    draw_bg(draw, t)
    draw_time_tag(draw, "2:38")
    draw_title(draw, "页面操作：预览、导出和成片", "Operation 3", x=130, y=118)
    paste_in_frame(frame, assets["export"], (122, 265), (960, 575), "导出页")
    rounded(draw, (1175, 300, 1715, 625), r=34, fill=COLORS["white"], outline=COLORS["line"], width=3)
    text_center(draw, (1175, 332, 540, 50), "默认导出 MP4 视频成片", F["body_b"], COLORS["teal_dark"])
    draw.text((1228, 430), "✓ 音乐叠加到原视频", font=F["small"], fill=COLORS["ink"])
    draw.text((1228, 495), "✓ 保留音频与 JSON 方案", font=F["small"], fill=COLORS["ink"])
    draw.text((1228, 560), "✓ 校验 BGM 覆盖完整视频", font=F["small"], fill=COLORS["ink"])
    rounded(draw, (1175, 665, 1715, 820), r=34, fill=blend(COLORS["white"], COLORS["teal"], 0.12), outline=COLORS["teal"], width=3)
    text_center(draw, (1175, 698, 540, 50), "导出的不是单独音乐", F["body_b"], COLORS["ink"])
    text_center(draw, (1175, 750, 540, 40), "而是可直接发布的视频作品", F["small"], COLORS["muted"])
    draw_caption(draw, "试听满意后，系统导出的是带配乐的视频成片。")


def scene_center_community(frame, draw, t, assets):
    draw_bg(draw, t)
    draw_time_tag(draw, "2:58")
    draw_title(draw, "个人中心与故事社区", "Community", x=130, y=118)
    paste_in_frame(frame, assets["community"], (910, 265), (850, 575), "社区")
    cards = [
        ("自动保存", "退出后仍可在个人中心继续任务", COLORS["teal"], 280),
        ("作品管理", "继续创作、删除草稿、修改头像昵称", COLORS["blue"], 445),
        ("社区发布", "实名或匿名分享作品，保留表达边界", COLORS["coral"], 610),
    ]
    for title, body, color, y in cards:
        card(draw, (140, y, 790, y + 130), title, body, color, "✓")
    draw_caption(draw, "创作不会因为关闭网页丢失，作品也可以进入社区交流。")


def scene_arch(frame, draw, t):
    draw_bg(draw, t)
    draw_time_tag(draw, "3:12")
    draw_title(draw, "技术架构", "Architecture", x=130, y=142)
    layers = [
        ("React / Vite", "前端交互"),
        ("FastAPI", "后端服务"),
        ("Timeline JSON", "声音编排协议"),
        ("ACE-Step", "BGM 生成"),
        ("FFmpeg", "视频导出"),
    ]
    for i, (title, body) in enumerate(layers):
        x = 170 + i * 335
        y = 445 + int((1 - ease((t - 192 - i * 0.2) / 0.8)) * 70)
        rounded(draw, (x, y, x + 275, y + 160), r=32, fill=COLORS["white"], outline=COLORS["teal"], width=3)
        title_font = font(23 if len(title) > 12 else 25, True)
        draw.text((x + 28, y + 42), title, font=title_font, fill=COLORS["teal_dark"])
        draw.text((x + 28, y + 92), body, font=F["tiny"], fill=COLORS["muted"])
        if i < 4:
            draw.text((x + 292, y + 52), "→", font=font(42, True), fill=COLORS["coral"])
    draw_caption(draw, "各层通过结构化时间线协作，模型和导出能力都可以继续替换升级。")


def scene_outro(frame, draw, t):
    draw.rectangle((0, 0, W, H), fill=COLORS["teal_dark"])
    for i in range(36):
        x = (i * 93 + int(t * 28)) % W
        y = 120 + (i * 79) % 820
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=blend(COLORS["teal_dark"], COLORS["yellow"], 0.75))
    draw_logo(draw, 860, 230, 1.9)
    text_center(draw, (0, 465, W, 90), "MuseCut", F["hero"], COLORS["white"])
    text_center(draw, (0, 575, W, 60), "用 AI 帮普通人把真实情绪变成作品", F["h2"], (221, 241, 236))
    text_center(draw, (0, 700, W, 44), "心声纪 SoulChord · 陶毅远 / 晁兴启 / 杨子田", F["body"], COLORS["white"])


def draw_frame(t, assets):
    frame = Image.new("RGB", (W, H), COLORS["bg"])
    draw = ImageDraw.Draw(frame)
    if t < 20:
        scene_intro(frame, draw, t)
    elif t < 45:
        scene_problem(frame, draw, t)
    elif t < 65:
        scene_position(frame, draw, t)
    elif t < 92:
        scene_workflow(frame, draw, t)
    elif t < 125:
        scene_home_upload(frame, draw, t, assets)
    elif t < 158:
        scene_timeline(frame, draw, t, assets)
    elif t < 178:
        scene_export(frame, draw, t, assets)
    elif t < 192:
        scene_center_community(frame, draw, t, assets)
    elif t < 204:
        scene_arch(frame, draw, t)
    else:
        scene_outro(frame, draw, t)
    return frame


def render():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if FRAME_DIR.exists():
        shutil.rmtree(FRAME_DIR)
    FRAME_DIR.mkdir(parents=True)
    assets = load_assets()
    total = DURATION * FPS
    for n in range(total):
        t = n / FPS
        frame = draw_frame(t, assets)
        if n % 200 == 0:
            print(f"render frame {n}/{total}")
        frame.save(FRAME_DIR / f"frame_{n:05d}.jpg", quality=88, optimize=False)

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAME_DIR / "frame_%05d.jpg"),
        "-stream_loop",
        "-1",
        "-i",
        str(BGM),
        "-t",
        str(DURATION),
        "-filter_complex",
        f"[1:a]volume=0.06,afade=t=in:st=0:d=2,afade=t=out:st={DURATION-4}:d=4[a]",
        "-map",
        "0:v",
        "-map",
        "[a]",
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
