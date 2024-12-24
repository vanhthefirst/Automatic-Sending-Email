# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Collect all necessary files
a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Environment files with explicit paths
        ('backend/.env', 'backend'),
        ('src/.env.local', 'src'),
        
        # Next.js build and configuration files
        ('.next', '.next'),
        ('node_modules', 'node_modules'),
        ('package.json', '.'),
        ('package-lock.json', '.'),
        ('next.config.js', '.'),
        ('postcss.config.js', '.'),
        ('tailwind.config.js', '.'),
        ('tsconfig.json', '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'pydantic',
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.image',
        'pandas',
        'matplotlib',
        'smtplib',
        'apscheduler',
        'python-dotenv',
        'http.server',
        'psutil',
        'requests',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EmailApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)