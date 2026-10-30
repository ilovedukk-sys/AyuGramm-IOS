# Pixel style

Two patches apply last, in this order: `patches/ayugram-pixel-style.patch` and `patches/ayugram-pixel-ui.patch`. `AyuPixelStyle.isEnabled` in `submodules/Display/Source/AyuPixelStyle.swift` turns the Swift side off, and `AyuPixelStyleEnabled` in `submodules/AppBundle/Sources/AppBundle/AppBundle.m` turns the Objective-C side off. Keep the two values equal. There is no setting in the app yet.

## What changes

- **Color:** `UIColor(rgb:)`, `UIColor(argb:)` and `UIColor(hexString:)` return grayscale. This covers themes, peer colors and color wallpapers. Destructive actions are gray, not red.
- **Accent:** black in day themes, white in night. Saved accent colors are ignored.
- **Corners:** `CALayer.cornerRadius` and `UIBezierPath` rounded rectangles are replaced at runtime, so layers and paths across the app are square. Circles from `GenerateImage.swift` are square too.
- **Bubbles:** Day bubble set in every day theme. Incoming bubbles are white with a black outline. Outgoing bubbles are black, or white with black content at night. Corners are cut in two steps, with no tails.
- **Panels:** the custom glass path is always used, and `GlassBackgroundView` draws a flat panel with a one point border.
- **Icons:** every asset of up to 64 pt loaded through `UIImage(bundleImageName:)` is redrawn on a one point grid in gray. Main tab icons are bitmaps.
- **Tab bar:** the flat bar runs edge to edge with a line on top. The selected cell is filled and its content inverted.
- **Avatars:** square, as a 24 x 24 gray mosaic.
- **Switches:** the drawn switch from `AyuMaterialControls`, which is forced on along with the rest of that option.
- **Text:** `Font.regular` and its siblings, and `Font.with` for the regular and round designs, use Golos Text. Monospace and camera fonts are unchanged.
- **Titles:** the chat list title, chat title and `NavigationTitleNode` use Handjet through `Font.pixelTitle`. The chat list title is larger and in capitals.
- **Labels:** chat list dates, message times, date headers, tab titles, folder tabs and list section headers use IBM Plex Mono through `Font.pixelLabel`.
- **Chat background:** a dot grid over the wallpaper.

## Not done

- The chat list title stays centered, and the settings profile keeps its stock layout.
- Folder tab titles are not in capitals, and the selected folder is not an inverted block.
- Button glow.
- Lottie animations other than the main tab icons, stickers, photos and videos keep their look.
- Shapes drawn directly with `fillEllipse`, `addArc` or `CGPath` stay round.
- Code that calls `UIFont.systemFont` directly keeps the system font.
- `UIColor(red:green:blue:alpha:)`, `UIColor(white:alpha:)` and system colors keep their own colors.
- Image wallpapers already saved by a user stay in place.
- The tinted night theme only becomes grayscale: its bubbles and accent are not reworked.

## Builds

Every push to `pixel-style-stage1` that changes the port starts `Native iOS port` in GitHub Actions as a `debug_arm64` build. The repository needs Actions enabled and the secrets `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`. The Bazel disk cache is saved after failed builds too and is bounded to 20 GB before compression, so the archive stays under the 10 GB limit of a cache entry. The first build has no cache. A change in `Display` rebuilds far more than a change in a screen module.

## Device checks

The second patch has not been compiled or run yet.

1. The app builds, including the extensions. Extensions do not bundle the fonts and must fall back to the system font.
2. All fonts load, and weights differ between regular and semibold. `UIAppFonts` lists them in `Telegram/BUILD`.
3. Text in bubbles, chat list rows and buttons is not clipped and sits on its baseline.
4. Emoji, Arabic, Hebrew and CJK text fall back correctly.
5. Bubble corners match in all neighbor positions, with incoming outlines, with photos and in replies.
6. Night theme: controls in outgoing bubbles (voice, file, poll, reactions) are visible on white.
7. Scrolling a long chat list stays smooth. Avatars and icons now go through extra image work.
8. Panels: icons and text stay visible on every panel, including over photos and video. Custom panel colors become opaque.
9. Icons stay readable at small sizes, and stretched or colored assets look right.
10. Round video messages, camera controls and the media editor still work when their layers are square.
11. The tab bar reaches the screen edges and hides its side and bottom borders on devices with and without a home indicator.

## Fonts

Golos Text, Handjet and IBM Plex Mono come from `google/fonts` under the SIL Open Font License. The license texts are in `assets/fonts/`.
