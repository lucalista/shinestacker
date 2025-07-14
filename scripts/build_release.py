import os
import shutil
import subprocess
from pathlib import Path
import platform

#
# assume the scripts runs under its directory, "scripts", as defined in release.yml
#
os.chdir("../")
project_root = Path(__file__).resolve().parent.parent
dist_dir = project_root / "dist"

sys_name = platform.system().lower()
if sys_name == 'darwin':
    pyinstaller_cmd = ["pyinstaller", "--windowed", "--onedir", "--name=focusstack-main", "--paths=src",
                       "--collect-all=focusstack", "--icon=ico/focus_stack.icns"]
elif sys_name == 'windows':
    pyinstaller_cmd = ["pyinstaller", "--windowed", "--onedir", "--name=focusstack-main", "--paths=src",
                       "--collect-all=focusstack", "--icon=ico/focus_stack.ico"]
else:
    pyinstaller_cmd = ["pyinstaller", "--onedir", "--name=focusstack-main", "--paths=src",
                       "--collect-all=focusstack"]

pyinstaller_cmd.append("src/focusstack/app/main.py")

subprocess.run(pyinstaller_cmd, check=True)

ico_dir = project_root / "ico"
target_ico = dist_dir / "focusstack-main" / "ico"
if target_ico.exists():
    shutil.rmtree(target_ico)
shutil.copytree(ico_dir, target_ico)

examples_dir = project_root / "examples"
target_examples = dist_dir / "focusstack-main" / "examples"
target_examples.mkdir(exist_ok=True)
for project_file in ["project.fsp", "stack-from-frames.fsp"]:
    shutil.copy(examples_dir / project_file, target_examples)

if sys_name == 'darwin':
    app_dir = dist_dir / "focusstack-main.app"
    target_app = dist_dir / "focusstack-main"
    if target_app.exists():
        shutil.move(app_dir, target_app)
elif sys_name == 'windows':
    app_dir = dist_dir / "focusstack-main.exe"
    target_app = dist_dir / "focusstack-main"
    if target_app.exists():
        shutil.move(app_dir, target_app)

shutil.make_archive(
    base_name=str(dist_dir / "focusstack-release"),
    format="zip",
    root_dir=dist_dir,
    base_dir="focusstack-main"
)
