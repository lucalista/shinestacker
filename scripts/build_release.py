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
project_name = "focusstack"
app_name = "focusstack"
package_dir = "focusstack"

sys_name = platform.system().lower()

pyinstaller_cmd = ["pyinstaller", "--onedir", f"--name={app_name}", "--paths=src",
                   f"--distpath=dist/{package_dir}", f"--collect-all={project_name}"]
if sys_name == 'darwin':
    pyinstaller_cmd += ["--windowed", "--icon=ico/focus_stack.icns"]
elif sys_name == 'windows':
    pyinstaller_cmd += ["--windowed", "--icon=ico/focus_stack.ico"]
pyinstaller_cmd += ["src/focusstack/app/main.py"]

print(" ".join(pyinstaller_cmd))
subprocess.run(pyinstaller_cmd, check=True)

ico_dir = project_root / "ico"
target_ico = dist_dir / package_dir / "ico"
if target_ico.exists():
    shutil.rmtree(target_ico)
shutil.copytree(ico_dir, target_ico)

examples_dir = project_root / "examples"
target_examples = dist_dir / package_dir / "examples"
target_examples.mkdir(exist_ok=True)
for project_file in ["project.fsp", "stack-from-frames.fsp"]:
    shutil.copy(examples_dir / project_file, target_examples)

shutil.make_archive(
    base_name=str(dist_dir / "focusstack-release"),
    format="zip",
    root_dir=dist_dir,
    base_dir=package_dir
)
