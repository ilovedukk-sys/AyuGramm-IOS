# Themes

A theme is a `.ayutheme` file: a small JSON file with values for the pixel style. It holds no code, so installing one cannot run anything. Themes are separate from plugins because a theme must be known before the first screen, while plugins belong to an account and load after sign-in.

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
  "fonts": { "body": "golos", "title": "handjet", "label": "plex" },
  "icons": { "grid": 1 },
  "avatars": { "mosaic": 24, "gray": true },
  "media": { "gray": true, "grid": 1 },
  "animation": { "stepsPerSecond": 20 },
  "chat": { "dots": true, "bubbleCorner": 6 }
}
```

| Value | Range | Meaning |
|---|---|---|
| `id` | `a-z 0-9 _ -`, up to 64 | A file with the same id replaces the installed one. `pixel` is reserved. |
| `name`, `author`, `version` | up to 64, 128 and 32 characters | Shown in the app. |
| `description` | up to 512 characters | Optional. |
| `palette.dark`, `palette.light` | `#RRGGBB` | Interface colors are reduced to their brightness and mapped between these two: black becomes `dark`, white becomes `light`. `light` must be clearly brighter than `dark`. |
| `fonts.body`, `fonts.title`, `fonts.label` | `golos`, `handjet`, `plex`, `system` | Message and list text, titles, and dates, counters and labels. |
| `icons.grid` | 0-4 | The size of an icon pixel in points. 0 keeps icons sharp. |
| `avatars.mosaic` | 0 or 8-64 | Cells on a side of the avatar mosaic. 0 keeps the full resolution. |
| `avatars.gray` | true, false | Gray avatars. |
| `media.gray` | true, false | Gray stickers, custom emoji, reaction icons and animated icons. |
| `media.grid` | 0-8 | Multiplies their pixel size. 0 keeps the full resolution. |
| `animation.stepsPerSecond` | 0 or 5-60 | How many values an animation jumps through per second. 0 keeps animations smooth. |
| `chat.dots` | true, false | The dot grid in chats. |
| `chat.bubbleCorner` | 2-16 | The size of the stepped bubble corners in points. |

Check a file before sharing it. The script applies the same rules as the app and also reports misspelled keys, which the app would ignore:

```bash
python3 tools/ayutheme.py check my_theme.ayutheme
```

Start from every default:

```bash
python3 tools/ayutheme.py new my_theme.ayutheme --id my_theme --name "My Theme" --author @me
```

Examples are in [themes](../themes).

## Limits of this version

- A theme is a variation of the pixel style. Square shapes, flat panels and the tab bar layout are not values yet.
- The palette covers colors that go through `UIColor(rgb:)`. Photos, videos and colors from `UIColor(white:)` or the system keep their own, and gray stickers stay gray rather than taking the palette.
- Fonts come from the four built into the app. A theme cannot bring its own.
- The sticker and emoji pickers are not affected.
