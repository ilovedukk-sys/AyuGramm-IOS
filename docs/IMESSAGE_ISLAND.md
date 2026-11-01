# Messages style and Dynamic Island

`patches/ayugram-imessage-island.patch` adds both. Neither has been run on a device yet.

## Dynamic Island and Live Activities

| What | iOS 26 | iOS 16.2 to 18 |
|---|---|---|
| Downloads | System progress UI, keeps downloading after the app is closed | Live Activity |
| Media uploads | System progress UI (Telegram's own code) | Live Activity |
| Voice chats | Live Activity with a timer and microphone state | Same |
| Calls without CallKit | Live Activity with a timer | Same |
| Calls through CallKit | Shown by the system | Same |
| Live location | Live Activity with a countdown | Same |

The system progress UI is `BGContinuedProcessingTask`, the mechanism Apple provides for long transfers. iOS draws it, so the app sets only its title, subtitle and progress. iOS shows it only outside the app.

A Live Activity is updated by the running app, not by push, because a sideloaded build has no working APNs. On iOS 18 and older, iOS suspends the app about 30 seconds after it is closed, and the progress stops until it is opened again.

Live Activities are drawn by the existing widget extension, so **the install must keep the app's extensions**. Some signing tools strip them. If the extension is gone, Live Activities do not appear.

## Messages style

**Settings → AyuGram → Appearance+ → iMessage style** is on by default and applies after a restart.

Done:

- Blue outgoing and gray incoming bubbles, a plain white or black background, following the system light or dark appearance.
- Uniform 18 pt bubble corners, with the tail on the last bubble of a group.
- No time or checks on bubbles. **Delivered** or **Read** appears under the last outgoing message. Channel posts keep their views and time, and saved deleted messages keep their mark.
- Dates and service messages as plain gray text.
- Chat list: 52 pt avatars, a blue unread dot left of the avatar, no counters or checks, and a chevron after the date.
- A plus instead of the paper clip.
- Chat header: the avatar centered above a small name, without the glass pill. A status line appears only while someone is typing. Private chats get a video call button on the right.
- Reactions are tapbacks on the corner of the bubble. A single reaction shows no count or avatar.
- Swiping the chat left reveals message times: outgoing messages move aside and incoming ones stay. This replaces swipe to reply, so reply from the message's context menu.
- No tab bar on the chat list when Contacts and Calls are hidden, which is the default. Appearance+ can bring those tabs back, and the bar with them. A gear in the chat list header opens Settings, where the bar is shown as the way back.

The app icon and name stay AyuGram. Apple's icon is not copied.
