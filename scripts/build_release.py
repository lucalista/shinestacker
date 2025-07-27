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
project_name = "shinestacker"
app_name = "shinestacker"
package_dir = "shinestacker"

sys_name = platform.system().lower()

pyinstaller_cmd = ["pyinstaller", "--onedir", f"--name={app_name}", "--paths=src",
                   f"--distpath=dist/{package_dir}", f"--collect-all={project_name}",
                   "--collect-data=imagecodecs", "--collect-submodules=imagecodecs", "--copy-metadata=imagecodecs"]
if sys_name == 'darwin':
    pyinstaller_cmd += ["--windowed", "--icon=src/shinestacker/gui/ico/shinestacker.icns"]
elif sys_name == 'windows':
    pyinstaller_cmd += ["--windowed", "--icon=src/shinestacker/gui/ico/shinestacker.ico"]
pyinstaller_cmd += ["src/shinestacker/app/main.py"]

print(" ".join(pyinstaller_cmd))
subprocess.run(pyinstaller_cmd, check=True)

examples_dir = project_root / "examples"
target_examples = dist_dir / package_dir / "examples"
target_examples.mkdir(exist_ok=True)
for project_file in ["complete-project.fsp", "stack-from-frames.fsp"]:
    shutil.copy(examples_dir / project_file, target_examples)
    shutil.copytree(examples_dir / 'input', target_examples / 'input', dirs_exist_ok=True)

shutil.make_archive(
    base_name=str(dist_dir / "shinestacker-release"),
    format="zip",
    root_dir=dist_dir,
    base_dir=package_dir
)
