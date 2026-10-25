import os
import shutil
import tarfile
import subprocess
from pathlib import Path
import platform


def setup_environment():
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    project_name = "shinestacker"
    app_name = "shinestacker"
    hooks_dir = "scripts/hooks"
    hook_files = list(Path(hooks_dir).glob("hook-*.py"))
    for hook in hook_files:
        print(f"  - {hook.name}")
    return project_root, dist_dir, project_name, app_name


def build_pyinstaller_command(sys_name, dist_dir, project_name, app_name, hooks_dir):
    if sys_name == 'darwin':
        return [
            "pyinstaller", "--windowed",
            f"--name={app_name}",
            f"--distpath={dist_dir}",
            "--paths=src",
            "--icon=src/shinestacker/gui/ico/shinestacker.icns",
            "--argv-emulation",
            f"--additional-hooks-dir={hooks_dir}",
            f"--collect-all={project_name}",
            "--collect-data=imagecodecs",
            "--collect-submodules=imagecodecs",
            "--copy-metadata=imagecodecs",
            "--copy-metadata=tifftools",
            "src/shinestacker/app/main.py"
        ]
    elif sys_name == 'windows':
        return [
            "pyinstaller", "--onedir", "--windowed",
            f"--name={app_name}",
            f"--distpath={dist_dir}",
            "--paths=src",
            "--icon=src/shinestacker/gui/ico/shinestacker.ico",
            f"--collect-all={project_name}",
            "--collect-data=imagecodecs", "--collect-submodules=imagecodecs",
            "--copy-metadata=imagecodecs", f"--additional-hooks-dir={hooks_dir}",
            "src/shinestacker/app/main.py"
        ]
    else:
        return [
            "pyinstaller", "--onedir",
            f"--name={app_name}",
            f"--distpath={dist_dir}",
            "--paths=src",
            f"--collect-all={project_name}",
            "--collect-data=imagecodecs", "--collect-submodules=imagecodecs",
            "--copy-metadata=imagecodecs", f"--additional-hooks-dir={hooks_dir}",
            "src/shinestacker/app/main.py"
        ]


def package_windows(dist_dir, app_name):
    shutil.make_archive(
        base_name=str(dist_dir / "shinestacker-release"),
        format="zip",
        root_dir=dist_dir,
        base_dir=app_name
    )


def package_macos(dist_dir, app_name, project_root):
    app_bundle = dist_dir / f"{app_name}.app"
    if not app_bundle.exists():
        print(f"ERROR: .app bundle not found at {app_bundle}")
        return
    version = get_version(project_root)
    build_number = version.replace('.', '') + '0'  # Convert x.y.z -> xyz0
    info_plist_template = project_root / "scripts" / "Info.plist"
    info_plist_target = app_bundle / "Contents" / "Info.plist"
    if info_plist_template.exists():
        print("Processing Info.plist...")
        with open(info_plist_template, 'r') as f:
            plist_content = f.read()
        plist_content = plist_content.replace('{{VERSION}}', version)
        plist_content = plist_content.replace('{{BUILD_NUMBER}}', build_number)
        info_plist_target.parent.mkdir(parents=True, exist_ok=True)
        with open(info_plist_target, 'w') as f:
            f.write(plist_content)
        print(f"Info.plist created at: {info_plist_target}")
    else:
        print(f"WARNING: Info.plist template not found at {info_plist_template}")
    icon_source = project_root / "src" / "shinestacker" / "gui" / "ico" / "shinestacker.icns"
    dmg_temp_dir = dist_dir / "dmg_temp"
    if dmg_temp_dir.exists():
        shutil.rmtree(dmg_temp_dir)
    shutil.copytree(app_bundle, dmg_temp_dir / app_bundle.name, symlinks=True)
    os.symlink("/Applications", dmg_temp_dir / "Applications")
    dmg_path = dist_dir / f"{app_name}-release.dmg"
    dmg_cmd = [
        "hdiutil", "create",
        "-volname", app_name,
        "-srcfolder", str(dmg_temp_dir),
        "-ov", str(dmg_path),
        "-format", "UDBZ",
        "-fs", "HFS+"
    ]
    subprocess.run(dmg_cmd, check=True)
    print(f"Created DMG: {dmg_path.name}")
    if icon_source.exists():
        print("Setting custom icon...")
        try:
            subprocess.run(["sips", "-i", str(icon_source)], check=True)
            subprocess.run(["DeRez", "-only", "icns", str(icon_source)],
                           stdout=open("/tmp/icon.r", "w"), check=True)
            subprocess.run(["Rez", "-append", "/tmp/icon.r", "-o", str(dmg_path)], check=True)
            subprocess.run(["SetFile", "-a", "C", str(dmg_path)], check=True)
            print("Custom icon set successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Could not set custom icon: {e}")
    shutil.rmtree(dmg_temp_dir)


def package_linux(dist_dir, app_name):
    archive_path = dist_dir / "shinestacker-release.tar.gz"
    linux_app_dir = dist_dir / app_name
    if linux_app_dir.exists():
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(linux_app_dir, arcname=app_name, recursive=True)
        print(f"Packaged Linux application: {app_name}")
    else:
        print(f"ERROR: Linux app directory not found at {linux_app_dir}")


def get_version(project_root):
    version_file = project_root / "src" / "shinestacker" / "_version.py"
    version = "0.0.0"
    if version_file.exists():
        with open(version_file, 'r') as f:
            content = f.read()
            import re
            match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                version = match.group(1)
    return version


def create_windows_installer(project_root, dist_dir):
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    iscc_exe = None
    for path in inno_paths:
        if os.path.exists(path):
            iscc_exe = path
            break
    if not iscc_exe:
        try:
            subprocess.run(["choco", "--version"], check=True, capture_output=True)
            subprocess.run(["choco", "install", "innosetup", "-y",
                            "--no-progress", "--accept-license"], check=True)
            for path in inno_paths:
                if os.path.exists(path):
                    iscc_exe = path
                    break
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    if iscc_exe:
        iss_script_source = project_root / "scripts" / "shinestacker-inno-setup.iss"
        iss_script_temp = project_root / "shinestacker-inno-setup.iss"
        if iss_script_source.exists():
            version = get_version(project_root)
            with open(iss_script_source, 'r') as f:
                iss_content = f.read()
            old_version_line = f'#define MyAppVersion "{"x.x.x"}"'
            new_version_line = f'#define MyAppVersion "{version}"'
            iss_content = iss_content.replace(old_version_line, new_version_line)
            with open(iss_script_temp, 'w') as f:
                f.write(iss_content)
            subprocess.run([iscc_exe, str(iss_script_temp)], check=True)
            iss_script_temp.unlink()
            if dist_dir.exists():
                installer_files = list(dist_dir.glob("*.exe"))
                if installer_files:
                    print(f"Installer created: {installer_files[0].name}")


def main():
    project_root, dist_dir, project_name, app_name = setup_environment()
    sys_name = platform.system().lower()
    hooks_dir = "scripts/hooks"
    pyinstaller_cmd = build_pyinstaller_command(
        sys_name, dist_dir, project_name, app_name, hooks_dir)
    print(" ".join(pyinstaller_cmd))
    subprocess.run(pyinstaller_cmd, check=True)
    if sys_name == 'windows':
        package_windows(dist_dir, app_name)
    elif sys_name == 'darwin':
        package_macos(dist_dir, app_name, project_root)
    else:
        package_linux(dist_dir, app_name)
    if sys_name == 'windows':
        print("=== CREATING WINDOWS INSTALLER ===")
        create_windows_installer(project_root, dist_dir)


if __name__ == "__main__":
    main()
