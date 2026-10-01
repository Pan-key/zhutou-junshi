# -*- mode: python ; coding: utf-8 -*-
"""猪头军师打包定义：全本地版（Laya 判断 + 内置 Ollama 起草）。

onedir 发布包 = 程序 + runtime/（Ollama 运行时）+ models/（qwen2.5:7b + Laya 快照）。
runtime/ 与 models/ 由 tools/make_package.py 生成（几 GB，已 .gitignore），
不在时打包照常进行（产出的是不带头模型的壳，方便先验 UI）。
"""
import os

from PyInstaller.utils.hooks import collect_all

NAME = "猪头军师"
_SPEC_ROOT = os.path.abspath(".")


def _treedir(datas, rel: str):
    """把项目里的目录整棵收进包（不存在就跳过，方便先打壳再补模型）。

    datas 元组是 (source, target_dir)：source 必须传「目录」，PyInstaller 会递归
    展开并保留相对结构（runtime/ → _internal/runtime/…）；如果传单个文件，目标
    路径后会被再拼一层文件名，路径就叠了。
    """
    src = os.path.join(_SPEC_ROOT, rel)
    if os.path.isdir(src):
        datas.append((src, rel))
    return datas


hiddenimports = [
    "app.worker", "app.capture", "app.ocr", "app.fill", "app.overlay", "app.settings",
    "app.version", "app.debugwin",
    "core.engine", "core.draft", "core.jev_client", "core.questions", "core.providers",
    "core.llm", "core.junshi", "core.laya_client", "core.runtime_local",
]
datas, binaries = [], []
# 全内置离线包：随包 Ollama 运行时 + 两个模型目录（tools/make_package.py 生成的）
datas = _treedir(datas, "runtime")
datas = _treedir(datas, "models")
# docs/：程序图标（app/overlay.py 取 docs/icon.ico 当窗口图标）+ 公众号横幅等资源
datas = _treedir(datas, "docs")
# 军师知识库：core/junshi.py 按 _app_root()/goutoujunshi/SKILL.md 读，随包带上才用得上
# （仓库在工程同级目录，不是这个仓库的一部分；没有就跳过，运行时退回内置精简版）
_skill = os.path.join(_SPEC_ROOT, "..", "goutoujunshi", "SKILL.md")
if os.path.isfile(_skill):
    datas.append((os.path.abspath(_skill), "goutoujunshi"))
for pkg in (
    "rapidocr_onnxruntime",
    "onnxruntime",
    "qfluentwidgets",
    "windows_capture",
    "openai",
    "certifi",
    # 本地 Laya 判断依赖
    "laya",
    "torch",
    "transformers",
    "huggingface_hub",
    "tokenizers",
    "safetensors",
):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

excludes = [
    "tkinter", "matplotlib", "scipy", "pandas",
    # torch 不需要的测试目录
    "torch.testing", "torch.distributed",
] + ["PySide6." + m for m in (
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWebEngineQuick", "QtWebChannel",
    "QtMultimedia", "QtMultimediaWidgets", "QtCharts", "QtDataVisualization",
    "QtQuick", "QtQuick3D", "QtQuickControls2", "QtQuickWidgets", "QtQuickTest", "QtQml",
    "QtPdf", "QtPdfWidgets", "QtBluetooth", "QtNfc", "QtSensors", "QtSerialPort",
    "QtTest", "QtDesigner", "QtHelp", "QtRemoteObjects", "QtScxml", "QtStateMachine",
    "QtTextToSpeech", "QtPositioning", "QtLocation", "QtSql",
    "Qt3DCore", "Qt3DRender", "Qt3DInput", "Qt3DLogic", "Qt3DAnimation", "Qt3DExtras",
)]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="docs/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=NAME,
)
