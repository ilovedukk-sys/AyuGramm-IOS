# Pixel style, stage 1

`patches/ayugram-pixel-style.patch` applies last. `AyuPixelStyle.isEnabled` in `submodules/Display/Source/AyuPixelStyle.swift` turns the whole block off. There is no setting in the app yet.

## What changes

- **Color:** `UIColor(rgb:)`, `UIColor(argb:)` and `UIColor(hexString:)` return grayscale. This covers themes, peer colors and color wallpapers. Destructive actions are gray, not red.
- **Accent:** black in day themes, white in night. Saved accent colors are ignored.
- **Bubbles:** Day bubble set in every day theme. Incoming bubbles are white with a black outline. Outgoing bubbles are black, or white with black content at night. Corners are cut in two steps, with no tails.
- **Text:** `Font.regular` and its siblings, and `Font.with` for the regular and round designs, use Golos Text. Monospace and camera fonts are unchanged.
- **Titles:** the chat list title, chat title and `NavigationTitleNode` use Handjet through `Font.pixelTitle`.

## Not in this stage

- Code that calls `UIFont.systemFont` directly keeps the system font.
- `UIColor(red:green:blue:alpha:)`, `UIColor(white:alpha:)`, system colors, image assets and media keep their own colors.
- Image wallpapers already saved by a user stay in place.
- The tinted night theme only becomes grayscale: its bubbles and accent are not reworked.
- Avatars, icons, glass panels, button glow, mono labels, mosaics and animations.

## Device checks

No build of this block has been compiled or run yet.

1. The app builds, including the extensions. Extensions do not bundle the fonts and must fall back to the system font.
2. Golos Text and Handjet load, and weights differ between regular and semibold. `UIAppFonts` lists them in `Telegram/BUILD`.
3. Text in bubbles, chat list rows and buttons is not clipped and sits on its baseline.
4. Emoji, Arabic, Hebrew and CJK text fall back correctly.
5. Bubble corners match in all neighbor positions, with incoming outlines, with photos and in replies.
6. Night theme: controls in outgoing bubbles (voice, file, poll, reactions) are visible on white.
7. Scrolling a long chat list stays smooth with the custom font.

## Fonts

Golos Text and Handjet come from `google/fonts` under the SIL Open Font License. The license texts are in `assets/fonts/`.
