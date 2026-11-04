#!/usr/bin/env python3
"""VoidGram theme engine (.vgtheme): reference resolver, validator and author tools.

The app's resolver (AyuThemeEngine.swift in patches/voidgram-theme-engine.patch) follows
this file rule for rule; ci/tests/test_vgtheme.py keeps the alias table, limits and
built-in themes of both in step.

    python tools/vgtheme.py validate themes/*.vgtheme
    python tools/vgtheme.py resolve themes/nord.vgtheme [--dark]
    python tools/vgtheme.py aliases            # Markdown table for the docs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

FORMAT_VERSION = 1
MAX_FILE_BYTES = 256 * 1024
MAX_VARS = 256
MAX_NATIVE = 1000
MAX_EXPRESSION = 200
MAX_DEPTH = 16
BASES = ("inherit", "day", "classic", "night", "tinted")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
VAR_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,47}$")
NUMBER_PATTERN = re.compile(r"^[0-9]*\.?[0-9]+%?$")
KEYS_FILE = Path(__file__).resolve().parent.parent / "themes" / "telegram-keys.json"

# Semantic names -> native Telegram-iOS keys, applied in this order (general before specific,
# so `chatList.title` wins over `text`). Mirrored by `AyuThemeEngine.aliases` in Swift.
ALIASES: list[tuple[str, list[str]]] = [
    ("background", ["list.blocksBg", "list.modalBlocksBg", "list.plainBg", "list.modalPlainBg", "chatList.bg", "chatList.itemBg"]),
    ("surface", ["list.itemBlocksBg", "list.itemModalBlocksBg", "actionSheet.opaqueItemBg", "contextMenu.background"]),
    ("separator", ["list.blocksSeparator", "list.plainSeparator", "chatList.itemSeparator", "root.navBar.separator", "root.tabBar.separator", "chat.inputPanel.panelSeparator", "actionSheet.opaqueItemSeparator", "contextMenu.itemSeparator"]),
    ("text", ["list.primaryText", "chatList.title", "root.navBar.primaryText", "actionSheet.primaryText", "contextMenu.primary", "notification.primaryText"]),
    ("secondaryText", ["list.secondaryText", "list.sectionHeaderText", "list.freeText", "list.disclosureArrow", "chatList.messageText", "chatList.dateText", "root.navBar.secondaryText", "actionSheet.secondaryText", "contextMenu.secondary"]),
    ("destructive", ["list.destructive", "actionSheet.destructiveActionText", "contextMenu.destructive", "chat.inputPanel.panelControlDestructive"]),
    ("highlight", ["list.itemHighlightedBg", "chatList.itemHighlightedBg", "actionSheet.opaqueItemHighlightedBg", "contextMenu.itemHighlightedBg"]),
    ("switch.on", ["list.switch.content"]),
    ("switch.off", ["list.switch.frame"]),
    ("navBar.background", ["root.navBar.background", "root.navBar.opaqueBackground"]),
    ("navBar.text", ["root.navBar.primaryText"]),
    ("navBar.button", ["root.navBar.button", "root.navBar.accentText", "root.navBar.control"]),
    ("tabBar.background", ["root.tabBar.background"]),
    ("tabBar.icon", ["root.tabBar.icon", "root.tabBar.text"]),
    ("tabBar.selected", ["root.tabBar.selectedIcon", "root.tabBar.selectedText"]),
    ("badge.background", ["root.tabBar.badgeBackground", "root.navBar.badgeFill", "chatList.unreadBadgeActiveBg", "chat.historyNav.badgeBg"]),
    ("badge.text", ["root.tabBar.badgeText", "root.navBar.badgeText", "chatList.unreadBadgeActiveText", "chat.historyNav.badgeText"]),
    ("search.background", ["root.searchBar.inputFill", "chatList.regularSearchBar", "chatList.pinnedSearchBar"]),
    ("search.text", ["root.searchBar.inputText"]),
    ("search.placeholder", ["root.searchBar.inputPlaceholderText", "root.searchBar.inputIcon"]),
    ("chatList.background", ["chatList.bg", "chatList.itemBg"]),
    ("chatList.pinned", ["chatList.pinnedItemBg"]),
    ("chatList.title", ["chatList.title"]),
    ("chatList.message", ["chatList.messageText"]),
    ("chatList.author", ["chatList.authorName"]),
    ("chatList.date", ["chatList.dateText"]),
    ("chatList.unread", ["chatList.unreadBadgeActiveBg"]),
    ("chatList.unreadText", ["chatList.unreadBadgeActiveText"]),
    ("chatList.muted", ["chatList.unreadBadgeInactiveBg", "chatList.muteIcon"]),
    ("chatList.mutedText", ["chatList.unreadBadgeInactiveText"]),
    ("chatList.checkmark", ["chatList.checkmark"]),
    ("chatList.online", ["chatList.onlineDot"]),
    ("outgoing.bubble", ["chat.message.outgoing.bubble.withWp.bg", "chat.message.outgoing.bubble.withWp.gradientBg", "chat.message.outgoing.bubble.withoutWp.bg", "chat.message.outgoing.bubble.withoutWp.gradientBg"]),
    ("outgoing.bubbleGradient", ["chat.message.outgoing.bubble.withWp.gradientBg", "chat.message.outgoing.bubble.withoutWp.gradientBg"]),
    ("outgoing.bubbleHighlighted", ["chat.message.outgoing.bubble.withWp.highlightedBg", "chat.message.outgoing.bubble.withoutWp.highlightedBg"]),
    ("outgoing.bubbleStroke", ["chat.message.outgoing.bubble.withWp.stroke", "chat.message.outgoing.bubble.withoutWp.stroke"]),
    ("outgoing.text", ["chat.message.outgoing.primaryText", "chat.message.outgoing.fileTitle"]),
    ("outgoing.secondaryText", ["chat.message.outgoing.secondaryText", "chat.message.outgoing.fileDescription", "chat.message.outgoing.fileDuration"]),
    ("outgoing.link", ["chat.message.outgoing.linkText"]),
    ("outgoing.accent", ["chat.message.outgoing.accentText", "chat.message.outgoing.accentControl", "chat.message.outgoing.mediaActiveControl"]),
    ("outgoing.check", ["chat.message.outgoingCheck"]),
    ("incoming.bubble", ["chat.message.incoming.bubble.withWp.bg", "chat.message.incoming.bubble.withWp.gradientBg", "chat.message.incoming.bubble.withoutWp.bg", "chat.message.incoming.bubble.withoutWp.gradientBg"]),
    ("incoming.bubbleGradient", ["chat.message.incoming.bubble.withWp.gradientBg", "chat.message.incoming.bubble.withoutWp.gradientBg"]),
    ("incoming.bubbleHighlighted", ["chat.message.incoming.bubble.withWp.highlightedBg", "chat.message.incoming.bubble.withoutWp.highlightedBg"]),
    ("incoming.bubbleStroke", ["chat.message.incoming.bubble.withWp.stroke", "chat.message.incoming.bubble.withoutWp.stroke"]),
    ("incoming.text", ["chat.message.incoming.primaryText", "chat.message.incoming.fileTitle"]),
    ("incoming.secondaryText", ["chat.message.incoming.secondaryText", "chat.message.incoming.fileDescription", "chat.message.incoming.fileDuration"]),
    ("incoming.link", ["chat.message.incoming.linkText"]),
    ("incoming.accent", ["chat.message.incoming.accentText", "chat.message.incoming.accentControl", "chat.message.incoming.mediaActiveControl"]),
    ("service.background", ["chat.serviceMessage.components.withDefaultWp.bg", "chat.serviceMessage.components.withDefaultWp.dateFillStatic", "chat.serviceMessage.components.withDefaultWp.dateFillFloat", "chat.serviceMessage.components.withCustomWp.bg", "chat.serviceMessage.components.withCustomWp.dateFillStatic", "chat.serviceMessage.components.withCustomWp.dateFillFloat"]),
    ("service.text", ["chat.serviceMessage.components.withDefaultWp.primaryText", "chat.serviceMessage.components.withCustomWp.primaryText", "chat.serviceMessage.dateText.withWp", "chat.serviceMessage.dateText.withoutWp"]),
    ("input.background", ["chat.inputPanel.panelBg", "chat.inputButtonPanel.panelBg", "chat.inputMediaPanel.stickersBg"]),
    ("input.field", ["chat.inputPanel.inputBg"]),
    ("input.fieldStroke", ["chat.inputPanel.inputStroke"]),
    ("input.text", ["chat.inputPanel.inputText_v2", "chat.inputPanel.primaryText"]),
    ("input.placeholder", ["chat.inputPanel.inputPlaceholder_v2", "chat.inputPanel.secondaryText"]),
    ("input.icons", ["chat.inputPanel.panelControl_v2", "chat.inputPanel.inputControl_v2"]),
    ("input.accent", ["chat.inputPanel.panelControlAccent", "chat.inputPanel.actionControlBg", "chat.inputPanel.mediaRecordControl.button"]),
    ("input.sendIcon", ["chat.inputPanel.actionControlFg", "chat.inputPanel.mediaRecordControl.activeIcon"]),
    ("menu.background", ["contextMenu.background", "actionSheet.opaqueItemBg"]),
    ("menu.text", ["contextMenu.primary", "actionSheet.primaryText"]),
]
ALIAS_NAMES = [name for name, _ in ALIASES]

# An alias left out of the file takes this expression of another alias, when that one is set.
DERIVED: list[tuple[str, str, str]] = [
    ("outgoing.bubbleHighlighted", "outgoing.bubble", "darken({}, 0.08)"),
    ("incoming.bubbleHighlighted", "incoming.bubble", "darken({}, 0.08)"),
]


class ThemeError(Exception):
    pass


# ARGB as 0xAARRGGBB, like UIColor(argb:).
def parse_hex(text: str) -> int | None:
    if text == "transparent":
        return 0
    if not text.startswith("#"):
        return None
    digits = text[1:]
    if not re.fullmatch(r"[0-9A-Fa-f]+", digits) or len(digits) not in (3, 4, 6, 8):
        return None
    if len(digits) in (3, 4):
        digits = "".join(c * 2 for c in digits)
    rgb, alpha = digits[:6], digits[6:] or "ff"
    return (int(alpha, 16) << 24) | int(rgb, 16)


def channels(argb: int) -> tuple[int, int, int, int]:
    return (argb >> 24) & 0xFF, (argb >> 16) & 0xFF, (argb >> 8) & 0xFF, argb & 0xFF


def pack(a: int, r: int, g: int, b: int) -> int:
    return (a << 24) | (r << 16) | (g << 8) | b


def lerp(x: int, y: int, t: float) -> int:
    # Swift's .rounded() rounds halves away from zero; values here are never negative.
    return max(0, min(255, int(x + (y - x) * t + 0.5)))


def mix(first: int, second: int, t: float) -> int:
    return pack(*(lerp(x, y, t) for x, y in zip(channels(first), channels(second))))


def contrast(color: int) -> int:
    _, r, g, b = channels(color)
    return 0xFF000000 if (299 * r + 587 * g + 114 * b) // 1000 > 150 else 0xFFFFFFFF


def format_hex(argb: int) -> str:
    a, r, g, b = channels(argb)
    return f"#{r:02X}{g:02X}{b:02X}" + ("" if a == 255 else f"{a:02X}")


@dataclass
class Context:
    variables: dict[str, str]
    base: dict[str, int]
    keys: set[str]
    resolving: list[str] = field(default_factory=list)
    cache: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class Parser:
    """expr := #hex | transparent | $var | @native.key | name(arg, ...); arg := expr | number[%]"""

    FUNCTIONS = {"mix": 3, "alpha": 2, "lighten": 2, "darken": 2, "contrast": 1}

    def __init__(self, text: str, context: Context, depth: int):
        self.text, self.index, self.context, self.depth = text, 0, context, depth

    def fail(self, message: str) -> ThemeError:
        return ThemeError(f"{message} in '{self.text}'")

    def skip(self) -> None:
        while self.index < len(self.text) and self.text[self.index] == " ":
            self.index += 1

    def token(self) -> str:
        self.skip()
        match = re.compile(r"[#$@]?[A-Za-z0-9_.%-]+").match(self.text, self.index)
        if not match:
            raise self.fail("expected a value")
        self.index = match.end()
        return match.group(0)

    def number(self) -> float:
        word = self.token()
        if not NUMBER_PATTERN.match(word):
            raise self.fail(f"'{word}' is not a number")
        value = float(word[:-1]) / 100.0 if word.endswith("%") else float(word)
        if not 0.0 <= value <= 1.0:
            raise self.fail(f"{word} is outside 0…1")
        return value

    def expect(self, char: str) -> None:
        self.skip()
        if self.index >= len(self.text) or self.text[self.index] != char:
            raise self.fail(f"expected '{char}'")
        self.index += 1

    def color(self) -> int:
        if self.depth > MAX_DEPTH:
            raise self.fail("too deeply nested")
        word = self.token()
        if word.startswith("$"):
            return resolve_variable(word[1:], self.context, self.depth + 1)
        if word.startswith("@"):
            path = word[1:]
            if self.context.keys and path not in self.context.keys:
                raise self.fail(f"unknown native key '{path}'")
            if path in self.context.base:
                return self.context.base[path]
            self.context.warnings.append(f"@{path} has no base value here; grey used")
            return 0xFF808080
        if word.startswith("#") or word == "transparent":
            value = parse_hex(word)
            if value is None:
                raise self.fail(f"'{word}' is not a colour")
            return value
        if word not in self.FUNCTIONS:
            raise self.fail(f"unknown function '{word}'")
        self.expect("(")
        name = word
        if name == "contrast":
            result = contrast(self.nested())
        elif name == "mix":
            first = self.nested()
            self.expect(",")
            second = self.nested()
            self.expect(",")
            result = mix(first, second, self.number())
        else:
            base = self.nested()
            self.expect(",")
            amount = self.number()
            if name == "alpha":
                result = (base & 0x00FFFFFF) | (lerp(0, 255, amount) << 24)
            else:
                target = 0xFFFFFF if name == "lighten" else 0x000000
                result = mix(base, (base & 0xFF000000) | target, amount)
        self.expect(")")
        return result

    def nested(self) -> int:
        self.depth += 1
        try:
            return self.color()
        finally:
            self.depth -= 1

    def parse(self) -> int:
        value = self.color()
        self.skip()
        if self.index != len(self.text):
            raise self.fail("unexpected text at the end")
        return value


def evaluate(text, context: Context, depth: int = 0) -> int:
    if not isinstance(text, str):
        raise ThemeError(f"colour must be a string, got {json.dumps(text)}")
    text = text.strip()
    if not text or len(text) > MAX_EXPRESSION:
        raise ThemeError(f"colour expression must be 1…{MAX_EXPRESSION} characters")
    return Parser(text, context, depth).parse()


def resolve_variable(name: str, context: Context, depth: int) -> int:
    if name in context.cache:
        return context.cache[name]
    if name not in context.variables:
        raise ThemeError(f"unknown variable ${name}")
    if name in context.resolving:
        raise ThemeError("variable cycle: " + " -> ".join("$" + n for n in context.resolving + [name]))
    context.resolving.append(name)
    try:
        value = evaluate(context.variables[name], context, depth)
    finally:
        context.resolving.pop()
    context.cache[name] = value
    return value


def load_keys() -> set[str]:
    return set(json.loads(KEYS_FILE.read_text(encoding="utf-8"))) if KEYS_FILE.exists() else set()


def object_field(source: dict, name: str, where: str) -> dict:
    value = source.get(name, {})
    if not isinstance(value, dict):
        raise ThemeError(f"{where}{name} must be an object")
    return value


@dataclass
class Resolved:
    base: str
    accent: int | None
    native: dict[str, int]
    wallpaper: list[int]
    rotation: int
    warnings: list[str]


def check_document(document) -> None:
    if not isinstance(document, dict):
        raise ThemeError("a theme is a JSON object")
    version = document.get("vgtheme")
    if isinstance(version, bool) or not isinstance(version, (int, float)) or version != FORMAT_VERSION:
        raise ThemeError(f'"vgtheme" must be {FORMAT_VERSION}')
    theme_id = document.get("id")
    if not isinstance(theme_id, str) or not ID_PATTERN.match(theme_id):
        raise ThemeError('"id" must be 1–64 of a-z 0-9 . _ - starting with a letter or digit')
    name = document.get("name")
    if isinstance(name, dict):
        if not name or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in name.items()):
            raise ThemeError('"name" must be a string or {"en": …, "ru": …}')
    elif not isinstance(name, str) or not name.strip():
        raise ThemeError('"name" must be a string or {"en": …, "ru": …}')
    if document.get("base", "inherit") not in BASES:
        raise ThemeError('"base" must be one of ' + ", ".join(BASES))
    for text_field in ("author", "description"):
        if text_field in document and not isinstance(document[text_field], str):
            raise ThemeError(f'"{text_field}" must be a string')
    variants = object_field(document, "variants", "")
    for variant in variants:
        if variant not in ("light", "dark"):
            raise ThemeError(f'variants may only be "light" and "dark", not "{variant}"')
    for where, block in [("", document)] + [(f"variants.{k}.", v) for k, v in variants.items()]:
        if not isinstance(block, dict):
            raise ThemeError(f"{where[:-1]} must be an object")
        variables = object_field(block, "vars", where)
        if len(variables) > MAX_VARS:
            raise ThemeError(f"{where}vars: at most {MAX_VARS}")
        for name in variables:
            if not VAR_PATTERN.match(name):
                raise ThemeError(f"{where}vars: '{name}' is not a valid name")
        for name in object_field(block, "colors", where):
            if name not in ALIAS_NAMES:
                raise ThemeError(f"{where}colors: unknown name '{name}' (see `vgtheme.py aliases`)")
        if len(object_field(block, "native", where)) > MAX_NATIVE:
            raise ThemeError(f"{where}native: at most {MAX_NATIVE} keys")


def merged_block(document: dict, dark: bool) -> dict:
    """The document with variants.light or variants.dark laid over it."""
    variant = object_field(document, "variants", "").get("dark" if dark else "light", {})
    result = {}
    for name in ("vars", "colors", "native"):
        result[name] = {**object_field(document, name, ""), **object_field(variant, name, "")}
    for name in ("accent", "wallpaper"):
        if name in variant:
            result[name] = variant[name]
        elif name in document:
            result[name] = document[name]
    return result


def resolve(document, dark: bool, base_values: dict[str, int] | None = None, keys: set[str] | None = None) -> Resolved:
    check_document(document)
    keys = load_keys() if keys is None else keys
    block = merged_block(document, dark)
    context = Context(variables=block["vars"], base=base_values or {}, keys=keys)

    def value(text, where: str) -> int:
        try:
            return evaluate(text, context)
        except ThemeError as error:
            raise ThemeError(f"{where}: {error}") from None

    accent = value(block["accent"], "accent") if "accent" in block else None
    colors = dict(block["colors"])
    for target, source, template in DERIVED:
        if target not in colors and source in colors:
            colors[target] = template.format(colors[source])
    native: dict[str, int] = {}
    for name, targets in ALIASES:
        if name in colors:
            resolved = value(colors[name], f"colors.{name}")
            for target in targets:
                native[target] = resolved
    for path, text in block["native"].items():
        if keys and path not in keys:
            context.warnings.append(f"native.{path} is not a Telegram theme key; ignored")
            continue
        native[path] = value(text, f"native.{path}")
    wallpaper, rotation = [], 0
    if "wallpaper" in block:
        spec = block["wallpaper"]
        if isinstance(spec, str):
            spec = {"colors": [spec]}
        elif isinstance(spec, list):
            spec = {"colors": spec}
        if not isinstance(spec, dict) or not isinstance(spec.get("colors"), list) or not 1 <= len(spec["colors"]) <= 4:
            raise ThemeError("wallpaper must be a colour, a list of 1–4 colours or {colors, rotation}")
        wallpaper = [value(c, f"wallpaper[{i}]") | 0xFF000000 for i, c in enumerate(spec["colors"])]
        rotation = spec.get("rotation", 0)
        if isinstance(rotation, bool) or not isinstance(rotation, (int, float)) or rotation != int(rotation) or not 0 <= rotation < 360:
            raise ThemeError("wallpaper.rotation must be a whole number 0…359")
        rotation = int(rotation)
    for name in block["vars"]:
        try:
            resolve_variable(name, context, 0)
        except ThemeError as error:
            raise ThemeError(f"vars.{name}: {error}") from None
    return Resolved(document.get("base", "inherit"), accent, native, wallpaper, rotation, context.warnings)


def load(path: Path):
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise ThemeError(f"larger than {MAX_FILE_BYTES // 1024} KB")
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ThemeError(f"not valid JSON: {error}") from None


def command_validate(paths: list[Path]) -> int:
    keys, failed, ids = load_keys(), 0, {}
    for path in paths:
        try:
            document = load(path)
            warnings = []
            for dark in (False, True):
                warnings += resolve(document, dark, keys=keys).warnings
            if document["id"] in ids:
                raise ThemeError(f"id '{document['id']}' is also used by {ids[document['id']]}")
            ids[document["id"]] = path.name
            print(f"ok    {path}")
            for warning in dict.fromkeys(warnings):
                print(f"      warning: {warning}")
        except ThemeError as error:
            failed += 1
            print(f"FAIL  {path}: {error}")
    return 1 if failed else 0


def command_resolve(path: Path, dark: bool) -> int:
    resolved = resolve(load(path), dark)
    print(json.dumps({
        "base": resolved.base,
        "accent": format_hex(resolved.accent) if resolved.accent is not None else None,
        "native": {k: format_hex(v) for k, v in sorted(resolved.native.items())},
        "wallpaper": [format_hex(c) for c in resolved.wallpaper],
        "rotation": resolved.rotation,
        "warnings": resolved.warnings,
    }, indent=2, ensure_ascii=False))
    return 0


BUILTIN_ORDER = ["void-graphite", "nord", "dracula", "oled-violet", "sakura"]
THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"


def swift_builtins() -> str:
    """AyuThemeEngineBuiltins.swift: the themes/ files the app ships, verbatim."""
    lines = [
        "import Foundation",
        "",
        "// Generated by `python tools/vgtheme.py builtins` from themes/*.vgtheme; do not edit by hand.",
        "enum AyuThemeEngineBuiltins {",
        "    static let all: [String] = [",
    ]
    for index, theme_id in enumerate(BUILTIN_ORDER):
        text = (THEMES_DIR / f"{theme_id}.vgtheme").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
        if '"""#' in text:
            raise ThemeError(f"{theme_id}: the text cannot contain a closing raw-string delimiter")
        lines.append('        #"""')
        lines.extend(("        " + line) if line else "" for line in text.split("\n"))
        lines.append('        """#' + ("," if index < len(BUILTIN_ORDER) - 1 else ""))
    lines += ["    ]", "}", ""]
    return "\n".join(lines)


def command_aliases() -> int:
    print("| Name | Telegram keys |\n|---|---|")
    for name, targets in ALIASES:
        print(f"| `{name}` | " + ", ".join(f"`{t}`" for t in targets) + " |")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("paths", type=Path, nargs="+")
    show = sub.add_parser("resolve")
    show.add_argument("path", type=Path)
    show.add_argument("--dark", action="store_true")
    sub.add_parser("aliases")
    sub.add_parser("builtins", help="print AyuThemeEngineBuiltins.swift")
    args = parser.parse_args(argv)
    if args.command == "builtins":
        sys.stdout.write(swift_builtins())
        return 0
    if args.command == "validate":
        return command_validate(args.paths)
    if args.command == "resolve":
        return command_resolve(args.path, args.dark)
    return command_aliases()


if __name__ == "__main__":
    sys.exit(main())
