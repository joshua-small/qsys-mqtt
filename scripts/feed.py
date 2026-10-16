"""Build a static NuGet feed from published GitHub release packages."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--sleet", default="sleet")
    args = parser.parse_args()
    root = Path.cwd()
    packages = root / "dist" / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    releases = json.loads(run("gh", "api", f"repos/{args.repository}/releases", "--paginate", "--slurp"))
    for page in releases:
        for release in page:
            if release["draft"] or release["prerelease"]:
                continue
            if not any(a["name"].endswith(".nupkg") for a in release["assets"]):
                raise RuntimeError(f"Published release missing package: {release['tag_name']}")
            run("gh", "release", "download", release["tag_name"], "--repo", args.repository,
                "--pattern", "*.nupkg", "--dir", str(packages), "--skip-existing")
    files = sorted(packages.glob("*.nupkg"))
    if not files:
        raise RuntimeError("No release packages found")
    for package in files:
        with zipfile.ZipFile(package) as archive:
            assert "content/MqttClient.qplug" in archive.namelist(), package
            assert "README.md" in archive.namelist(), package
    config = {"sources": [{"name": "pages", "type": "local", "path": str(root / "feed"),
                            "baseURI": args.base_url.rstrip("/") + "/"}]}
    Path("sleet.json").write_text(json.dumps(config), encoding="utf-8")
    print(run(args.sleet, "push", str(packages), "--config", "sleet.json", "--source", "pages"))
    feed = root / "feed"
    shutil.copyfile("icon.png", feed / "icon.png")
    (feed / ".nojekyll").touch()
    (feed / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>MQTT Client (TLS fix pending) for Q-SYS</title>'
        '<h1>MQTT Client (TLS fix pending) for Q-SYS</h1>'
        f'<p><a href="https://github.com/{args.repository}#readme">Installation and user manual</a></p>'
        '<p>My Packages URL:</p><code>' + args.base_url.rstrip("/") +
        '/registration/joshuasmall.qsys.mqttclient/index.json</code>', encoding="utf-8")
    index = json.loads((feed / "index.json").read_text())
    assert any("RegistrationsBaseUrl" in r["@type"] for r in index["resources"])
    registration = json.loads((feed / "registration/joshuasmall.qsys.mqttclient/index.json").read_text())
    assert registration["count"] > 0
    for package in files:
        print(package.name, hashlib.sha256(package.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
