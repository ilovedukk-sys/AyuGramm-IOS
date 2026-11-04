#!/usr/bin/env python3
"""List every native Telegram-iOS theme key that a .vgtheme `native` block can set.

Reads PresentationTheme.swift and PresentationThemeCodable.swift of the pinned upstream
tree and writes themes/telegram-keys.json: {"chat.message.outgoing.bubble.withoutWp.bg":
"color", ...}. The app checks keys against the live theme too; this file is for authors,
docs and tools/vgtheme.py.

    python tools/vgtheme_keys.py <Telegram-iOS checkout> [--out themes/telegram-keys.json]
"""
import argparse
import json
import re
from pathlib import Path

SOURCES = "submodules/TelegramPresentationData/Sources"


def class_properties(theme_source: str) -> dict[str, dict[str, str]]:
    """Class name -> {property: type} for the theme classes."""
    result: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"public (?:final )?class (\w+)[^{]*\{", theme_source):
        name = match.group(1)
        depth, index = 1, match.end()
        while depth and index < len(theme_source):
            depth += {"{": 1, "}": -1}.get(theme_source[index], 0)
            index += 1
        body = theme_source[match.end():index]
        props: dict[str, str] = {}
        for prop in re.finditer(r"^\s*public let (\w+): ([\w.\[\]]+)", body, re.M):
            props[prop.group(1)] = prop.group(2)
        result[name] = props
    return result


def codable_blocks(codable_source: str) -> dict[str, str]:
    """Type name -> body of its `extension X: Codable { ... }`."""
    blocks: dict[str, str] = {}
    for match in re.finditer(r"extension ([\w.]+): (?:@retroactive )?Codable \{", codable_source):
        depth, index = 1, match.end()
        while depth and index < len(codable_source):
            depth += {"{": 1, "}": -1}.get(codable_source[index], 0)
            index += 1
        blocks[match.group(1).split(".")[-1]] = codable_source[match.end():index]
    return blocks


def coding_keys(block: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    enum = re.search(r"enum CodingKeys: String, CodingKey \{(.*?)\}", block, re.S)
    if not enum:
        return keys
    for case in re.finditer(r"case `?(\w+)`?(?:\s*=\s*\"([^\"]+)\")?", enum.group(1)):
        keys[case.group(1)] = case.group(2) or case.group(1)
    return keys


def encode_body(block: str) -> str:
    match = re.search(r"func encode\(to encoder: Encoder\) throws \{", block)
    if not match:
        return ""
    depth, index = 1, match.end()
    while depth and index < len(block):
        depth += {"{": 1, "}": -1}.get(block[index], 0)
        index += 1
    return block[match.end():index]


def walk(type_name: str, prefix: str, blocks, props, out: dict[str, str], seen=()):
    block = blocks.get(type_name)
    if block is None or type_name in seen:
        return
    keys = coding_keys(block)
    body = encode_body(block)
    for color in re.finditer(r"encodeColor\(&\w+, [^,]+, \.`?(\w+)`?\)", body):
        out[prefix + keys.get(color.group(1), color.group(1))] = "color"
    for colors in re.finditer(r"encodeColorList\(&\w+, [^,]+, \.`?(\w+)`?\)", body):
        out[prefix + keys.get(colors.group(1), colors.group(1))] = "colorList"
    for nested in re.finditer(r"\w+\.encode\(self\.(\w+)(?:\.\w+)?, forKey: \.`?(\w+)`?\)", body):
        prop, key = nested.group(1), nested.group(2)
        path = prefix + keys.get(key, key)
        prop_type = props.get(type_name, {}).get(prop, "")
        if prop_type in blocks and prop_type != type_name and coding_keys(blocks[prop_type]):
            walk(prop_type, path + ".", blocks, props, out, seen + (type_name,))
        elif prop_type.endswith("TelegramWallpaper") or prop_type == "TelegramWallpaper?":
            out[path] = "wallpaper"
        else:
            out[path] = "value"
    # Keys the decoder reads but the encoder may skip (optional colours with fallbacks).
    for color in re.finditer(r"decodeColor\(values, \.`?(\w+)`?", block):
        out.setdefault(prefix + keys.get(color.group(1), color.group(1)), "color")
    for wallpaper in re.finditer(r"TelegramWallpaperStandardizedCodable\(self\.\w+\), forKey: \.`?(\w+)`?\)", body):
        out[prefix + keys.get(wallpaper.group(1), wallpaper.group(1))] = "wallpaper"
    # Optional members encoded through `if let`.
    for nested in re.finditer(r"\w+\.encode(?:IfPresent)?\((\w+), forKey: \.`?(\w+)`?\)", body):
        local, key = nested.group(1), nested.group(2)
        path = prefix + keys.get(key, key)
        prop_type = props.get(type_name, {}).get(local, "").rstrip("?")
        if prop_type in blocks:
            walk(prop_type, path + ".", blocks, props, out, seen + (type_name,))
        elif path not in out:
            out[path] = "value"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "themes" / "telegram-keys.json")
    args = parser.parse_args()
    sources = args.source / SOURCES
    props = class_properties((sources / "PresentationTheme.swift").read_text(encoding="utf-8"))
    blocks = codable_blocks((sources / "PresentationThemeCodable.swift").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    walk("PresentationTheme", "", blocks, props, out)
    for meta in ("name", "basedOn", "dark"):
        out.pop(meta, None)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dict(sorted(out.items())), indent=1) + "\n", encoding="utf-8", newline="\n")
    colors = sum(1 for kind in out.values() if kind == "color")
    print(f"{len(out)} keys ({colors} colours) -> {args.out}")


if __name__ == "__main__":
    main()
