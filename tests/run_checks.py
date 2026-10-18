"""Offline Lua 5.3 doubles and package checks; no Designer/hardware acceptance."""
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parents[1]
if sys.flags.optimize: raise SystemExit("Run tests without Python optimization; assertions must be enabled")
for name in ['test_package_identity.py', 'test_mqtt.py', 'test_mqtt5.py', 'test_tls.py']:
    subprocess.run([sys.executable, str(root / "tests" / name)], cwd=root, check=True)
