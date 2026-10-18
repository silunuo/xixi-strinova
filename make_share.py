#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键打包「分享版」：
  生成 分享版/汐汐小桌宠/ （只含运行必需文件 + 通用启动器 + 使用说明）
  并压缩为 汐汐小桌宠-分享版.zip

用法：python make_share.py
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SHARE_ROOT = os.path.join(HERE, "分享版")
SHARE = os.path.join(SHARE_ROOT, "汐汐小桌宠")
ZIP_BASE = os.path.join(HERE, "汐汐小桌宠-分享版")

README = '''汐汐小桌宠 · 使用说明
==============================

【第一次使用】
1. 电脑需要安装 Python 3.8 以上版本
   下载：https://www.python.org/downloads/
   安装时务必勾选 "Add Python to PATH"
2. 双击「启动桌宠.bat」
   启动器优先使用项目内 .venv、venv 中的 Python，然后查找 py 和 python。
   缺少依赖时会显示 PowerShell 安装命令，请按提示执行后重新启动。
3. 依赖安装完成后，首次启动会出现在屏幕右下角，之后恢复上次的位置与设置

【玩法】
- 按住脑袋 rua 头 / 按住身体拖动 / 滚轮放大缩小
- 人物支持 50%～200% 缩放，窗口会保留完整按钮栏所需的宽度
- 底部按钮：摸摸头、投喂、聊聊、🔊 音效、中/日 语音切换
- 右键汐汐：选择语音、休息或退出；唤回按钮的右键菜单也能退出
- 语音最多同时播放两段，新语音开始时，上一段会在 300 毫秒内淡出
- 连续触发第三段语音时，会停止最早的一段；静音会停止当前声音
- 聊天里带"对吗"，她会回答"对的对的 / 不对不对"
- 约 75～80 秒没有操作后入睡，自动闲聊不会推迟入睡
- 点右侧小叉让她休息，再点独立的"唤回汐汐"按钮叫她回来
- 休息期间暂停闲聊、状态衰减和渲染
- 选中桌宠或唤回按钮后，按 Alt+F4 可以退出程序
- 位置、缩放、语言和声音开关会保存到项目目录的 pet_settings.json
- 断开副屏或修改分辨率后，会把窗口移回可用屏幕；空间不足时下调缩放比例

【发给别人 / 换电脑】
把整个「汐汐小桌宠」文件夹打包发过去，
对方装好 Python 后双击「启动桌宠.bat」。
缺少依赖时，按启动器提示执行 requirements.txt 的安装命令。
分享包不带原使用者的 pet_settings.json，对方从默认设置开始使用。

【文件说明】
pet_qt.py        主程序
pet_settings.py  读取和保存本机设置
pet_settings.json 运行时生成的本机设置
xixi.png         人物图（透明背景）
xixi_sad.png     难过状态的去饱和图
voice/           汐汐语音（中/日 各 13 段）
启动桌宠.bat     双击启动
requirements.txt 运行依赖清单
使用说明.txt     本文件

【版权】
人物与语音版权归《卡拉彼丘》(Strinova) 原作所有，
仅供个人学习娱乐使用，请勿商用。
'''


def main():
    if os.path.exists(SHARE_ROOT):
        shutil.rmtree(SHARE_ROOT)
    os.makedirs(SHARE)

    # 必需文件
    for name in ("pet_qt.py", "pet_settings.py", "xixi.png", "xixi_sad.png",
                 "启动桌宠.bat", "requirements.txt"):
        shutil.copy(os.path.join(HERE, name), os.path.join(SHARE, name))

    # 语音
    os.makedirs(os.path.join(SHARE, "voice", "wav", "cn"))
    os.makedirs(os.path.join(SHARE, "voice", "wav", "jp"))
    for lang in ("cn", "jp"):
        src = os.path.join(HERE, "voice", "wav", lang)
        dst = os.path.join(SHARE, "voice", "wav", lang)
        for f in os.listdir(src):
            shutil.copy(os.path.join(src, f), os.path.join(dst, f))
    shutil.copy(os.path.join(HERE, "voice", "manifest.json"),
                os.path.join(SHARE, "voice", "manifest.json"))

    # 启动器与依赖清单直接复用项目文件，只在这里生成分享版说明。
    with open(os.path.join(SHARE, "使用说明.txt"), "w", encoding="utf-8-sig") as f:
        f.write(README)

    # 压缩
    zip_path = shutil.make_archive(ZIP_BASE, "zip", SHARE_ROOT, "汐汐小桌宠")
    size = os.path.getsize(zip_path) / 1048576
    print("分享包已生成：%s （%.1f MB）" % (zip_path, size))


if __name__ == "__main__":
    main()
