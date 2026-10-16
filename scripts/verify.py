"""Verify package identity and source integrity before publishing."""
from pathlib import Path
import hashlib
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
source = (root / "content/MqttClient.qplug").read_bytes()
assert hashlib.sha256(source).hexdigest() == "79607c6170dd9c8a55ab8e1e9c209d74b1701f27526d40431bafccc3b58aeca2", "Update the reviewed source digest for an intentional plugin revision"
info = re.search(r"PluginInfo\s*=\s*\{(.*?)\}", source.decode("utf-8-sig"), re.S)[1]
version = re.search(r'\bVersion\s*=\s*"([^"]+)"', info)[1]
project = ET.parse(root / "MqttClient.csproj").getroot()
assert version == project.findtext("PropertyGroup/Version"), "Plugin/package version mismatch"
assert project.findtext("PropertyGroup/PackageId") == "JoshuaSmall.Qsys.MqttClient"
assert (root / "icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
assert "https://joshua-small.github.io/qsys-mqtt/registration/joshuasmall.qsys.mqttclient/index.json" in (root / "README.md").read_text()
print("Verified", "MqttClient.qplug", version, hashlib.sha256(source).hexdigest())
