import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import vgtheme  # noqa: E402

PATCH = ROOT / "patches" / "voidgram-theme-engine.patch"


def patched_file(name: str) -> str:
    """A file the theme engine patch adds, as the app gets it."""
    text = PATCH.read_text(encoding="utf-8")
    for block in re.split(r"(?m)^(?=diff --git )", text):
        if block.startswith(f"diff --git a/{name} b/{name}"):
            body = block.split("\n@@", 1)[1].split("\n", 1)[1]
            return "".join(line[1:] + "\n" for line in body.split("\n") if line.startswith("+"))
    raise AssertionError(f"{name} is not added by {PATCH.name}")


ENGINE = "submodules/Display/Source/AyuThemeEngine.swift"
BUILTINS = "submodules/Display/Source/AyuThemeEngineBuiltins.swift"


def theme(**fields):
    document = {"vgtheme": 1, "id": "t", "name": "T"}
    document.update(fields)
    return document


def color(expression, **variables):
    resolved = vgtheme.resolve(theme(vars=variables, colors={"text": expression}), dark=False, keys=set())
    return resolved.native["list.primaryText"]


class SwiftParityTests(unittest.TestCase):
    def test_alias_table_matches_the_app(self):
        source = patched_file(ENGINE)
        table = source.split("public static let aliases", 1)[1].split("\n    ]\n", 1)[0]
        swift = [(name, re.findall(r'"([^"]+)"', targets)) for name, targets in re.findall(r'\("([^"]+)", \[([^\]]*)\]\)', table)]
        self.assertEqual(swift, vgtheme.ALIASES)

    def test_derived_names_and_limits_match_the_app(self):
        source = patched_file(ENGINE)
        derived = re.findall(r'\("([^"]+)", "([^"]+)", "([^"]+)"\)', source.split("static let derived", 1)[1].split("]\n", 1)[0])
        self.assertEqual(derived, vgtheme.DERIVED)
        for swift_name, value in [("maxFileBytes", vgtheme.MAX_FILE_BYTES), ("maxVars", vgtheme.MAX_VARS), ("maxNative", vgtheme.MAX_NATIVE), ("maxExpression", vgtheme.MAX_EXPRESSION), ("maxDepth", vgtheme.MAX_DEPTH), ("formatVersion", vgtheme.FORMAT_VERSION)]:
            match = re.search(rf"static let {swift_name} = ([0-9 *]+)\n", source)
            self.assertIsNotNone(match, swift_name)
            self.assertEqual(eval(match.group(1)), value, swift_name)
        self.assertIn('public static let bases = ["' + '", "'.join(vgtheme.BASES) + '"]', source)
        for pattern in (vgtheme.ID_PATTERN.pattern, vgtheme.VAR_PATTERN.pattern, vgtheme.NUMBER_PATTERN.pattern):
            self.assertIn(pattern.replace("\\", "\\\\"), source)

    def test_builtin_themes_are_the_repository_files(self):
        self.assertEqual(patched_file(BUILTINS), vgtheme.swift_builtins())


class ThemeFileTests(unittest.TestCase):
    def test_repository_themes_resolve_cleanly(self):
        keys = vgtheme.load_keys()
        ids = set()
        for path in sorted((ROOT / "themes").glob("*.vgtheme")):
            document = vgtheme.load(path)
            self.assertNotIn(document["id"], ids)
            ids.add(document["id"])
            self.assertEqual(path.stem, document["id"])
            for dark in (False, True):
                resolved = vgtheme.resolve(document, dark, keys=keys)
                self.assertEqual(resolved.warnings, [], path.name)
        self.assertEqual(set(vgtheme.BUILTIN_ORDER), ids)

    def test_alias_targets_are_telegram_keys(self):
        keys = json.loads(vgtheme.KEYS_FILE.read_text(encoding="utf-8"))
        for name, targets in vgtheme.ALIASES:
            for target in targets:
                self.assertEqual(keys.get(target), "color", f"{name} -> {target}")
        self.assertEqual(len(vgtheme.ALIAS_NAMES), len(set(vgtheme.ALIAS_NAMES)))

    def test_docs_list_the_current_names(self):
        docs = (ROOT / "docs" / "THEME_ENGINE_RU.md").read_text(encoding="utf-8")
        table = docs.split("<!-- aliases:begin -->\n", 1)[1].split("<!-- aliases:end -->", 1)[0]
        rows = [line.split("`")[1] for line in table.splitlines()[2:]]
        self.assertEqual(rows, vgtheme.ALIAS_NAMES)

    def test_patch_is_applied_and_its_sources_are_required(self):
        self.assertIn('"voidgram-theme-engine.patch"', (ROOT / "ci" / "prepare.py").read_text(encoding="utf-8"))
        required = json.loads((ROOT / "ci" / "required_port_sources.json").read_text(encoding="utf-8"))
        for name in (ENGINE, BUILTINS, "submodules/TelegramPresentationData/Sources/AyuThemeEngineApply.swift", "submodules/SettingsUI/Sources/AyuThemesController.swift"):
            self.assertIn(name, required)


class ExpressionTests(unittest.TestCase):
    def test_hex_forms(self):
        self.assertEqual(color("#abc"), 0xFFAABBCC)
        self.assertEqual(color("#abcd"), 0xDDAABBCC)
        self.assertEqual(color("#102030"), 0xFF102030)
        self.assertEqual(color("#10203080"), 0x80102030)
        self.assertEqual(color("transparent"), 0)

    def test_functions(self):
        self.assertEqual(color("mix(#000000, #ffffff, 0.5)"), 0xFF808080)
        self.assertEqual(color("mix(#000000, #ffffff, 50%)"), 0xFF808080)
        self.assertEqual(color("alpha(#ff0000, 0.5)"), 0x80FF0000)
        self.assertEqual(color("lighten(#000000, 0.25)"), 0xFF404040)
        self.assertEqual(color("darken(#ffffff, 0.25)"), 0xFFBFBFBF)
        self.assertEqual(color("darken(#ffffff80, 0.5)"), 0x80808080)
        self.assertEqual(color("contrast(#ffffff)"), 0xFF000000)
        self.assertEqual(color("contrast(#202020)"), 0xFFFFFFFF)
        self.assertEqual(color("alpha( mix( $a , #000000 , 0.5 ) , 1 )", a="#ffffff"), 0xFF808080)

    def test_variables_chain_and_cycles(self):
        self.assertEqual(color("$c", a="#112233", b="$a", c="lighten($b, 0)"), 0xFF112233)
        with self.assertRaisesRegex(vgtheme.ThemeError, "cycle"):
            color("$a", a="$b", b="$a")
        with self.assertRaisesRegex(vgtheme.ThemeError, "unknown variable"):
            color("$missing")

    def test_unused_broken_variable_fails(self):
        with self.assertRaisesRegex(vgtheme.ThemeError, "vars.bad"):
            color("#000000", bad="nope(#000)")

    def test_errors(self):
        for bad in ["#12", "#ggg", "red", "mix(#000, #fff)", "mix(#000, #fff, 2)", "alpha(#000, -1)", "alpha(#000, 0x1)", "#000 #fff", "", "$", "lighten(#000, 1.)"]:
            with self.assertRaises(vgtheme.ThemeError, msg=bad):
                color(bad)
        with self.assertRaisesRegex(vgtheme.ThemeError, "deeply"):
            color("contrast(" * 18 + "#000" + ")" * 18)
        self.assertEqual(color("contrast(" * 15 + "#000" + ")" * 15), 0xFFFFFFFF)

    def test_base_references(self):
        resolved = vgtheme.resolve(theme(colors={"text": "mix(@list.primaryText, #ffffff, 0.5)"}), False, base_values={"list.primaryText": 0xFF000000}, keys={"list.primaryText"})
        self.assertEqual(resolved.native["list.primaryText"], 0xFF808080)
        with self.assertRaisesRegex(vgtheme.ThemeError, "unknown native key"):
            vgtheme.resolve(theme(colors={"text": "@list.nope"}), False, keys={"list.primaryText"})


class DocumentTests(unittest.TestCase):
    def test_header_checks(self):
        for broken in [{"vgtheme": True}, {"vgtheme": 2}, {"id": "Bad Id"}, {"name": ""}, {"name": {"en": ""}}, {"base": "dark"}, {"author": 5}, {"variants": {"dusk": {}}}, {"colors": {"nope": "#000"}}, {"vars": {"1x": "#000"}}]:
            with self.assertRaises(vgtheme.ThemeError, msg=str(broken)):
                vgtheme.resolve(theme(**broken), False, keys=set())

    def test_variants_override_and_aliases_order(self):
        document = theme(
            vars={"x": "#111111"},
            colors={"text": "$x", "chatList.title": "#222222"},
            variants={"dark": {"vars": {"x": "#333333"}, "wallpaper": "#010203"}},
            wallpaper=["#ffffff", "#000000"],
        )
        light = vgtheme.resolve(document, False, keys=set())
        dark = vgtheme.resolve(document, True, keys=set())
        self.assertEqual(light.native["list.primaryText"], 0xFF111111)
        self.assertEqual(dark.native["list.primaryText"], 0xFF333333)
        self.assertEqual(light.native["chatList.title"], 0xFF222222)
        self.assertEqual(light.wallpaper, [0xFFFFFFFF, 0xFF000000])
        self.assertEqual(dark.wallpaper, [0xFF010203])

    def test_native_overrides_aliases_and_unknown_keys_warn(self):
        document = theme(colors={"text": "#111111"}, native={"list.primaryText": "#222222", "list.nope": "#333333"})
        resolved = vgtheme.resolve(document, False, keys={"list.primaryText", "chatList.title"})
        self.assertEqual(resolved.native["list.primaryText"], 0xFF222222)
        self.assertNotIn("list.nope", resolved.native)
        self.assertEqual(len(resolved.warnings), 1)

    def test_bubble_highlight_is_derived(self):
        resolved = vgtheme.resolve(theme(colors={"outgoing.bubble": "#ffffff"}), False, keys=set())
        self.assertEqual(resolved.native["chat.message.outgoing.bubble.withoutWp.highlightedBg"], 0xFFEBEBEB)
        resolved = vgtheme.resolve(theme(colors={"outgoing.bubble": "#ffffff", "outgoing.bubbleHighlighted": "#000000"}), False, keys=set())
        self.assertEqual(resolved.native["chat.message.outgoing.bubble.withWp.highlightedBg"], 0xFF000000)

    def test_wallpaper_forms(self):
        resolved = vgtheme.resolve(theme(wallpaper={"colors": ["#10203080", "#000"], "rotation": 90.0}), False, keys=set())
        self.assertEqual(resolved.wallpaper, [0xFF102030, 0xFF000000])
        self.assertEqual(resolved.rotation, 90)
        for broken in [[], ["#000"] * 5, {"colors": ["#000"], "rotation": 360}, {"colors": ["#000"], "rotation": True}, {"rotation": 0}, 5]:
            with self.assertRaises(vgtheme.ThemeError, msg=str(broken)):
                vgtheme.resolve(theme(wallpaper=broken), False, keys=set())


if __name__ == "__main__":
    unittest.main()
