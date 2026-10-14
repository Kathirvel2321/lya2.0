"""Isolated approved-artwork check; no Desktop, sensors, stores or network."""
import ast
import hashlib
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from app import Crystal, HERE


def main():
    output = HERE.parent / "review" / "2026-10-14-approved-body-install"
    output.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    parent = QWidget()
    crystal = Crystal(parent)
    crystal.set_reduced_motion(True)
    asset = HERE / "assets" / "lya-reference-body.png"
    expected = QPixmap(str(asset)).scaled(288, 408, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
    assert crystal.original.toImage() == expected.toImage()
    assert crystal.base.cacheKey() == crystal.original.cacheKey()
    assert not crystal.using_model and crystal.original.hasAlphaChannel()
    # The actual launcher must not silently select the old experimental bake.
    tree = ast.parse((HERE / "app.py").read_text(encoding="utf-8"))
    startup = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    selection = [node for node in ast.walk(startup) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == "set_artwork"]
    assert len(selection) == 1
    assert ast.unparse(selection[0].args[0]) == "args.model_art and (not args.original_art)"
    activated = []
    crystal.activated.connect(lambda: activated.append(True))
    crystal.show()
    parent.show()
    QTest.keyClick(crystal, Qt.Key.Key_Return)
    assert len(activated) == 1
    results = []
    for name, size, task, phase, morph in (
        ("resting", (230, 315), "idle", "standby", 0),
        ("listening", (230, 315), "listening", "listening", 0),
        ("thinking", (230, 315), "thinking", "thinking", 0),
        ("speaking", (230, 315), "idle", "speaking", 0),
        ("docked", (72, 72), "idle", "standby", 1),
    ):
        crystal.setMinimumSize(1, 1)
        crystal.setMaximumSize(16777215, 16777215)
        crystal.resize(*size)
        crystal.circle_mix = morph
        crystal.set_state(task=task)
        crystal.set_voice_phase(phase)
        application.processEvents()
        image = crystal.grab().toImage()
        assert not image.isNull() and image.hasAlphaChannel()
        assert any(image.pixelColor(x, y).alpha() for y in range(image.height()) for x in range(image.width()))
        assert image.save(str(output / (name + ".png")))
        assert not crystal.timer.isActive()
        results.append(name)
    crystal.set_artwork(True)
    crystal.set_artwork(False)
    assert crystal.base.cacheKey() == crystal.original.cacheKey()
    crystal.close()
    parent.close()
    result = {"success": True, "synthetic_states": results,
              "asset_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
              "keyboard_activation": True, "legacy_toggle_returns_to_approved_body": True,
              "startup_default_verified": True, "live_voice_tested": False}
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
