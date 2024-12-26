# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

fastapi_hidden = collect_submodules('fastapi')
starlette_hidden = collect_submodules('starlette')
uvicorn_hidden = collect_submodules('uvicorn')
encodings_hidden = collect_submodules('encodings')

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Environment files with explicit paths
        ('backend/.env', 'backend'),
        ('src/.env.local', 'src'),
        
        ('backend', 'backend'),

        # Next.js build and configuration files
        ('.next', '.next'),
        ('public', 'public'),
        ('package.json', '.'),
        ('package-lock.json', '.'),
        ('next.config.js', '.'),
        ('tsconfig.json', '.'),
    ],
    hiddenimports=[
        # System modules
        'encodings',
        *encodings_hidden,
        'winreg',

        # FastAPI and dependencies
        *fastapi_hidden,
        *starlette_hidden,
        *uvicorn_hidden,
        'fastapi',
        'pydantic',

        # Email related
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.image',
        
        # Data processing
        'pandas',
        'numpy',
        'matplotlib',
        'matplotlib.backends.backend_agg',

        # Server and process management
        'smtplib',
        'apscheduler',
        'python-dotenv',
        'http.server',
        'webbrowser',
        'psutil',
        'threading',
        'multiprocessing',

        # Uvicorn dependencies
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

a.datas = [d for d in a.datas if not d[0].startswith('node_modules')]
a.binaries = [b for b in a.binaries if not b[0].startswith('node_modules')]

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