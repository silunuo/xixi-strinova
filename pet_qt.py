#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汐汐小桌宠 · 原生桌面版（PyQt5）
- 无边框 / 半透明 / 始终置顶：真正的像素级透明，直接看到桌面
- 拖动、缩放全部走原生窗口消息，丝滑流畅（无任何 IPC / 浏览器引擎）
- rua 头 / 投喂 / 对话 / 心情与饱食度 / 打瞌睡 / 唤回
- 音效与动画手感对齐网页版 index.html
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "xixi.png")
IMG_SAD = os.path.join(HERE, "xixi_sad.png")

from PyQt5.QtCore import (Qt, QTimer, QPoint, QPointF, QRectF, QElapsedTimer,
                          QSize, QPropertyAnimation, QEvent)
from PyQt5.QtGui import (QPainter, QPixmap, QColor, QFont, QFontMetrics, QPen,
                         QBrush, QLinearGradient, QRadialGradient)
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLineEdit,
                             QLabel, QHBoxLayout, QVBoxLayout,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect)

# ---------------------------------------------------------------- 常量
BASE_W, BASE_H = 400, 480          # 窗口设计尺寸（缩放 1x）
PET_BASE_W = 204                   # 人物基础宽度（原 340 的 60%，文字按钮不随之缩放）
CLOSE_EXTRA_Y = 32                 # 关闭按钮下移量（设计像素）
CYAN = QColor("#2ec4d9")
CYAN_DEEP = QColor("#0e9bb5")
CORAL = QColor("#f0705f")
INK = QColor("#3a4763")

LINES = {
    "patLight": ["唔…？", "喵？", "怎么啦？", "……戳到我啦。", "（歪头）"],
    "patLong": ["喵呜～……好舒服。", "头发要乱了啦！笨蛋……", "再、再摸一会儿也可以啦。",
                "嘿嘿，好痒……", "汐汐的帽子不许摘哦！"],
    "feed": ["吧唧吧唧……谢谢投喂！", "呜哇，是这个！好开心！", "喵呜…投喂值班日快乐！",
             "（嚼嚼）…还要！", "肚子暖暖的，谢谢你～"],
    "feedFull": ["吃不下了啦……肚子好撑。", "已经饱饱的了喵～"],
    "hungry": ["肚子…在叫了。", "有吃的吗……？", "咕噜咕噜……", "有点没力气了……"],
    "greet": ["你来啦！今天也要开心喵。", "汐汐在这里等你哦。", "呜…是你就好。", "注意到我啦？嘿嘿。"],
    "chatFood": ["想吃鱼！……或者蛋糕。", "你吃饭了吗？要好好吃饭哦。", "投喂我投喂我！（举手）"],
    "chatPat": ["头…给你摸一下下哦。", "帽子下面是秘密！", "摸头会长高……真的吗？"],
    "chatName": ["我是汐汐！卡拉彼丘的汐汐！", "汐汐汐～记住没！", "耳朵是真的！…大概。"],
    "chatLike": ["诶？！……喜、喜欢吗？", "喵呜……❤", "说这种话……不害臊吗……"],
    "chatMood": ["现在心情还不错喵。", "只要你来，心情就很好。", "有点困了……但还能陪你。"],
    "chatBye": ["要走了吗……路上小心。", "再见喵！会想你的。", "下次再来玩哦！"],
    "idle": ["今天天气真好喵。", "你在干嘛呀？", "嘀嘀咕咕……", "（盯着你看）",
             "要摸摸头吗？", "喵～", "发呆了很久了哦。"],
    "idleHungry": ["（捂着肚子）……", "好想吃东西……", "有零食的味道吗？"],
    "sleep": ["Zzz……", "（睡着了，发出小小的呼吸声）"],
    "wake": ["…！醒了醒了，没睡没睡。", "喵呜……睡迷糊了。"],
    "closeBye": ["那汐汐先去休息了……", "晚安喵。", "要记得想我哦！"],
}
FOODS = ["🍰", "🐟", "🍙", "🥮", "🍓", "🧋", "🍡", "🦐"]
HEARTS = ["❤️", "💕", "💖", "✨", "💗"]
CRUMBS = ["✨", "⭐", "🍃", "・"]


def pick(arr):
    return random.choice(arr)


def emoji_font(px):
    f = QFont("Segoe UI Emoji")
    f.setPixelSize(int(px))
    f.setStyleStrategy(QFont.PreferDefault)
    return f


def text_font(px):
    f = QFont("Microsoft YaHei")
    f.setPixelSize(int(px))
    return f


def ensure_sad_pixmap():
    """预生成去饱和版人物图（难过状态用）"""
    if os.path.exists(IMG_SAD):
        return
    try:
        from PIL import Image, ImageEnhance
        im = Image.open(IMG).convert("RGBA")
        im = ImageEnhance.Color(im).enhance(0.82)
        im = ImageEnhance.Brightness(im).enhance(0.985)
        im.save(IMG_SAD)
    except Exception:
        import shutil
        shutil.copy(IMG, IMG_SAD)


# ---------------------------------------------------------------- 音效
# 与网页版 index.html 的 WebAudio 完全一致的配方：
#   振荡器(sine/square/triangle) + gain 从 vol 指数衰减到 0.0001（时长即 dur），
#   无 attack（正弦/方波零相位起幅，听感就是网页版那种短促敲击）。
# pygame.mixer 使用 16 个音效声道，另留 2 个专用声道播放语音。
import io
import wave

import numpy as np

SAMPLE_RATE = 44100
SOUND_CHANNEL_COUNT = 16
VOICE_MAX_CONCURRENT = 2
VOICE_FADEOUT_MS = 300


def _render_tone(freq, dur, vol=0.5, wave_type="sine"):
    """复刻网页版 beep()：指定波形 + 指数衰减包络"""
    n = max(1, int(SAMPLE_RATE * dur))
    t = np.linspace(0, dur, n, False)
    x = 2 * np.pi * freq * t
    if wave_type == "square":            # 方波：奇次谐波
        data = np.sign(np.sin(x))
    elif wave_type == "triangle":        # 三角波：奇次谐波 1/n²
        data = np.zeros(n)
        for k in range(1, 14, 2):
            data += ((-1) ** ((k - 1) // 2)) * np.sin(k * x) / (k * k)
        data *= 8 / np.pi ** 2
    else:                                # sine
        data = np.sin(x)
    # 网页版包络：gain=vol 起，指数衰减到 0.0001（ decay = ln(10000)/dur ）
    data *= np.exp(-9.2103404 / dur * t) * vol
    return (np.clip(data, -1, 1) * 32767).astype(np.int16)


def _wav_bytes(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def _build_sounds():
    """预生成全部音效 WAV——参数与网页版逐一对应"""
    gap = np.zeros(int(SAMPLE_RATE * 0.02), dtype=np.int16)   # 网页版 setTimeout 90ms 的间隙
    return {
        # 摸头：sine 520~680Hz 随机音高、0.09s（网页版同款短促“敲脑袋”）
        "pat0": _wav_bytes(_render_tone(523.25, 0.09, 0.55)),   # C5
        "pat1": _wav_bytes(_render_tone(554.37, 0.09, 0.55)),   # C#5
        "pat2": _wav_bytes(_render_tone(587.33, 0.09, 0.55)),   # D5
        "pat3": _wav_bytes(_render_tone(622.25, 0.09, 0.55)),   # D#5
        "pat4": _wav_bytes(_render_tone(659.25, 0.09, 0.55)),   # E5
        "pat5": _wav_bytes(_render_tone(679.00, 0.09, 0.55)),
        # 投喂：方波两连音 300Hz(0.07s) → 240Hz(0.09s)
        "feed": _wav_bytes(np.concatenate([
            _render_tone(300.0, 0.07, 0.50, "square"),
            gap,
            _render_tone(240.0, 0.09, 0.50, "square"),
        ])),
        # 聊聊：三角波 660Hz 0.07s
        "chat": _wav_bytes(_render_tone(660.0, 0.07, 0.50, "triangle")),
        # 点击/唤回：sine 440Hz 0.06s
        "pop": _wav_bytes(_render_tone(440.0, 0.06, 0.50)),
    }


_SOUNDS = None
_MIXER_OK = False
_voice_channels = []


def init_sounds():
    """初始化 pygame 混音器并加载全部音效（主线程调用一次）"""
    global _SOUNDS, _MIXER_OK, _voice_channels
    if _SOUNDS is not None:
        return _SOUNDS
    _SOUNDS = {}
    try:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
        pygame.mixer.set_num_channels(SOUND_CHANNEL_COUNT + VOICE_MAX_CONCURRENT)
        pygame.mixer.set_reserved(VOICE_MAX_CONCURRENT)
        _voice_channels = [pygame.mixer.Channel(i) for i in range(VOICE_MAX_CONCURRENT)]
        for key, data in _build_sounds().items():
            snd = pygame.mixer.Sound(file=io.BytesIO(data))
            snd.set_volume(0.5)
            _SOUNDS[key] = snd
        _MIXER_OK = True
    except Exception as e:
        print("音效初始化失败（将静音运行）:", e, flush=True)
        _SOUNDS = {}
        _MIXER_OK = False
        _voice_channels = []
    return _SOUNDS


def play_sound(name):
    """播放指定音效；mixer 自动分配空闲声道，不覆盖、不丢弃"""
    if not _MIXER_OK:
        return
    snd = _SOUNDS.get(name)
    if snd is None:
        return
    try:
        snd.play()
    except Exception:
        pass


def play_voice(sound):
    """最多同时播放两段语音，新语音开始时淡出上一段。"""
    if not _MIXER_OK or not _voice_channels:
        return
    try:
        # 优先使用空闲声道；两个声道都在播放时，停止最早的一段。
        channel = next((ch for ch in _voice_channels if not ch.get_busy()),
                       _voice_channels[0])
        channel.stop()
        for previous in _voice_channels:
            if previous is not channel and previous.get_busy():
                previous.fadeout(VOICE_FADEOUT_MS)
        channel.play(sound)
        # 按开始播放的先后顺序保存，方便下次找到最早的语音。
        _voice_channels.remove(channel)
        _voice_channels.append(channel)
    except Exception as e:
        print("语音播放失败:", e, flush=True)


def stop_audio():
    """停止正在播放的语音和音效。"""
    if not _MIXER_OK:
        return
    try:
        import pygame
        pygame.mixer.stop()
    except Exception as e:
        print("停止声音失败:", e, flush=True)


# ---------------------------------------------------------------- 语音
# 汐的真人语音（来源：卡拉彼丘WIKI），中/日双语切换，字幕始终为中文
VOICE_DIR = os.path.join(HERE, "voice", "wav")
VOICE_TEXTS = {
    "greet": "老板好，我叫汐，头脑灵活技术全面价格公道，不管你从哪里认识的我，要不要先下单试试我的水平？",
    "hello": "你好",
    "pat": "嘿嘿嘿，老板真有眼光，这趟包你平安",
    "feed": "大好人，谢谢你",
    "happy": "哼，赢了！奖金到手！",
    "sad": "这点佣金我可不玩命，溜了溜了",
    "idle1": "啊，希望今天的工作可以轻松一点",
    "idle2": "早点开打，早点收工",
    "idle3": "哦，我是不是忘记说子弹也算钱？",
    "sleep": "我先飘一会儿",
    "love": "你是我的偶像",
    "yes": "对的对的",
    "no": "不对不对",
}
VOICE_LANGS = ("cn", "jp")

_voices = None
_voice_dur = {}


def load_voices():
    """加载全部语音 WAV 到 pygame（返回 {lang: {key: Sound}}）"""
    global _voices, _voice_dur
    if _voices is not None:
        return _voices
    _voices = {"cn": {}, "jp": {}}
    try:
        import pygame
        import wave as _wave
        for lang in VOICE_LANGS:
            d = os.path.join(VOICE_DIR, lang)
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if not name.endswith(".wav"):
                    continue
                key = name[:-4]
                path = os.path.join(d, name)
                snd = pygame.mixer.Sound(path)
                snd.set_volume(0.9)
                _voices[lang][key] = snd
                with _wave.open(path) as w:
                    _voice_dur[(lang, key)] = w.getnframes() / w.getframerate()
    except Exception as e:
        print("语音加载失败（将无声运行）:", e, flush=True)
        _voices = {"cn": {}, "jp": {}}
    return _voices


# ---------------------------------------------------------------- 气泡
class BubbleWidget(QWidget):
    """打字机效果的气泡（圆角框 + 小尾巴）"""

    def __init__(self, parent):
        super().__init__(parent)
        self.full = ""
        self.shown = 0
        self._max_text_w = 240
        self._font_px = 14
        self._font = text_font(14)
        self.setFont(self._font)
        self.hide()
        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._tick)
        # 持久化的隐藏定时器：每次 say 重置，避免旧定时器提前藏起新气泡
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._check_hide)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def say(self, text, hold_ms=2600):
        self.full = text
        self.shown = 0
        self.adjust_size()
        self.show()
        self.raise_()
        self._type_timer.start(45)
        self._hide_timer.start(hold_ms + 120)

    def _check_hide(self):
        if self.shown >= len(self.full):
            self.hide()

    def _tick(self):
        self.shown += 1
        if self.shown >= len(self.full):
            self._type_timer.stop()
        self.adjust_size()
        self.update()

    def set_scale(self, s, avail_w=None):
        # 气泡宽度只需避开右上角关闭按钮
        cap = 280
        if avail_w:
            cap = min(cap, avail_w - 80)
        self._max_text_w = max(110, cap * s - 28)
        self._font_px = max(9, 14 * s)
        # 注意：必须把字体保存为实例属性再用 QFontMetrics，
        # 直接 QFontMetrics(self.font) 会因 Qt 字体对象所有权问题导致堆损坏崩溃
        self._font = text_font(self._font_px)
        self.setFont(self._font)

    def _lines(self):
        fm = QFontMetrics(self._font)
        lines, cur = [], ""
        for ch in self.full[:self.shown]:
            if fm.horizontalAdvance(cur + ch) > self._max_text_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur if cur else " ")
        return fm, lines

    def adjust_size(self):
        if not self.full:
            self.hide()
            return
        fm, lines = self._lines()
        w = max(fm.horizontalAdvance(l) for l in lines) + 28
        h = len(lines) * (self._font_px + 5) + 18 + 8  # +尾巴
        self.setFixedSize(max(int(w), 40), int(h))

    def paintEvent(self, e):
        if not self.full:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        tail_h = 8
        box = QRectF(1, 1, w - 2, h - tail_h - 2)
        # 主体
        p.setPen(QPen(CYAN, 2))
        p.setBrush(QBrush(QColor(255, 255, 255, 242)))
        p.drawRoundedRect(box, 12, 12)
        # 尾巴
        cx = w / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 242)))
        p.drawPolygon(QPoint(int(cx - 7), int(box.bottom())),
                      QPoint(int(cx + 7), int(box.bottom())),
                      QPoint(int(cx), h - 1))
        p.setPen(QPen(CYAN, 2))
        p.drawLine(int(cx - 7), int(box.bottom()), int(cx), h - 2)
        p.drawLine(int(cx + 7), int(box.bottom()), int(cx), h - 2)
        # 文字
        fm, lines = self._lines()
        p.setPen(QPen(INK))
        y = 10 + self._font_px
        for l in lines:
            p.drawText(QPoint(14, int(y)), l)
            y += self._font_px + 5
        # 打字光标
        if self._type_timer.isActive() and lines:
            last = lines[-1]
            x = 14 + fm.horizontalAdvance(last) + 2
            p.setPen(QPen(CYAN))
            p.drawText(QPoint(int(x), int(y - 5)), "|")


# ---------------------------------------------------------------- 状态条
class MeterWidget(QWidget):
    def __init__(self, icon, c1, c2, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.c1, self.c2 = c1, c2
        self.value = 1.0
        self._s = 1.0
        self.setFont(emoji_font(12))

    def set_scale(self, s):
        self._s = s
        self.setFont(emoji_font(12 * s))
        self.setFixedSize(int(52 * s), int(16 * s))

    def set_value(self, v):
        self.value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self._s
        icon_s = 13 * s
        bar_h = 6 * s
        bar_w = 34 * s
        y = (self.height() - bar_h) / 2
        p.setFont(emoji_font(12 * s))
        p.setPen(QPen(INK))
        p.drawText(QRectF(0, (self.height() - icon_s) / 2, icon_s, icon_s),
                   Qt.AlignCenter, self.icon)
        bar = QRectF(icon_s + 2 * s, y, bar_w, bar_h)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(34, 48, 79, 38)))
        p.drawRoundedRect(bar, bar_h / 2, bar_h / 2)
        fw = bar.width() * self.value
        if fw > 0.5:
            grad = QLinearGradient(bar.left(), 0, bar.right(), 0)
            grad.setColorAt(0, self.c1)
            grad.setColorAt(1, self.c2)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), fw, bar.height()),
                              bar_h / 2, bar_h / 2)


# ---------------------------------------------------------------- 主窗口
IDLE_UI_OPACITY = 0.55      # 鼠标不在桌宠上时，底部栏/关闭按钮的半虚化透明度


class PetWindow(QWidget):

    def __init__(self):
        super().__init__()
        ensure_sad_pixmap()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.resize(BASE_W, BASE_H)

        # 图片
        self.pix_normal = QPixmap(IMG)
        self.pix_sad = QPixmap(IMG_SAD) if os.path.exists(IMG_SAD) else self.pix_normal
        self.pet_scale = 1.0
        self._pix_cache = (1.0, None, None)

        # 状态
        self.fullness = 78.0
        self.mood = 82.0
        self.sound_on = True
        self.asleep = False
        self.pet_state = "idle"          # idle/patting/happy/eating/thinking/asleep
        self.state_start = 0
        self.patting = False
        self.pat_start = 0
        self.feed_cd = False
        self.chat_open = False
        self.particles = []
        self.food = None
        self._last_frame = 0
        self._dragging = False
        self._drag_moved = False
        self._drag_offset = QPoint()
        self._mouse_pos = QPoint(-100, -100)
        self._hover_ui = False

        self.clock = QElapsedTimer()
        self.clock.start()
        self.interact_clock = QElapsedTimer()
        self.interact_clock.start()

        init_sounds()   # 预热音效（需主线程）
        self.voice_lang = "cn"
        load_voices()   # 预载汐的真人语音

        self._build_ui()
        self.relayout()

        # 渲染循环（60fps，驱动全部动画与粒子）
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update)
        self.render_timer.start(16)

        # 逻辑定时器
        QTimer.singleShot(800, self._greet)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._idle_chatter)
        self.idle_timer.start(9000)
        self.hunger_timer = QTimer(self)
        self.hunger_timer.timeout.connect(self._hunger_tick)
        self.hunger_timer.start(9000)
        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self._sleep_check)
        self.sleep_timer.start(5000)
        self._pat_heart_timer = QTimer(self)
        self._pat_heart_timer.timeout.connect(self._pat_heart_tick)

    # ---------------- 音效 ----------------
    def _beep(self, kind="pop"):
        """播放音效（互不打断、完整播完）；kind: pat/feed/chat/pop"""
        if not self.sound_on:
            return
        if kind == "pat":
            play_sound("pat%d" % random.randint(0, 5))   # 网页版同款随机音高
        else:
            play_sound(kind)

    def say_voice(self, key):
        """播放当前语言的语音，并显示中文字幕"""
        if self.sound_on:
            snd = load_voices().get(self.voice_lang, {}).get(key)
            if snd is not None:
                play_voice(snd)
        text = VOICE_TEXTS.get(key)
        if text:
            hold = int(_voice_dur.get((self.voice_lang, key), 2.0) * 1000) + 400
            self.bubble.say(text, max(hold, 1500))

    def _say_or_voice(self, voice_key, text_lines, voice_prob=0.5):
        """随机：一半概率播真人语音（中文字幕），一半显示普通文字台词"""
        if random.random() < voice_prob:
            self.say_voice(voice_key)
        else:
            self.bubble.say(pick(text_lines))

    # ---------------- UI ----------------
    def _shadow(self, color, blur=12, y_off=4, alpha=90):
        """按钮投影（网页版 box-shadow 效果）"""
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(blur)
        eff.setColor(QColor(color.red(), color.green(), color.blue(), alpha))
        eff.setOffset(0, y_off)
        return eff

    def _apply_btn_style(self):
        """网页版按钮风格：135deg 渐变胶囊 + 投影 + 悬停上浮（圆润饱满）"""
        s = self.pet_scale
        fs = max(9, int(12 * s))
        pad = max(5, int(7 * s))
        padx = max(9, int(13 * s))
        cyan_style = """
            QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #2ec4d9,stop:1 #0e9bb5);
                        color:white;border:none;border-radius:999px;
                        padding:%dpx %dpx;font-size:%dpx;font-family:"Microsoft YaHei";}
            QPushButton:hover{margin-top:-2px;margin-bottom:2px;}
            QPushButton:pressed{margin-top:1px;margin-bottom:-1px;}
            QPushButton:disabled{color:rgba(255,255,255,120);}
        """ % (pad, padx, fs)
        coral_style = cyan_style.replace("#2ec4d9", "#f4826f").replace("#0e9bb5", "#f0705f")
        ghost_style = """
            QPushButton{background:rgba(255,255,255,225);color:#3a4763;
                        border:none;border-radius:999px;
                        padding:%dpx %dpx;font-size:%dpx;font-family:"Microsoft YaHei";}
            QPushButton:hover{margin-top:-2px;margin-bottom:2px;}
            QPushButton:pressed{margin-top:1px;margin-bottom:-1px;}
        """ % (pad, max(8, int(11 * s)), fs)
        self.btn_pat.setStyleSheet(coral_style)
        self.btn_feed.setStyleSheet(cyan_style)
        self.btn_chat.setStyleSheet(cyan_style)
        self.btn_sound.setStyleSheet(ghost_style)
        self.btn_lang.setStyleSheet(ghost_style)
        # 投影（网页版 box-shadow）
        self.btn_pat.setGraphicsEffect(self._shadow(CORAL, 12 * s, 4 * s, 100))
        self.btn_feed.setGraphicsEffect(self._shadow(CYAN_DEEP, 12 * s, 4 * s, 100))
        self.btn_chat.setGraphicsEffect(self._shadow(CYAN_DEEP, 12 * s, 4 * s, 100))
        self.btn_sound.setGraphicsEffect(self._shadow(INK, 10 * s, 3 * s, 45))
        self.btn_lang.setGraphicsEffect(self._shadow(INK, 10 * s, 3 * s, 45))
        # 悬停时投影加深+抬升（网页版 hover 手感）
        self._btn_shadows = {
            self.btn_pat: (CORAL, 12 * s, 4 * s, 100),
            self.btn_feed: (CYAN_DEEP, 12 * s, 4 * s, 100),
            self.btn_chat: (CYAN_DEEP, 12 * s, 4 * s, 100),
            self.btn_sound: (INK, 10 * s, 3 * s, 45),
            self.btn_lang: (INK, 10 * s, 3 * s, 45),
        }
        if not getattr(self, "_btn_filtered", False):
            for b in self._btn_shadows:
                b.installEventFilter(self)
            self._btn_filtered = True

    def eventFilter(self, obj, e):
        """按钮悬停：投影变大变远，模拟网页版 hover 上浮"""
        if e.type() == QEvent.Enter and obj in getattr(self, "_btn_shadows", {}):
            c, blur, y_off, a = self._btn_shadows[obj]
            eff = obj.graphicsEffect()
            if eff:
                eff.setBlurRadius(blur * 1.4)
                eff.setOffset(0, y_off + 3 * self.pet_scale)
        elif e.type() == QEvent.Leave and obj in getattr(self, "_btn_shadows", {}):
            c, blur, y_off, a = self._btn_shadows[obj]
            eff = obj.graphicsEffect()
            if eff:
                eff.setBlurRadius(blur)
                eff.setOffset(0, y_off)
        return super().eventFilter(obj, e)

    def _build_ui(self):
        self.bubble = BubbleWidget(self)

        # 状态条：竖排成组，放在底部栏左侧（网页版底部栏版式）
        self.meter_full = MeterWidget("🍖", QColor("#ffd166"), QColor("#f4a259"), self)
        self.meter_mood = MeterWidget("💗", QColor("#ff8fa3"), QColor("#f0705f"), self)
        self.meter_group = QWidget(self)
        vlay = QVBoxLayout(self.meter_group)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(2)
        vlay.addWidget(self.meter_full)
        vlay.addWidget(self.meter_mood)

        self.btn_pat = QPushButton("🖐️ 摸摸头", self)
        self.btn_pat.setCursor(Qt.PointingHandCursor)
        self.btn_pat.clicked.connect(self._on_pat_click)

        self.btn_feed = QPushButton("🍰 投喂", self)
        self.btn_feed.setCursor(Qt.PointingHandCursor)
        self.btn_feed.clicked.connect(self._on_feed_click)

        self.btn_chat = QPushButton("💬 聊聊", self)
        self.btn_chat.setCursor(Qt.PointingHandCursor)
        self.btn_chat.clicked.connect(self._on_chat_click)

        self.btn_sound = QPushButton("🔊", self)
        self.btn_sound.setCursor(Qt.PointingHandCursor)
        self.btn_sound.clicked.connect(self._on_sound_click)

        self.btn_lang = QPushButton("中", self)
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.clicked.connect(self._on_lang_click)

        # 底部栏：[状态条组][按钮组] 一行排布（网页版底部栏版式）
        self.bottom_bar = QWidget(self)
        lay = QHBoxLayout(self.bottom_bar)
        lay.setContentsMargins(6, 6, 6, 6)      # 给按钮投影留出空间
        lay.setSpacing(6)
        lay.addWidget(self.meter_group)
        lay.addWidget(self.btn_pat)
        lay.addWidget(self.btn_feed)
        lay.addWidget(self.btn_chat)
        lay.addWidget(self.btn_sound)
        lay.addWidget(self.btn_lang)

        # 聊天输入
        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("和汐汐说点什么…")
        self.chat_input.setStyleSheet("""
            QLineEdit{background:white;color:#3a4763;border:2px solid #2ec4d9;
                      border-radius:999px;padding:6px 12px;font-size:13px;
                      font-family:"Microsoft YaHei";selection-background-color:#2ec4d9;}
        """)
        self.chat_input.returnPressed.connect(self._on_chat_submit)
        self.chat_input.hide()

        # 关闭 / 缩放提示 / 唤回
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,190);color:#3a4763;border:none;
                        border-radius:11px;font-size:12px;font-family:"Microsoft YaHei";}
            QPushButton:hover{background:white;color:#f0705f;}
        """)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self._on_close_click)

        self.scale_toast = QLabel("100%", self)
        self.scale_toast.setStyleSheet("""
            QLabel{background:rgba(34,48,79,200);color:white;border-radius:999px;
                   padding:3px 10px;font-size:11px;font-family:"Microsoft YaHei";}
        """)
        self.scale_toast.hide()
        self._toast_timer = QTimer(self)
        self._toast_timer.timeout.connect(self.scale_toast.hide)

        self.btn_recall = QPushButton("✨ 唤回汐汐", self)
        self.btn_recall.setStyleSheet("""
            QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #f4826f,stop:1 #f0705f);
                        color:white;border:none;border-radius:999px;
                        padding:8px 16px;font-size:13px;font-family:"Microsoft YaHei";}
        """)
        self.btn_recall.setGraphicsEffect(self._shadow(CORAL, 12, 4, 100))
        self.btn_recall.setCursor(Qt.PointingHandCursor)
        self.btn_recall.clicked.connect(self._on_recall_click)
        self.btn_recall.hide()

        # 半虚化效果：鼠标不在桌宠上时，底部栏与关闭按钮变淡（网页版设计）
        self.bar_fx = QGraphicsOpacityEffect(self.bottom_bar)
        self.bar_fx.setOpacity(IDLE_UI_OPACITY)
        self.bottom_bar.setGraphicsEffect(self.bar_fx)
        self.bar_anim = QPropertyAnimation(self.bar_fx, b"opacity", self)
        self.bar_anim.setDuration(200)
        self.close_fx = QGraphicsOpacityEffect(self.btn_close)
        self.close_fx.setOpacity(IDLE_UI_OPACITY)
        self.btn_close.setGraphicsEffect(self.close_fx)
        self.close_anim = QPropertyAnimation(self.close_fx, b"opacity", self)
        self.close_anim.setDuration(200)

        self._apply_btn_style()
        self._build_voice_menu()

    def _fade_ui(self, show):
        """悬停时 1.0，移开后半虚化 0.55（网页版 opacity 过渡）"""
        target = 1.0 if show else IDLE_UI_OPACITY
        for fx, anim in ((self.bar_fx, self.bar_anim), (self.close_fx, self.close_anim)):
            anim.stop()
            anim.setStartValue(fx.opacity())
            anim.setEndValue(target)
            anim.start()

    def enterEvent(self, e):
        self._hover_ui = True
        self._fade_ui(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_ui = False
        self._mouse_pos = QPoint(-100, -100)
        self._fade_ui(False)
        super().leaveEvent(e)

    def relayout(self):
        s = self.pet_scale
        w, h = self.width(), self.height()
        # 按钮风格随缩放刷新（网页版尺寸）
        self._apply_btn_style()
        # 底部栏（状态条组 + 按钮组）
        self.meter_full.set_scale(s)
        self.meter_mood.set_scale(s)
        m = max(4, int(6 * s))
        self.bottom_bar.layout().setContentsMargins(m, m, m, m)
        self.bottom_bar.adjustSize()
        bw = self.bottom_bar.width()
        self.bottom_bar.move(int((w - bw) / 2), int(h - 12 * s - self.bottom_bar.height()))
        # 聊天输入（底部栏上方）
        iw = int(210 * s)
        self.chat_input.setFixedSize(iw, max(26, int(32 * s)))
        ih = self.chat_input.height()
        self.chat_input.move(int((w - iw) / 2),
                             int(h - 12 * s - self.bottom_bar.height() - 6 * s - ih))
        # 关闭按钮（按需求下移）与缩放提示
        cs = max(18, int(22 * s))
        self.btn_close.setFixedSize(cs, cs)
        close_y = int((8 + CLOSE_EXTRA_Y) * s)
        self.btn_close.move(int(w - 8 * s - cs), close_y)
        self.scale_toast.move(int(w - 8 * s - 60 * s), close_y + cs + int(4 * s))
        self.scale_toast.setFont(text_font(max(9, int(11 * s))))
        # 唤回按钮
        self.btn_recall.move(int((w - self.btn_recall.width()) / 2), int(h / 2))
        # 气泡宽度与位置
        self.bubble.set_scale(s, self.width())
        self._position_bubble()

    # ---------------- 几何 ----------------
    def pet_rect(self):
        w = PET_BASE_W * self.pet_scale
        h = w * self.pix_normal.height() / self.pix_normal.width()
        x = (self.width() - w) / 2
        bottom_off = max(56, 64 * self.pet_scale)
        y = self.height() - bottom_off - h
        return QRectF(x, y, w, h)

    def head_rect(self):
        r = self.pet_rect()
        return QRectF(r.x() + r.width() * 0.21, r.y() + r.height() * 0.03,
                      r.width() * 0.58, r.height() * 0.20)

    def mouth_pos(self):
        r = self.pet_rect()
        return r.center().x(), r.y() + r.height() * 0.45

    def current_pixmap(self):
        sad = (self.fullness < 25 or self.mood < 25) and not self.patting
        base = self.pix_sad if sad else self.pix_normal
        if self._pix_cache[0] != self.pet_scale or self._pix_cache[1] is not base:
            r = self.pet_rect()
            scaled = base.scaledToWidth(max(1, int(r.width())),
                                        Qt.SmoothTransformation)
            self._pix_cache = (self.pet_scale, base, scaled)
        return self._pix_cache[2]

    # ---------------- 变换 ----------------
    def pet_transform(self):
        now = self.clock.elapsed()
        sx, sy, rot, dx, dy = 1.0, 1.0, 0.0, 0.0, 0.0
        st = self.pet_state
        if st == "patting":
            # 复刻网页版 CSS：squish .5s ease-in-out infinite alternate
            # 关键：相位从每次摸头重新起算 → 连点脑袋就是一下一下的“敲脑袋”Boing
            u = ((now - self.pat_start) % 1000) / 1000.0
            k = (1 - math.cos(2 * math.pi * u)) / 2      # 平滑 0→1→0（ease-in-out 感）
            sx = 1.03 - 0.045 * k                        # from scale(1.03,.94)
            sy = 0.94 + 0.09 * k                         # to   scale(.985,1.03)
            rot = -1.2 + 2.4 * k                         # rotate -1.2° → 1.2°
        elif st == "happy":
            prog = (now - self.state_start) / 500.0
            if prog >= 1:
                self._set_state("idle")
            else:
                dy = -26 * math.sin(math.pi * prog)
                k = math.sin(math.pi * prog)
                sx, sy = 1 + 0.05 * k, 1 - 0.05 * k
        elif st == "eating":
            # 复刻网页版 CSS：chomp .22s ease-in-out 4（4 次咀嚼）
            u = ((now - self.state_start) % 220) / 220.0
            k = (1 - math.cos(2 * math.pi * u)) / 2
            sy = 1 - 0.05 * k                            # 50% 时 scale(1.02,.97)
            dy = 2 * k                                   # translateY(2px)
        elif st == "thinking":
            ph = math.sin(now / 600.0)
            rot = -4 * ph
            dx = -4 * (ph + 1) / 2
        elif st == "asleep":
            ph = math.sin(now / 2000.0)
            rot = 1.5 * ph
            dy = 4 + ph
        else:  # idle
            ph = math.sin(now / 1600.0)
            dy = 7 * ph
            sy = 1 + 0.015 * math.sin(now / 1600.0 + math.pi / 2)
        return sx, sy, rot, dx, dy

    def _set_state(self, st, duration=0):
        self.pet_state = st
        self.state_start = self.clock.elapsed()
        if duration:
            QTimer.singleShot(duration, self._state_timeout)

    def _state_timeout(self):
        if self.pet_state in ("happy", "eating", "thinking"):
            self._set_state("idle")

    # ---------------- 绘制 ----------------
    def _position_bubble(self, cur_dy=0.0):
        """气泡贴在人物头顶上方，并跟随呼吸/挤压的纵向位移（像桌宠在说话）"""
        if not self.bubble.isVisible():
            return
        r = self.pet_rect()
        bw, bh = self.bubble.width(), self.bubble.height()
        x = r.center().x() - bw / 2
        y = r.y() + cur_dy - bh - 6 * self.pet_scale
        y = max(2.0, y)      # 防止超出窗口顶部
        self.bubble.move(int(x), int(y))

    def paintEvent(self, e):
        now = self.clock.elapsed()
        dt = min(0.05, (now - self._last_frame) / 1000.0) if self._last_frame else 0.016
        self._last_frame = now
        self._update_particles(dt)
        self._update_food(now)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        # 脚下柔和投影（增强桌面悬浮感）
        r = self.pet_rect()
        shadow = QRadialGradient(r.center().x(), r.bottom() - 6 * self.pet_scale,
                                 r.width() * 0.42)
        shadow.setColorAt(0, QColor(34, 48, 79, 46))
        shadow.setColorAt(0.6, QColor(34, 48, 79, 18))
        shadow.setColorAt(1, QColor(34, 48, 79, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(QRectF(r.center().x() - r.width() * 0.42, r.bottom() - 30 * self.pet_scale,
                             r.width() * 0.84, 34 * self.pet_scale))

        # 人物
        pix = self.current_pixmap()
        sx, sy, rot, dx, dy = self.pet_transform()
        # 气泡跟随人物当前位置（在头顶上方浮动）
        self._position_bubble(dy)
        p.save()
        p.translate(r.center())
        p.scale(sx, sy)
        p.rotate(rot)
        p.translate(dx, dy)
        p.drawPixmap(QRectF(-r.width() / 2, -r.height() / 2, r.width(), r.height()),
                     pix, QRectF(pix.rect()))
        p.restore()

        # 摸头热区悬停提示（网页版 #head-zone:hover 的柔光）
        if not self.patting and self.head_rect().contains(self._mouse_pos):
            hr = self.head_rect()
            glow = QRadialGradient(hr.center(), hr.width() * 0.6)
            glow.setColorAt(0, QColor(46, 196, 217, 46))
            glow.setColorAt(1, QColor(46, 196, 217, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(hr)

        # 食物
        if self.food:
            p.setFont(emoji_font(26 * self.pet_scale))
            p.setPen(QPen(QColor(34, 48, 79, 60)))
            p.drawText(QPointF(self.food["x"] + 2, self.food["y"] + 2), self.food["char"])
            p.setPen(QPen(INK))
            p.drawText(QPointF(self.food["x"], self.food["y"]), self.food["char"])

        # 粒子
        for pt in self.particles:
            alpha = int(255 * (1 - pt["life"] / pt["ttl"]))
            if alpha <= 0:
                continue
            c = QColor(58, 71, 99, alpha)
            p.setFont(emoji_font(pt["size"] * (0.6 + 0.4 * (1 - pt["life"] / pt["ttl"]))))
            p.setPen(QPen(c))
            p.drawText(QPointF(pt["x"], pt["y"]), pt["text"])

    # ---------------- 粒子 ----------------
    def _spawn_particle(self, text, x, y, size=18):
        self.particles.append({
            "text": text, "x": x, "y": y,
            "vx": random.uniform(-14, 14), "vy": random.uniform(-52, -30),
            "life": 0.0, "ttl": random.uniform(0.9, 1.2), "size": size,
        })

    def _update_particles(self, dt):
        alive = []
        for pt in self.particles:
            pt["life"] += dt
            if pt["life"] >= pt["ttl"]:
                continue
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
            pt["vy"] *= 0.985
            alive.append(pt)
        self.particles = alive

    def spawn_hearts(self, n):
        for i in range(n):
            QTimer.singleShot(i * 110, lambda: self._spawn_particle(
                pick(HEARTS),
                self.width() / 2 + random.uniform(-45, 45),
                self.pet_rect().y() + random.uniform(10, 50),
                16 * self.pet_scale))

    def spawn_crumbs(self):
        mx, my = self.mouth_pos()
        for _ in range(8):
            self._spawn_particle(pick(CRUMBS),
                                 mx + random.uniform(-25, 25), my + random.uniform(-10, 10),
                                 12 * self.pet_scale)

    def spawn_zzz(self):
        self._spawn_particle("💤", self.width() / 2 + 70 * self.pet_scale,
                             self.pet_rect().y() + 30, 20 * self.pet_scale)

    # ---------------- 食物 ----------------
    def _update_food(self, now):
        if not self.food:
            return
        f = self.food
        t = (now - f["t0"]) / 500.0
        if t >= 1:
            self.food = None
            self._on_food_arrive()
        else:
            ease = t * t  # 加速下落
            f["y"] = f["y0"] + (f["y1"] - f["y0"]) * ease

    def _on_food_arrive(self):
        self.spawn_crumbs()
        self._set_state("eating", 900)
        # 音效只在点击投喂时响一次（与网页版一致），此处只做视觉反馈
        if self.fullness > 86:
            self.mood = min(100, self.mood + 6)
            self._say_or_voice("happy", LINES["feedFull"])
        else:
            self.fullness = min(100, self.fullness + 34)
            self.mood = min(100, self.mood + 9)
            self._say_or_voice("feed", LINES["feed"])
        self.update_meters()

    # ---------------- 互动 ----------------
    def _mark_interact(self):
        self.interact_clock.restart()

    def wake_if_asleep(self):
        if self.asleep:
            self.asleep = False
            self._set_state("idle")
            self._say_or_voice("hello", LINES["wake"])

    def start_pat(self):
        if self.patting:
            return
        self.patting = True
        self.pat_start = self.clock.elapsed()
        self._mark_interact()
        self.wake_if_asleep()
        self._set_state("patting")
        self._beep("pat")
        self.spawn_hearts(2)
        self._pat_heart_timer.start(260)

    def _pat_heart_tick(self):
        if self.patting:
            self.spawn_hearts(1)

    def end_pat(self):
        if not self.patting:
            return
        self.patting = False
        self._pat_heart_timer.stop()
        dur = self.clock.elapsed() - self.pat_start
        self.mood = min(100, self.mood + min(12, dur / 120.0))
        if dur > 1100:
            self._say_or_voice("pat", LINES["patLong"])
            self.spawn_hearts(4)
        else:
            self.bubble.say(pick(LINES["patLight"]), 1800)
            self.spawn_hearts(2)
        self._set_state("idle")
        self.update_meters()

    def feed(self):
        if self.feed_cd:
            return
        self.feed_cd = True
        self._mark_interact()
        self.wake_if_asleep()
        self._beep("feed")
        mx, my = self.mouth_pos()
        self.food = {"char": pick(FOODS), "x": mx - 13 * self.pet_scale,
                     "y0": -40.0, "y1": my - 20 * self.pet_scale, "t0": self.clock.elapsed()}
        QTimer.singleShot(1150, self._feed_cd_done)

    def _feed_cd_done(self):
        self.feed_cd = False

    def reply(self, text):
        self._mark_interact()
        self.wake_if_asleep()
        self._beep("chat")
        self._set_state("thinking", 650)
        self.bubble.say("……", 900)

        def answer():
            if "对吗" in text:
                self.say_voice(pick(["yes", "no"]))
                return
            voice = None
            line = None
            if any(k in text for k in ("吃", "饿", "饭", "食", "粮", "鱼", "蛋糕", "零食")):
                line = pick(LINES["chatFood"])
            elif any(k in text for k in ("头", "摸", "rua", "头发", "帽子")):
                line = pick(LINES["chatPat"])
            elif any(k in text for k in ("名字", "是谁", "叫什么")):
                line = pick(LINES["chatName"])
            elif any(k in text for k in ("喜欢", "爱", "老婆", "贴贴", "亲")):
                if random.random() < 0.5:
                    voice = "love"
                else:
                    line = pick(LINES["chatLike"])
                self.mood = min(100, self.mood + 7)
            elif any(k in text for k in ("心情", "开心", "高兴", "怎么样", "好吗")):
                line = pick(LINES["chatMood"])
            elif any(k in text for k in ("再见", "拜拜", "晚安", "走了", "bye")):
                line = pick(LINES["chatBye"])
            elif any(k in text for k in ("你好", "嗨", "hi", "hello", "早", "晚上好")):
                line = pick(LINES["greet"])
            elif self.fullness < 28:
                line = pick(LINES["hungry"])
            else:
                line = pick(LINES["idle"])
            if voice:
                self.say_voice(voice)
            else:
                self.bubble.say(line)
            self.mood = min(100, self.mood + 2)
            self.update_meters()

        QTimer.singleShot(650, answer)

    def say_hello(self):
        self._mark_interact()
        self._beep("pop")
        self._say_or_voice("hello", LINES["greet"])
        self.mood = min(100, self.mood + 3)
        self.update_meters()

    def update_meters(self):
        self.meter_full.set_value(self.fullness / 100.0)
        self.meter_mood.set_value(self.mood / 100.0)

    # ---------------- 定时逻辑 ----------------
    def _greet(self):
        self.say_voice("greet")

    def _idle_chatter(self):
        if self.asleep or self.patting or self.chat_open:
            return
        if self.interact_clock.elapsed() < 9000:
            return
        if random.random() < 0.5:
            if self.fullness < 30:
                self._say_or_voice("sad", LINES["idleHungry"])
            else:
                self._say_or_voice(pick(["idle1", "idle2", "idle3"]), LINES["idle"])
            self._mark_interact()

    def _hunger_tick(self):
        self.fullness = max(0, self.fullness - 1.6)
        self.mood = max(0, self.mood - 0.8)
        if self.fullness < 25 and not self.asleep and random.random() < 0.35:
            self._say_or_voice("sad", LINES["hungry"])
            self._mark_interact()
        self.update_meters()

    def _sleep_check(self):
        if self.interact_clock.elapsed() > 75000 and not self.asleep:
            self.asleep = True
            self._set_state("asleep")
            self._say_or_voice("sleep", LINES["sleep"])
        if self.asleep:
            self.spawn_zzz()

    # ---------------- 按钮 ----------------
    def _on_pat_click(self):
        self.start_pat()
        QTimer.singleShot(900, self.end_pat)

    def _on_feed_click(self):
        self.feed()

    def _on_chat_click(self):
        self._mark_interact()
        self.wake_if_asleep()
        self.chat_open = not self.chat_open
        if self.chat_open:
            self.chat_input.show()
            self.chat_input.setFocus()
        else:
            self.chat_input.hide()

    def _on_chat_submit(self):
        text = self.chat_input.text().strip()
        self.chat_input.clear()
        if text:
            self.reply(text)

    def _build_voice_menu(self):
        from PyQt5.QtWidgets import QMenu
        self.voice_menu = QMenu(self)
        self.voice_menu.setStyleSheet("""
            QMenu{background:#ffffff;border:1px solid #2ec4d9;border-radius:10px;padding:6px;}
            QMenu::item{font-family:"Microsoft YaHei";font-size:13px;color:#3a4763;padding:6px 22px;border-radius:6px;}
            QMenu::item:selected{background:#e8f7fa;color:#0e9bb5;}
        """)
        items = [
            ("greet", "自我介绍"),
            ("hello", "你好"),
            ("pat", "老板真有眼光"),
            ("feed", "大好人，谢谢你"),
            ("happy", "奖金到手"),
            ("sad", "溜了溜了"),
            ("idle1", "闲聊·希望工作轻松点"),
            ("idle2", "闲聊·早点收工"),
            ("idle3", "闲聊·子弹也算钱"),
            ("sleep", "我先飘一会儿"),
            ("yes", "对的对的"),
            ("no", "不对不对"),
            ("love", "你是我的偶像"),
        ]
        for key, label in items:
            act = self.voice_menu.addAction(label)
            act.triggered.connect(lambda checked=False, k=key: self.say_voice(k))

    def _on_lang_click(self):
        self.voice_lang = "jp" if self.voice_lang == "cn" else "cn"
        self.btn_lang.setText("日" if self.voice_lang == "jp" else "中")
        self._mark_interact()
        self.say_voice("hello")   # 用新语言打声招呼，字幕仍是中文

    def _on_sound_click(self):
        self.sound_on = not self.sound_on
        self.btn_sound.setText("🔊" if self.sound_on else "🔇")
        if self.sound_on:
            self._beep("pop")
        else:
            stop_audio()
        self.bubble.say("（打开声音）" if self.sound_on else "（静音模式）", 1800)

    def _on_close_click(self):
        self._mark_interact()
        self.bubble.say(pick(LINES["closeBye"]), 2200)
        self._beep("pop")
        QTimer.singleShot(1400, self._fade_out)

    def _fade_out(self):
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(500)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._after_fade_out)
        self._fade.start()

    def _after_fade_out(self):
        self.hide()
        self.setWindowOpacity(1.0)
        self.btn_recall.show()
        self.btn_recall.raise_()

    def _on_recall_click(self):
        self.btn_recall.hide()
        self.show()
        self.raise_()
        self._beep("pop")
        self._mark_interact()
        QTimer.singleShot(300, lambda: self.bubble.say("汐汐回来啦！", 2000))

    # ---------------- 缩放 ----------------
    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        if delta == 0:
            e.ignore()
            return
        e.accept()
        self._mark_interact()
        self.wake_if_asleep()
        self.set_scale(self.pet_scale + (0.08 if delta > 0 else -0.08))

    def set_scale(self, s):
        s = round(max(0.5, min(2.0, s)) * 100) / 100.0
        if abs(s - self.pet_scale) < 0.001:
            return
        self.pet_scale = s
        self._pix_cache = (-1, None, None)      # 缓存失效
        self.resize(int(BASE_W * s), int(BASE_H * s))   # 原生 resize，丝滑
        self.relayout()
        self.scale_toast.setText("%d%%" % int(s * 100))
        self.scale_toast.show()
        self._toast_timer.start(900)

    # ---------------- 鼠标（原生拖动） ----------------
    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self._mark_interact()
            self.voice_menu.exec_(e.globalPos())
            e.accept()
            return
        if e.button() == Qt.LeftButton:
            if self.head_rect().contains(e.pos()):
                self.start_pat()
                e.accept()
                return
            self._dragging = True
            self._drag_moved = False
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            self._mark_interact()
            e.accept()

    def mouseMoveEvent(self, e):
        self._mouse_pos = e.pos()
        if self._dragging:
            if e.globalPos() != self._drag_offset:
                self._drag_moved = True
            self.move(e.globalPos() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.patting:
                self.end_pat()
            if self._dragging:
                self._dragging = False
                if not self._drag_moved:
                    self.say_hello()
            e.accept()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = PetWindow()
    geo = app.primaryScreen().availableGeometry()
    pet.move(geo.right() - pet.width() - 40, geo.bottom() - pet.height() - 60)
    pet.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
