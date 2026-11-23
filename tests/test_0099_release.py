import importlib.util
import tarfile
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_release.py"
spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
build_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_release)


class TestReleasePackaging(unittest.TestCase):
    def test_asset_names(self):
        for system, machine, expected in [
            ("linux", "x86_64", "shinestacker-1.18.1-linux-x86_64"),
            ("windows", "AMD64", "shinestacker-1.18.1-windows-x86_64"),
            ("darwin", "arm64", "shinestacker-1.18.1-macos-arm64"),
            ("linux", "aarch64", "shinestacker-1.18.1-linux-arm64"),
        ]:
            with self.subTest(system=system, machine=machine):
                self.assertEqual(
                    build_release.release_asset_name("v1.18.1", system, machine), expected
                )

    def test_archives_keep_application_directory(self):
        with TemporaryDirectory() as directory:
            dist = Path(directory)
            (dist / "shinestacker").mkdir()
            (dist / "shinestacker" / "app").write_text("application")
            linux_name = "shinestacker-1.18.1-linux-x86_64"
            windows_name = "shinestacker-1.18.1-windows-x86_64"
            build_release.package_linux(dist, "shinestacker", linux_name)
            build_release.package_windows(dist, "shinestacker", windows_name)
            with tarfile.open(dist / f"{linux_name}.tar.gz") as archive:
                self.assertIn("shinestacker/app", archive.getnames())
            with zipfile.ZipFile(dist / f"{windows_name}.zip") as archive:
                self.assertIn("shinestacker/app", archive.namelist())

    def test_macos_disk_image_name(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / "dist"
            (dist / "shinestacker.app").mkdir(parents=True)
            name = "shinestacker-1.18.1-macos-arm64"
            with patch.object(build_release.os, "symlink"), \
                    patch.object(build_release.subprocess, "run") as run:
                build_release.package_macos(dist, "shinestacker", root, name)
            self.assertIn(str(dist / f"{name}.dmg"), run.call_args.args[0])

    def test_windows_installer_name(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts" / "shinestacker-inno-setup.iss").write_text(
                '#define MyAppVersion "x.x.x"'
            )
            name = "shinestacker-1.18.1-windows-x86_64"
            with patch.object(build_release.os.path, "exists", return_value=True), \
                    patch.object(build_release.subprocess, "run") as run:
                build_release.create_windows_installer(root, root / "dist", name)
            self.assertIn(f"/F{name}", run.call_args.args[0])

    def test_main_passes_versioned_name_to_windows_packagers(self):
        root = Path("/project")
        dist = root / "dist"
        name = "shinestacker-1.18.1-windows-x86_64"
        with patch.object(build_release, "setup_environment",
                          return_value=(root, dist, "shinestacker", "shinestacker")), \
                patch.object(build_release, "get_version", return_value="1.18.1"), \
                patch.object(build_release.platform, "system", return_value="Windows"), \
                patch.object(build_release.platform, "machine", return_value="AMD64"), \
                patch.object(build_release.subprocess, "run"), \
                patch.object(build_release, "package_windows") as package, \
                patch.object(build_release, "create_windows_installer") as installer:
            build_release.main()
        package.assert_called_once_with(dist, "shinestacker", name)
        installer.assert_called_once_with(root, dist, name)


if __name__ == "__main__":
    unittest.main()
