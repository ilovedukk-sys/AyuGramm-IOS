# Themes

A theme is a `.ayutheme` file: a JSON file with values for the style and, optionally, fonts. It holds no code, so installing one cannot run a program. A font is the one part of a theme that the system has to parse as a binary file, so the install prompt says when a theme contains fonts: install those only from authors you trust. Themes are separate from plugins because a theme must be known before the first screen, while plugins belong to an account and load after sign-in.

## Installing

- Tap a `.ayutheme` file in a chat, or open one from Files.
- Or use **Settings → AyuGram Preferences → Themes → Install .ayutheme file**.

The app shows the name, author and description, then installs the file. A theme applies when the app restarts, because fonts, shapes and runtime hooks are set up at launch. **Standard look** on the same page turns the style off completely.

If the app dies within 20 seconds of launch three times in a row, the fourth launch uses the standard look and the Themes page says so. App extensions always use the standard look.

## Writing a theme

Only the header is required. Any other value keeps its default, which is the built-in Pixel theme.

```json
{
  "format": "ayu-theme-1",
  "id": "my_theme",
  "name": "My Theme",
  "author": "@me",
  "version": "1.0",
  "description": "What it looks like.",
  "palette": { "dark": "#000000", "light": "#FFFFFF" },
  "shapes": { "corners": "square", "panels": "flat", "tabBar": "flat" },
  "fonts": { "body": "golos", "title": "handjet", "label": "plex" },
  "icons": { "grid": 1 },
  "avatars": { "mosaic": 24, "gray": true },
  "media": { "gray": true, "grid": 1, "pickers": true },
  "photos": { "gray": false, "grid": 0 },
  "animation": { "stepsPerSecond": 20 },
  "chat": { "dots": true, "bubbleCorner": 6, "wallpaperGray": false }
}
```

| Value | Range | Meaning |
|---|---|---|
| `id` | `a-z 0-9 _ -`, up to 64 | A file with the same id replaces the installed one. `pixel` is reserved. |
| `name`, `author`, `version` | up to 64, 128 and 32 characters | Shown in the app. |
| `description` | up to 512 characters | Optional. |
| `palette.dark`, `palette.light` | `#RRGGBB` | Interface colors are reduced to their brightness and mapped between these two: black becomes `dark`, white becomes `light`. `light` must be clearly brighter than `dark`. |
| `shapes.corners` | `square`, `stock` | Square layers, circles and stepped message bubbles, or the regular rounded ones. |
| `shapes.panels` | `flat`, `stock` | Flat bordered panels without Liquid Glass motion, or the regular glass. Flat panels are always square. |
| `shapes.tabBar` | `flat`, `stock` | The edge-to-edge bar with bitmap icons, or the regular tab bar. `flat` also turns on the drawn switches. |
| `fonts.body`, `fonts.title`, `fonts.label` | `golos`, `handjet`, `plex`, `system` or a custom font id | Message and list text, titles, and dates, counters and labels. |
| `customFonts` | up to 3, each up to 4 MB | The theme's own `.ttf` or `.otf` fonts. Add them with `add-font`. Check that the license allows sharing them. |
| `icons.grid` | 0-4 | The size of an icon pixel in points. 0 keeps icons sharp. |
| `avatars.mosaic` | 0 or 8-64 | Cells on a side of the avatar mosaic. 0 keeps the full resolution. |
| `avatars.gray` | true, false | Gray avatars. |
| `media.gray` | true, false | Stickers, custom emoji, reaction icons and animated icons lose their colors and take the palette's light color. |
| `media.grid` | 0-8 | Multiplies their pixel size. 0 keeps the full resolution. |
| `media.pickers` | true, false | Whether the sticker and emoji panels follow `media`. |
| `photos.gray` | true, false | Gray photos and videos inside chats. A photo opened full screen keeps its original look. |
| `photos.grid` | 0-8 | The size of a photo pixel in points. 0 keeps the full resolution. Videos stay sharp. |
| `animation.stepsPerSecond` | 0 or 5-60 | How many values an animation jumps through per second. 0 keeps animations smooth. |
| `chat.dots` | true, false | The dot grid in chats. |
| `chat.bubbleCorner` | 2-16 | The size of the stepped bubble corners in points, with square corners. |
| `chat.wallpaperGray` | true, false | Gray wallpapers, including ones you have set yourself. |

Check a file before sharing it. The script applies the same rules as the app and also reports misspelled keys, which the app would ignore:

```bash
python3 tools/ayutheme.py check my_theme.ayutheme
```

Start from every default:

```bash
python3 tools/ayutheme.py new my_theme.ayutheme --id my_theme --name "My Theme" --author @me
```

Embed a font, then choose it in `fonts`:

```bash
python3 tools/ayutheme.py add-font my_theme.ayutheme MyFont.ttf --id myfont
```

Examples are in [themes](../themes).

## Limits of this version

- The palette covers colors that go through `UIColor(rgb:)`. Colors from `UIColor(white:)` and system colors keep their own.
- A palette tints gray stickers and photos by its light color only, so their dark parts stay black rather than taking `palette.dark`.
- `shapes` choose between the two looks that exist in the app. A theme cannot define a new corner radius or tab bar layout.
- Combinations that mix `square` and `stock` shapes have had the least testing.
- A photo opened full screen, profile photos in their gallery and other viewers keep their original look.
