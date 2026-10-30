import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ayutheme", ROOT / "tools/ayutheme.py")
AYUTHEME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AYUTHEME)


def theme(**values):
    return {"format": "ayu-theme-1", "id": "test", "name": "Test", "author": "Me", "version": "1.0", **values}


class ThemeTests(unittest.TestCase):
    def test_example_themes_are_valid(self):
        files = sorted((ROOT / "themes").glob("*.ayutheme"))
        self.assertTrue(files)
        for path in files:
            self.assertEqual(AYUTHEME.check_file(path), [], path.name)

    def test_only_the_header_is_required(self):
        self.assertEqual(AYUTHEME.errors(theme()), [])

    def test_header_problems_are_reported(self):
        self.assertTrue(AYUTHEME.errors(theme(format="ayu-theme-2")))
        self.assertTrue(AYUTHEME.errors(theme(id="../evil")))
        self.assertTrue(AYUTHEME.errors(theme(id="pixel")))
        self.assertTrue(AYUTHEME.errors(theme(name="")))

    def test_unreadable_palettes_are_rejected(self):
        self.assertTrue(AYUTHEME.errors(theme(palette={"dark": "#222222", "light": "#333333"})))
        self.assertTrue(AYUTHEME.errors(theme(palette={"dark": "#FFFFFF", "light": "#000000"})))
        self.assertTrue(AYUTHEME.errors(theme(palette={"dark": "black", "light": "#FFFFFF"})))

    def test_values_outside_their_ranges_are_rejected(self):
        for values in ({"icons": {"grid": 5}}, {"avatars": {"mosaic": 4}}, {"media": {"grid": 9}}, {"animation": {"stepsPerSecond": 2}}, {"chat": {"bubbleCorner": 1}}, {"fonts": {"body": "comic"}}, {"icons": {"grid": True}}):
            self.assertTrue(AYUTHEME.errors(theme(**values)), values)

    def test_zero_turns_a_feature_off(self):
        self.assertEqual(AYUTHEME.errors(theme(icons={"grid": 0}, avatars={"mosaic": 0}, media={"grid": 0}, animation={"stepsPerSecond": 0})), [])

    def test_unknown_keys_are_reported(self):
        self.assertTrue(AYUTHEME.errors(theme(colours={})))
        self.assertTrue(AYUTHEME.errors(theme(icons={"size": 1})))

    def test_shapes_take_known_values_only(self):
        self.assertEqual(AYUTHEME.errors(theme(shapes={"corners": "stock", "panels": "stock", "tabBar": "stock"})), [])
        self.assertTrue(AYUTHEME.errors(theme(shapes={"corners": "round"})))
        self.assertTrue(AYUTHEME.errors(theme(shapes={"tabBar": 1})))

    def test_oversized_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "big.ayutheme"
            path.write_text(json.dumps(theme(description="x" * (9 * 1024 * 1024))))
            self.assertTrue(AYUTHEME.check_file(path))

    def test_a_font_can_be_embedded_and_chosen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "t.ayutheme"
            font = Path(directory) / "f.ttf"
            font.write_bytes(b"\x00\x01\x00\x00" + b"x" * 100)
            path.write_text(json.dumps(theme(fonts={"title": "myfont"})))
            self.assertTrue(AYUTHEME.check_file(path))
            AYUTHEME.add_font(path, font, "myfont")
            self.assertEqual(AYUTHEME.check_file(path), [])

    def test_bad_fonts_are_rejected(self):
        good = base64.b64encode(b"OTTO" + b"x" * 100).decode()
        self.assertEqual(AYUTHEME.errors(theme(customFonts=[{"id": "a", "file": good}])), [])
        self.assertTrue(AYUTHEME.errors(theme(customFonts=[{"id": "a", "file": base64.b64encode(b"<html>").decode()}])))
        self.assertTrue(AYUTHEME.errors(theme(customFonts=[{"id": "a", "file": "not base64!"}])))
        self.assertTrue(AYUTHEME.errors(theme(customFonts=[{"id": "golos", "file": good}])))
        self.assertTrue(AYUTHEME.errors(theme(customFonts=[{"id": "a", "file": good}, {"id": "a", "file": good}])))
        self.assertTrue(AYUTHEME.errors(theme(customFonts=[{"id": str(index), "file": good} for index in range(4)])))
        self.assertTrue(AYUTHEME.errors(theme(customFonts=[{"id": "a", "file": base64.b64encode(b"OTTO" + b"x" * (4 * 1024 * 1024)).decode()}])))


if __name__ == "__main__":
    unittest.main()
