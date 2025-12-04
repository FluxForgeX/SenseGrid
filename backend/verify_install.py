import importlib
import sys

pkgs = {
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'python-socketio': 'socketio',
    'asyncio-mqtt': 'asyncio_mqtt',
    'motor': 'motor',
    'python-jose': 'jose',
    'passlib': 'passlib',
    'python-dotenv': 'dotenv',
    'pydantic': 'pydantic',
    'loguru': 'loguru',
    'pywebpush': 'pywebpush',
    'ultralytics': 'ultralytics',
    'opencv-python': 'cv2',
    'numpy': 'numpy',
}

ok = True
for pkg_name, module_name in pkgs.items():
    try:
        m = importlib.import_module(module_name)
        ver = getattr(m, '__version__', None)
        print(f"{pkg_name}: OK (module={module_name}) version={ver}")
    except Exception as e:
        print(f"{pkg_name}: ERROR importing {module_name}: {e}")
        ok = False

if not ok:
    sys.exit(2)
