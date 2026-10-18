"""Verify reviewed source bytes and product/release identity before packaging."""
import argparse
import hashlib
from pathlib import Path
from package_checks import check_identity

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--release-tag", help="Exact release tag; must equal v + source and project version")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
source = (root / "content/MqttClient.qplug").read_bytes()
if hashlib.sha256(source).hexdigest() != "de6d6f546c8a766778741e086988ab4ab03b7fe589fb1079d946b47e3594962a":
    raise SystemExit("Update the reviewed source digest for an intentional plugin revision")
try:
    version = check_identity(source.decode("utf-8-sig"), (root / "MqttClient.csproj").read_text(),
        "JoshuaSmall.Qsys.MqttClient", args.release_tag)
except ValueError as error:
    raise SystemExit(str(error)) from error
if not (root / "icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("Invalid package icon")
if "https://joshua-small.github.io/qsys-mqtt/registration/joshuasmall.qsys.mqttclient/index.json" not in (root / "README.md").read_text():
    raise SystemExit("README Library feed does not match package identity")
print("Verified", "MqttClient.qplug", version, hashlib.sha256(source).hexdigest())
