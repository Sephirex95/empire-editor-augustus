# Empire Editor for Augustus by Sephirex95

A visual tool for creating and editing *Empire* maps and trade data for the [Augustus](https://github.com/Keriew/augustus/tree/master) project.

---

## Summary

- Visual, PySide6-based editor for Empire maps, saving them as .xml
- Supports trade routes, city metadata, empire borders and custom backgrounds
- Ships with **Areldir’s** beautiful new Empire maps in 3 versions
- Requires valid Caesar III installation to run
- Extracts **vanilla Caesar III** assets **at runtime** from your local installation (not redistributed).
- A long list of default cities to auto-place on the maps (with recalculated coordinates for all 3 Areldir's maps)
- Currently **DOES NOT** support invasions or future paths. TBA soon.
- main_window.py is in dire need of a refactor, the code is massive (4k+ lines). There's a lot of duplicated methods and unnecessary checks, which I'll try to remove to be easier to maintain.

---

## Releases

Download the full program from Releases. Currently no Github build (TBA)

- Built with **PyInstaller** (onedir). Includes all necessary libraries, including packaged Python 3.13.
- Dependencies and runtime files are placed under `./_internal/`.
- Release includes **packaged Augustus assets** and **maps by Areldir** so the editor works out of the box, provided there's a valid C3 installation.

> **Windows:** unzip and run `EmpireEditor.exe`. 

---

## Run from source

```bash
# Python 3.11+ recommended
pip install -r requirements.txt
python main_window.py
```

Minimal runtime requirements:

- [PySide6](https://pypi.org/project/PySide6/)
- [Pillow](https://pypi.org/project/Pillow/)

Other utilities (if any) are listed in `requirements.txt`.

---

## Build (PyInstaller)

This repo includes a working `EmpireEditor.spec` (onedir, windowed, with assets placed under `_internal/`).

```bash
pyinstaller -y --clean EmpireEditor.spec
# Output: dist/EmpireEditor/EmpireEditor.exe and ./_internal/*
```

Notes:

- The spec excludes NumPy/MKL for a smaller build. It was removed from the current version, but an old version of sg_reader that uses np is still in repo (not imported anywhere in the main process though).
- `augustus_assets/` and `editor.ico` are included under `_internal/`.
- If you change the icon or assets directory, update the spec accordingly.

---

## Credits & Thanks

- **Sgreader** code is a Python conversion of parts of the **citybuilding-tools** by **Bianca “bvschaik” van Schaik**, author of [Julius](https://github.com/bvschaik/julius) and founder of the community: [https://github.com/bvschaik/citybuilding-tools](https://github.com/bvschaik/citybuilding-tools)
- Enormous thanks to **Areldir** for making and generously sharing the Empire maps bundled with this editor.
- **Vanilla assets** are extracted at runtime from *Caesar III* by **Impressions Games**, published by **Sierra Studios (Activision)**.
- Huge thanks to **Destinationwalker**, **CommissarMarek**, and **Turgon** for consulting on the XML logic, and **PrettyFlower** for the original custom-empires code.
- And to the **Augustus** community and dev team for support and contributions—big and small.

---

## License & third‑party notices

**Project license:** add your preferred license (e.g., MIT/BSD/GPL) and include a `LICENSE` file in the repo.

**PySide6 / Qt for Python**

This application uses **PySide6** (Qt for Python). PySide6 and Qt are available under the **GNU LGPL v3**.

- LGPL v3: [https://www.gnu.org/licenses/lgpl-3.0.html](https://www.gnu.org/licenses/lgpl-3.0.html)
- PySide sources & license texts: [https://code.qt.io/pyside/pyside-setup](https://code.qt.io/pyside/pyside-setup)
- Qt licensing overview: [https://www.qt.io/terms-conditions/license/](https://www.qt.io/terms-conditions/license/)

This application dynamically links to PySide6/Qt. Under the LGPL v3, you may replace or relink those libraries with a modified version. Reverse engineering is permitted for the purpose of debugging such modifications.

**Caesar III content**

No proprietary Caesar III assets are redistributed in this repository or in releases. Vanilla assets are extracted at runtime from the user’s own installation of *Caesar III*. *Caesar III* is © Impressions Games / Sierra Studios (Activision).

**Bundled assets**

Releases include **Augustus** assets and **Areldir’s** Empire maps with permission. If you reuse these assets, please respect the original authors’ terms and attribution.

---
