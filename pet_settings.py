# -*- coding: utf-8 -*-
"""读取和保存项目目录内的桌宠设置。"""
import json
import math
import os
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(HERE, "pet_settings.json")
DEFAULT_SETTINGS = {
    "position": None,
    "scale": 1.0,
    "voice_lang": "cn",
    "sound_on": True,
}


def load_settings():
    """忽略无效字段，缺少设置文件时使用默认值。"""
    settings = DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        return settings
    except (OSError, ValueError) as e:
        print("读取桌宠设置失败，将使用默认设置:", e, flush=True)
        return settings
    if not isinstance(data, dict):
        print("桌宠设置格式有误，将使用默认设置。", flush=True)
        return settings

    scale = data.get("scale")
    if (isinstance(scale, (int, float)) and not isinstance(scale, bool)
            and (isinstance(scale, int) or math.isfinite(scale))):
        settings["scale"] = round(max(0.5, min(2.0, scale)), 2)
    if data.get("voice_lang") in ("cn", "jp"):
        settings["voice_lang"] = data["voice_lang"]
    if isinstance(data.get("sound_on"), bool):
        settings["sound_on"] = data["sound_on"]
    position = data.get("position")
    if isinstance(position, dict) and all(
            isinstance(position.get(axis), int)
            and not isinstance(position[axis], bool)
            and -(2 ** 31) <= position[axis] < 2 ** 31
            for axis in ("x", "y")):
        settings["position"] = {axis: position[axis] for axis in ("x", "y")}
    return settings


def save_settings(settings):
    """写入临时文件后替换设置文件，写入失败时保留原文件。"""
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".pet_settings-", suffix=".tmp", dir=HERE)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")
        os.replace(temp_path, SETTINGS_FILE)
        return True
    except (OSError, TypeError, ValueError) as e:
        print("保存桌宠设置失败:", e, flush=True)
        return False
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
