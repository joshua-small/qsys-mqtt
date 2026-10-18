"""Release identity checks shared by local verification and packaging."""
import re
import xml.etree.ElementTree as ET

VERSION = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?"

def check_identity(source, project, expected_id, release_tag=None):
    info = re.search(r"PluginInfo\s*=\s*\{(.*?)\}", source, re.S)
    match = re.search(r'\bVersion\s*=\s*"([^" ]+)"', info[1]) if info else None
    version = match[1] if match else ""
    if not re.fullmatch(VERSION, version):
        raise ValueError("PluginInfo.Version must be a three- or four-part numeric version")
    xml = ET.fromstring(project)
    if xml.findtext("PropertyGroup/Version") != version:
        raise ValueError("Plugin/package version mismatch")
    if xml.findtext("PropertyGroup/PackageId") != expected_id:
        raise ValueError("Unexpected package identity")
    if release_tag is not None and release_tag != "v" + version:
        raise ValueError("Release tag must equal v + PluginInfo.Version and project Version")
    return version
