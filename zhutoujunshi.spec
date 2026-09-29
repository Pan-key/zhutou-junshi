# -*- mode: python ; coding: utf-8 -*-
"""猪头军师打包定义：全本地版（Laya 判断 + OpenAI 兼容起草端点）。"""
from PyInstaller.utils.hooks import collect_all

NAME = "猪头军师"

hiddenimports = [
    "app.worker", "app.capture", "app.ocr", "app.fill", "app.overlay", "app.settings",
    "app.version", "app.update", "app.debugwin",
    "core.engine", "core.draft", "core.jev_client", "core.questions", "core.providers",
    "core.llm", "core.junshi", "core.laya_client",
]
datas, binaries = [], []
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
