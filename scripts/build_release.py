import os
import shutil
import subprocess
from pathlib import Path

os.chdir("../")
project_root = Path(__file__).resolve().parent.parent
dist_dir = project_root / "dist"
ico_dir = project_root / "ico"
examples_dir = project_root / "examples"

subprocess.run([
    "pyinstaller",
    "--onedir",
    "--name=focusstack-main",
    "--paths=src",
    "--collect-all=focusstack",
    "src/focusstack/app/main.py"
], check=True)

target_ico = dist_dir / "focusstack-main" / "ico"
if target_ico.exists():
    shutil.rmtree(target_ico)
shutil.copytree(ico_dir, target_ico)

target_examples = dist_dir / "examples"
target_examples.mkdir(exist_ok=True)
for project_file in ["project.fsp", "stack-from-frames.fsp"]:
    shutil.copy(examples_dir / project_file, target_examples)

shutil.make_archive(
    base_name=str(dist_dir / "focusstack-release"),
    format="zip",
    root_dir=dist_dir,
    base_dir="focusstack-main"
)
