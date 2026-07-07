# Installation Note for macOS Users

**This note applies only if you downloaded Shine Stacker as a compressed archive from the [release page](https://github.com/lucalista/shinestacker/releases).**

macOS system security (Gatekeeper) may prevent applications from running if they were downloaded from the Internet and are not signed with an official Apple Developer Certificate.

To allow Shine Stacker to run safely, please follow these steps:

1. Download the disk image file, ```shinestacker-macos-apple-silicon.dmg``` for more recent computers using ARM processors, or ```shinestacker-macos-intel.dmg ``` for computers using Intel x86-64 processors.
2. Double-click the ```.dmg``` file and drag the **Shine Stacker** app into your **Application** folder.
3. Open the **Terminal** (found in *Applications > Utilities > Terminal*).
4. Run the following command to remove the quarantine attribute:
```bash
sudo xattr -cr /Applications/shinestacker.app
```
5. You can now launch Shine Stacker normally from your Applications folder.

> 💡 Tip: macOS might still show a security warning the first time you open the app.
> If that happens, right-click the app and choose Open, then confirm.


*Note that only macOS apple silicon (ARM processor) is supported. x64 intel platform is not supported due to missing free build machines on GitHub.*