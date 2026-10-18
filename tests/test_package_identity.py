"""Exercise mismatched release identities before any package upload."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_checks import check_identity

class IdentityTests(unittest.TestCase):
    def check(self, version="1.2.3", package="1.2.3", tag=None, identity="Example.Plugin"):
        return check_identity('PluginInfo = { Version = "' + version + '" }',
            '<Project><PropertyGroup><Version>' + package + '</Version><PackageId>' + identity +
            '</PackageId></PropertyGroup></Project>', "Example.Plugin", tag)

    def test_matching_three_and_four_part_versions(self):
        for version in ("1.2.3", "1.2.3.4"):
            self.assertEqual(version, self.check(version, version, "v" + version))
            self.assertEqual(version, self.check(version, version))

    def test_rejects_wrong_tag_even_when_numeric(self):
        for tag in ("v1.2.4", "1.2.3", "v1.2.3.0", "v1.2.3-beta", "v1.2.3\n", "../v1.2.3", ""):
            with self.subTest(tag=tag), self.assertRaises(ValueError): self.check(tag=tag)

    def test_rejects_project_and_identity_mismatch(self):
        with self.assertRaises(ValueError): self.check(package="1.2.4")
        with self.assertRaises(ValueError): self.check(identity="Other.Plugin")

    def test_rejects_missing_or_malformed_plugin_version(self):
        for version in ("", "1.2", "1.2.3-beta", "01.2.3", "1.2.3.4.5"):
            with self.subTest(version=version), self.assertRaises(ValueError): self.check(version, version)
        with self.assertRaises(ValueError): check_identity("", "<Project/>", "Example.Plugin")

if __name__ == "__main__": unittest.main()
