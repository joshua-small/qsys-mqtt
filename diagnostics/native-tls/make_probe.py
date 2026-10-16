"""Create disposable test identities and a native Q-SYS Control Script."""
import argparse
from pathlib import Path
from pki import create_pki

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path, help="New empty directory outside Plugins")
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
if any(output.iterdir()):
    raise SystemExit("Output must be empty; existing evidence is never overwritten")
create_pki(output / "pki")
parts = ["-- DISPOSABLE LOOPBACK TEST ONLY: contains synthetic private keys.\n"]
for name in ("ca", "wrong-ca", "client", "client-renewed", "untrusted-client"):
    variable = name.replace("-", "_")
    parts.append(f"local {variable} = [=[{(output / 'pki' / (name + '.pem')).read_text()}]=]\n")
    if name not in ("ca", "wrong-ca"):
        parts.append(f"local {variable}_key = [=[{(output / 'pki' / (name + '.key')).read_text()}]=]\n")
parts.append(Path(__file__).with_name("probe.lua.in").read_text())
(output / "probe.lua").write_text("".join(parts))
print(output / "probe.lua")
