#!/usr/bin/env python3
"""Create and check .ayutheme files. The rules match AyuTheme.validate() in the app."""
import argparse
import base64
import binascii
import json
from pathlib import Path
import re
import sys

FORMAT = "ayu-theme-1"
MAXIMUM_FILE_BYTES = 8 * 1024 * 1024
MAXIMUM_FONT_BYTES = 4 * 1024 * 1024
MAXIMUM_FONT_COUNT = 3
BUILT_IN_FONTS = ("golos", "handjet", "plex", "system")
FONT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true")
ID_PATTERN = r"[a-z0-9_-]{1,64}"
SECTIONS = {
    "palette": {"dark": str, "light": str},
    "shapes": {"corners": str, "panels": str, "tabBar": str},
    "fonts": {"body": str, "title": str, "label": str},
    "icons": {"grid": int},
    "avatars": {"mosaic": int, "gray": bool},
    "media": {"gray": bool, "grid": int, "pickers": bool},
    "photos": {"gray": bool, "grid": int},
    "animation": {"stepsPerSecond": int},
    "chat": {"dots": bool, "bubbleCorner": int, "wallpaperGray": bool},
}
DEFAULTS = {
    "palette": {"dark": "#000000", "light": "#FFFFFF"},
    "shapes": {"corners": "square", "panels": "flat", "tabBar": "flat"},
    "fonts": {"body": "golos", "title": "handjet", "label": "plex"},
    "icons": {"grid": 1},
    "avatars": {"mosaic": 24, "gray": True},
    "media": {"gray": True, "grid": 1, "pickers": True},
    "photos": {"gray": False, "grid": 0},
    "animation": {"stepsPerSecond": 20},
    "chat": {"dots": True, "bubbleCorner": 6, "wallpaperGray": False},
}
CHOICES = {("shapes", "corners"): ("square", "stock"), ("shapes", "panels"): ("flat", "stock"), ("shapes", "tabBar"): ("flat", "stock")}
RANGES = {("icons", "grid"): (0, 4), ("media", "grid"): (0, 8), ("photos", "grid"): (0, 8), ("chat", "bubbleCorner"): (2, 16)}


def luma(value):
    number = int(value[1:], 16)
    red, green, blue = (number >> 16) & 0xff, (number >> 8) & 0xff, number & 0xff
    return (red * 0.2126 + green * 0.7152 + blue * 0.0722) / 255.0


def font_errors(theme):
    fonts = theme.get("customFonts", [])
    if not isinstance(fonts, list):
        return ["customFonts must be a list"], []
    found, identifiers = [], []
    if len(fonts) > MAXIMUM_FONT_COUNT:
        found.append(f"customFonts can hold at most {MAXIMUM_FONT_COUNT} fonts")
    for font in fonts:
        if not isinstance(font, dict):
            found.append("each custom font must be an object")
            continue
        identifier = font.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(ID_PATTERN, identifier) or identifier in BUILT_IN_FONTS:
            found.append(f"custom font id {identifier!r} is not valid")
        elif identifier in identifiers:
            found.append(f"custom font id {identifier} is used twice")
        else:
            identifiers.append(identifier)
        try:
            data = base64.b64decode(font.get("file") or "", validate=True)
        except (binascii.Error, TypeError, ValueError):
            found.append(f"custom font {identifier}: file is not base64")
            continue
        if not data:
            found.append(f"custom font {identifier}: file is missing")
        elif len(data) > MAXIMUM_FONT_BYTES:
            found.append(f"custom font {identifier}: larger than {MAXIMUM_FONT_BYTES} bytes")
        elif data[:4] not in FONT_MAGIC:
            found.append(f"custom font {identifier}: not a TrueType or OpenType font")
    return found, identifiers


def errors(theme):
    """Everything wrong with a parsed theme. Unknown keys are reported: the app ignores them, so they are typos."""
    if not isinstance(theme, dict):
        return ["the file must hold a JSON object"]
    found = []
    if theme.get("format") != FORMAT:
        found.append(f"format must be {FORMAT}")
    identifier = theme.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(ID_PATTERN, identifier):
        found.append("id must be 1-64 characters: a-z, 0-9, _ or -")
    elif identifier == "pixel":
        found.append("id pixel belongs to the built-in theme")
    for key, limit in (("name", 64), ("author", 128), ("version", 32)):
        value = theme.get(key)
        if not isinstance(value, str) or not 1 <= len(value) <= limit:
            found.append(f"{key} must be 1-{limit} characters")
    description = theme.get("description", "")
    if not isinstance(description, str) or len(description) > 512:
        found.append("description must be at most 512 characters")
    for key in theme:
        if key not in SECTIONS and key not in ("format", "id", "name", "author", "version", "description", "customFonts"):
            found.append(f"unknown key {key}")
    merged = {}
    for section, fields in SECTIONS.items():
        values = theme.get(section, {})
        if not isinstance(values, dict):
            found.append(f"{section} must be an object")
            values = {}
        for key, value in values.items():
            expected = fields.get(key)
            if expected is None:
                found.append(f"unknown key {section}.{key}")
            elif type(value) is not expected:
                found.append(f"{section}.{key} must be {expected.__name__}")
        merged[section] = {**DEFAULTS[section], **{key: value for key, value in values.items() if type(value) is fields.get(key)}}
    for key in ("dark", "light"):
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", merged["palette"][key]):
            found.append(f"palette.{key} must look like #RRGGBB")
    if not any("palette" in item for item in found) and luma(merged["palette"]["light"]) - luma(merged["palette"]["dark"]) < 0.4:
        found.append("palette.light must be clearly brighter than palette.dark: text would be unreadable")
    problems, custom = font_errors(theme)
    found.extend(problems)
    for key in ("body", "title", "label"):
        if merged["fonts"][key] not in BUILT_IN_FONTS and merged["fonts"][key] not in custom:
            found.append(f"fonts.{key} must be one of {', '.join(BUILT_IN_FONTS + tuple(custom))}")
    for (section, key), choices in CHOICES.items():
        if merged[section][key] not in choices:
            found.append(f"{section}.{key} must be one of {', '.join(choices)}")
    for (section, key), (low, high) in RANGES.items():
        if not low <= merged[section][key] <= high:
            found.append(f"{section}.{key} must be {low}-{high}")
    if merged["avatars"]["mosaic"] != 0 and not 8 <= merged["avatars"]["mosaic"] <= 64:
        found.append("avatars.mosaic must be 0 or 8-64")
    if merged["animation"]["stepsPerSecond"] != 0 and not 5 <= merged["animation"]["stepsPerSecond"] <= 60:
        found.append("animation.stepsPerSecond must be 0 or 5-60")
    return found


def check_file(path):
    data = path.read_bytes()
    if len(data) > MAXIMUM_FILE_BYTES:
        return [f"the file is larger than {MAXIMUM_FILE_BYTES} bytes"]
    try:
        theme = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"not valid JSON: {error}"]
    return errors(theme)


def write_theme(path, theme):
    path.write_text(json.dumps(theme, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_font(theme_path, font_path, identifier):
    """Embeds a font in a theme, replacing a font with the same id. Check the font's license first."""
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    data = font_path.read_bytes()
    fonts = [font for font in theme.get("customFonts", []) if font.get("id") != identifier]
    fonts.append({"id": identifier, "file": base64.b64encode(data).decode("ascii")})
    theme["customFonts"] = fonts
    problems = errors(theme)
    if problems:
        raise SystemExit("\n".join(problems))
    write_theme(theme_path, theme)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check theme files")
    check.add_argument("files", type=Path, nargs="+")
    new = commands.add_parser("new", help="write a theme with every value set to its default")
    new.add_argument("file", type=Path)
    new.add_argument("--id", required=True)
    new.add_argument("--name", required=True)
    new.add_argument("--author", required=True)
    font = commands.add_parser("add-font", help="embed a .ttf or .otf font in a theme")
    font.add_argument("theme", type=Path)
    font.add_argument("font", type=Path)
    font.add_argument("--id", required=True, help="the name to use in fonts.body, fonts.title or fonts.label")
    arguments = parser.parse_args()

    if arguments.command == "new":
        if arguments.file.exists():
            raise SystemExit(f"{arguments.file} already exists")
        theme = {"format": FORMAT, "id": arguments.id, "name": arguments.name, "author": arguments.author, "version": "1.0", "description": "", **DEFAULTS}
        problems = errors(theme)
        if problems:
            raise SystemExit("\n".join(problems))
        write_theme(arguments.file, theme)
        print(f"Wrote {arguments.file}")
        return

    if arguments.command == "add-font":
        add_font(arguments.theme, arguments.font, arguments.id)
        print(f"Added {arguments.font.name} to {arguments.theme} as {arguments.id}")
        return

    failed = False
    for path in arguments.files:
        problems = check_file(path)
        print(f"{path}: {'OK' if not problems else 'FAILED'}")
        for problem in problems:
            print(f"  {problem}")
        failed = failed or bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
