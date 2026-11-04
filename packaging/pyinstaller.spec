# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller: gera um build onedir (não onefile).

Onedir é necessário aqui porque `catalogo.db` precisa morar como um arquivo
de verdade ao lado do .exe, editável e persistente entre execuções — onefile
extrai tudo para uma pasta temporária a cada execução, o que apagaria/
resetaria o catálogo toda vez.
"""

from pathlib import Path

block_cipher = None

_ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(_ROOT / "run_app.py")],
    pathex=[str(_ROOT)],
    binaries=[],
    datas=[
        (str(_ROOT / "app" / "db" / "schema.sql"), "app/db"),
        (
            str(_ROOT / "app" / "ui" / "assets" / "structdim_perfis_aco.png"),
            "app/ui/assets",
        ),
        (
            str(_ROOT / "app" / "ui" / "assets" / "structdim_logo.png"),
            "app/ui/assets",
        ),
        (
            str(_ROOT / "app" / "ui" / "assets" / "structdim_icon.png"),
            "app/ui/assets",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Dimensionamento",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Dimensionamento",
)
