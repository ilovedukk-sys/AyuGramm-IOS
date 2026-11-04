# Движок тем VoidGram (.vgtheme)

**Настройки → VoidGram → Темы, цвета и бейджи → Темы VoidGram.** Тема — это JSON-файл
`.vgtheme`. В нём есть переменные, функции цвета, отдельные варианты для светлого и тёмного
режима, понятные имена и прямой доступ ко всем ~440 ключам темы Telegram-iOS.
Исходники: `patches/voidgram-theme-engine.patch`, эталонная реализация и валидатор —
`tools/vgtheme.py`, примеры — `themes/`.

## Как тема ложится на интерфейс

1. **База.** Берётся текущая тема Telegram или, если указано `"base"`, встроенная
   (`day`, `classic`, `night`, `tinted`).
2. **Вариант.** Если у базы тёмный вид, поверх файла накладывается `variants.dark`,
   иначе `variants.light`.
3. **Акцент.** `"accent"` перекрашивает тему штатным механизмом Telegram, как выбор акцента в
   настройках: кнопки, ссылки, переключатели, свои пузыри.
4. **`colors`** — понятные имена из таблицы ниже, каждое раскрывается в несколько ключей Telegram.
   Порядок фиксирован (общие имена → частные), поэтому `chatList.title` всегда сильнее, чем `text`.
5. **`native`** — точные ключи Telegram; сильнее всего остального.
6. **Обои** из `"wallpaper"`.
7. Поверх темы ложатся **«Свои цвета»** со страницы «Темы, цвета и бейджи» и стекло AyuGlass.
   Ручные правки пользователя всегда сильнее темы.

Тема применяется сразу, без перезапуска. Если файл перестал читаться, интерфейс остаётся
обычным Telegram. В режиме-приманке (decoy) тема не показывается, как и всё остальное
оформление VoidGram.

## Формат

```json
{
  "vgtheme": 1,
  "id": "nord",
  "name": { "en": "Nord", "ru": "Норд" },
  "author": "you",
  "description": "Короткое описание",
  "base": "night",
  "accent": "$frost",
  "vars": { "bg": "#2E3440", "frost": "#88C0D0" },
  "colors": { "background": "$bg", "outgoing.bubble": "mix($bg, $frost, 0.4)" },
  "native": { "chat.message.outgoing.bubble.withWp.stroke": "transparent" },
  "wallpaper": { "colors": ["#2E3440", "#3B4252"], "rotation": 45 },
  "variants": {
    "light": { "vars": { "bg": "#ECEFF4" }, "wallpaper": "#E5E9F0" }
  }
}
```

| Поле | Обязательно | Что это |
|---|---|---|
| `vgtheme` | да | версия формата, сейчас `1` |
| `id` | да | 1–64 символа `a-z 0-9 . _ -`; тема с тем же id заменяет установленную, id встроенных тем заняты |
| `name` | да | строка или `{ "en": …, "ru": … }` |
| `author`, `description` | нет | строки, видны при импорте |
| `base` | нет | `inherit` (по умолчанию: текущая тема Telegram), `day`, `classic`, `night`, `tinted` |
| `accent` | нет | цвет-акцент |
| `vars` | нет | до 256 переменных; имя `[A-Za-z_][A-Za-z0-9_-]*` |
| `colors` | нет | понятные имена (таблица ниже) |
| `native` | нет | до 1000 ключей Telegram (`themes/telegram-keys.json`) |
| `wallpaper` | нет | цвет, список из 1–4 цветов (градиент Telegram) или `{ "colors": […], "rotation": 0…359 }` |
| `variants` | нет | `light` и/или `dark`: свои `vars`, `colors`, `native`, `accent`, `wallpaper` |

Внутри варианта `vars`, `colors` и `native` дополняют основной блок по ключам, а `accent` и
`wallpaper` заменяют его. Размер файла — не больше 256 КБ.

## Цвета и выражения

| Запись | Значение |
|---|---|
| `#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA` | как в CSS: альфа **в конце** |
| `transparent` | полностью прозрачный |
| `$name` | переменная; переменные могут ссылаться друг на друга, циклы — ошибка |
| `@chatList.title` | значение ключа в базовой теме (до применения этой темы) |
| `mix(a, b, t)` | смешать: `t = 0` → `a`, `t = 1` → `b` (все каналы, включая альфу) |
| `alpha(a, t)` | тот же цвет с непрозрачностью `t` |
| `lighten(a, t)` / `darken(a, t)` | смешать с белым / чёрным на долю `t`, альфа сохраняется |
| `contrast(a)` | чёрный или белый — что читается на фоне `a` |

Числа записываются как `0.35` или `35%` и должны быть в диапазоне 0…1. Вложенность — до 16
уровней, одно выражение — до 200 символов. Каналы считаются как `floor(x + (y − x)·t + 0.5)`,
поэтому Python-валидатор и приложение дают одинаковые результаты до бита.

У обоев альфа всегда 100%. Если задан `outgoing.bubble` (или `incoming.bubble`), а цвет нажатия
`…bubbleHighlighted` не указан, он считается как `darken(пузырь, 0.08)`. Заливка пузыря из
трёх и более цветов (`bgList`) заменяется одной заливкой, как только тема задаёт `bg`.

## Понятные имена (`colors`)

Применяются в этом порядке:

<!-- aliases:begin -->
| Name | Telegram keys |
|---|---|
| `background` | `list.blocksBg`, `list.modalBlocksBg`, `list.plainBg`, `list.modalPlainBg`, `chatList.bg`, `chatList.itemBg` |
| `surface` | `list.itemBlocksBg`, `list.itemModalBlocksBg`, `actionSheet.opaqueItemBg`, `contextMenu.background` |
| `separator` | `list.blocksSeparator`, `list.plainSeparator`, `chatList.itemSeparator`, `root.navBar.separator`, `root.tabBar.separator`, `chat.inputPanel.panelSeparator`, `actionSheet.opaqueItemSeparator`, `contextMenu.itemSeparator` |
| `text` | `list.primaryText`, `chatList.title`, `root.navBar.primaryText`, `actionSheet.primaryText`, `contextMenu.primary`, `notification.primaryText` |
| `secondaryText` | `list.secondaryText`, `list.sectionHeaderText`, `list.freeText`, `list.disclosureArrow`, `chatList.messageText`, `chatList.dateText`, `root.navBar.secondaryText`, `actionSheet.secondaryText`, `contextMenu.secondary` |
| `destructive` | `list.destructive`, `actionSheet.destructiveActionText`, `contextMenu.destructive`, `chat.inputPanel.panelControlDestructive` |
| `highlight` | `list.itemHighlightedBg`, `chatList.itemHighlightedBg`, `actionSheet.opaqueItemHighlightedBg`, `contextMenu.itemHighlightedBg` |
| `switch.on` | `list.switch.content` |
| `switch.off` | `list.switch.frame` |
| `navBar.background` | `root.navBar.background`, `root.navBar.opaqueBackground` |
| `navBar.text` | `root.navBar.primaryText` |
| `navBar.button` | `root.navBar.button`, `root.navBar.accentText`, `root.navBar.control` |
| `tabBar.background` | `root.tabBar.background` |
| `tabBar.icon` | `root.tabBar.icon`, `root.tabBar.text` |
| `tabBar.selected` | `root.tabBar.selectedIcon`, `root.tabBar.selectedText` |
| `badge.background` | `root.tabBar.badgeBackground`, `root.navBar.badgeFill`, `chatList.unreadBadgeActiveBg`, `chat.historyNav.badgeBg` |
| `badge.text` | `root.tabBar.badgeText`, `root.navBar.badgeText`, `chatList.unreadBadgeActiveText`, `chat.historyNav.badgeText` |
| `search.background` | `root.searchBar.inputFill`, `chatList.regularSearchBar`, `chatList.pinnedSearchBar` |
| `search.text` | `root.searchBar.inputText` |
| `search.placeholder` | `root.searchBar.inputPlaceholderText`, `root.searchBar.inputIcon` |
| `chatList.background` | `chatList.bg`, `chatList.itemBg` |
| `chatList.pinned` | `chatList.pinnedItemBg` |
| `chatList.title` | `chatList.title` |
| `chatList.message` | `chatList.messageText` |
| `chatList.author` | `chatList.authorName` |
| `chatList.date` | `chatList.dateText` |
| `chatList.unread` | `chatList.unreadBadgeActiveBg` |
| `chatList.unreadText` | `chatList.unreadBadgeActiveText` |
| `chatList.muted` | `chatList.unreadBadgeInactiveBg`, `chatList.muteIcon` |
| `chatList.mutedText` | `chatList.unreadBadgeInactiveText` |
| `chatList.checkmark` | `chatList.checkmark` |
| `chatList.online` | `chatList.onlineDot` |
| `outgoing.bubble` | `chat.message.outgoing.bubble.withWp.bg`, `chat.message.outgoing.bubble.withWp.gradientBg`, `chat.message.outgoing.bubble.withoutWp.bg`, `chat.message.outgoing.bubble.withoutWp.gradientBg` |
| `outgoing.bubbleGradient` | `chat.message.outgoing.bubble.withWp.gradientBg`, `chat.message.outgoing.bubble.withoutWp.gradientBg` |
| `outgoing.bubbleHighlighted` | `chat.message.outgoing.bubble.withWp.highlightedBg`, `chat.message.outgoing.bubble.withoutWp.highlightedBg` |
| `outgoing.bubbleStroke` | `chat.message.outgoing.bubble.withWp.stroke`, `chat.message.outgoing.bubble.withoutWp.stroke` |
| `outgoing.text` | `chat.message.outgoing.primaryText`, `chat.message.outgoing.fileTitle` |
| `outgoing.secondaryText` | `chat.message.outgoing.secondaryText`, `chat.message.outgoing.fileDescription`, `chat.message.outgoing.fileDuration` |
| `outgoing.link` | `chat.message.outgoing.linkText` |
| `outgoing.accent` | `chat.message.outgoing.accentText`, `chat.message.outgoing.accentControl`, `chat.message.outgoing.mediaActiveControl` |
| `outgoing.check` | `chat.message.outgoingCheck` |
| `incoming.bubble` | `chat.message.incoming.bubble.withWp.bg`, `chat.message.incoming.bubble.withWp.gradientBg`, `chat.message.incoming.bubble.withoutWp.bg`, `chat.message.incoming.bubble.withoutWp.gradientBg` |
| `incoming.bubbleGradient` | `chat.message.incoming.bubble.withWp.gradientBg`, `chat.message.incoming.bubble.withoutWp.gradientBg` |
| `incoming.bubbleHighlighted` | `chat.message.incoming.bubble.withWp.highlightedBg`, `chat.message.incoming.bubble.withoutWp.highlightedBg` |
| `incoming.bubbleStroke` | `chat.message.incoming.bubble.withWp.stroke`, `chat.message.incoming.bubble.withoutWp.stroke` |
| `incoming.text` | `chat.message.incoming.primaryText`, `chat.message.incoming.fileTitle` |
| `incoming.secondaryText` | `chat.message.incoming.secondaryText`, `chat.message.incoming.fileDescription`, `chat.message.incoming.fileDuration` |
| `incoming.link` | `chat.message.incoming.linkText` |
| `incoming.accent` | `chat.message.incoming.accentText`, `chat.message.incoming.accentControl`, `chat.message.incoming.mediaActiveControl` |
| `service.background` | `chat.serviceMessage.components.withDefaultWp.bg`, `chat.serviceMessage.components.withDefaultWp.dateFillStatic`, `chat.serviceMessage.components.withDefaultWp.dateFillFloat`, `chat.serviceMessage.components.withCustomWp.bg`, `chat.serviceMessage.components.withCustomWp.dateFillStatic`, `chat.serviceMessage.components.withCustomWp.dateFillFloat` |
| `service.text` | `chat.serviceMessage.components.withDefaultWp.primaryText`, `chat.serviceMessage.components.withCustomWp.primaryText`, `chat.serviceMessage.dateText.withWp`, `chat.serviceMessage.dateText.withoutWp` |
| `input.background` | `chat.inputPanel.panelBg`, `chat.inputButtonPanel.panelBg`, `chat.inputMediaPanel.stickersBg` |
| `input.field` | `chat.inputPanel.inputBg` |
| `input.fieldStroke` | `chat.inputPanel.inputStroke` |
| `input.text` | `chat.inputPanel.inputText_v2`, `chat.inputPanel.primaryText` |
| `input.placeholder` | `chat.inputPanel.inputPlaceholder_v2`, `chat.inputPanel.secondaryText` |
| `input.icons` | `chat.inputPanel.panelControl_v2`, `chat.inputPanel.inputControl_v2` |
| `input.accent` | `chat.inputPanel.panelControlAccent`, `chat.inputPanel.actionControlBg`, `chat.inputPanel.mediaRecordControl.button` |
| `input.sendIcon` | `chat.inputPanel.actionControlFg`, `chat.inputPanel.mediaRecordControl.activeIcon` |
| `menu.background` | `contextMenu.background`, `actionSheet.opaqueItemBg` |
| `menu.text` | `contextMenu.primary`, `actionSheet.primaryText` |
<!-- aliases:end -->

Всё остальное (опросы, кнопки клавиатуры, графики, стикер-панель и т. д.) задаётся через `native`.

## Ключи Telegram (`native`)

Полный список с типами — `themes/telegram-keys.json`. Его генерирует `tools/vgtheme_keys.py`
из исходников Telegram-iOS закреплённой версии. Ключи в стиле `.tgios-theme`:
`root.tabBar.selectedIcon`, `list.itemBlocksBg`, `chat.message.outgoing.bubble.withWp.bg`
(`withWp` — поверх обоев, `withoutWp` — без них).

Чтобы начать с полной копии текущей темы, нажмите **«Ключи текущей темы»**: получится файл, где
в `native` выписаны все цвета. Удалите лишнее и поменяйте нужное.

## Где взять и как поставить

- **Встроенные:** Void Графит (светлый и тёмный варианты), Nord, Dracula, OLED фиолетовая, Сакура.
- **Файл в чате.** Нажмите на `.vgtheme`, проверьте автора и предупреждения, затем выберите
  «Установить и применить». В секретных чатах и сообщениях с запретом копирования файл
  открывается как обычный документ.
- **Импорт из Файлов** или **вставка JSON из буфера обмена** на странице тем.
- **Тема из своих цветов** превращает «Свои цвета» в файл, которым можно поделиться.
- **Плагины:** `ayu.ui.theme.list/active/apply/reset/install`, разрешение `themes`
  (см. [CODE_PLUGINS.md](CODE_PLUGINS.md)).

На странице тем нажатие на тему применяет её. Повторное нажатие на включённую открывает меню:
«Поделиться файлом», «Скопировать JSON», «Удалить» (у встроенных тем удаления нет). Файлы лежат
в `Application Support/VoidGram/Themes/<id>.vgtheme`.

## Проверка без телефона

```bash
python tools/vgtheme.py validate themes/*.vgtheme
python tools/vgtheme.py resolve themes/nord.vgtheme --dark
python -m unittest ci.tests.test_vgtheme
```

`validate` проверяет обе версии темы (светлую и тёмную) и предупреждает о неизвестных ключах.
`ci/tests/test_vgtheme.py` проверяет, что таблица имён, лимиты, шаблоны и встроенные темы в
Swift-патче совпадают с `tools/vgtheme.py`. Встроенные темы — это файлы из `themes/`: после их
правки перегенерируйте `AyuThemeEngineBuiltins.swift` командой `python tools/vgtheme.py builtins`.

## Что проверить на устройстве

- Переключение тем и возврат к Telegram без перезапуска; авто-ночь переключает `variants`.
- Пузыри с обоями и без, градиенты пузырей, обои 2–4 цвета с поворотом.
- «Свои цвета» поверх темы, OLED-режим WhiteGram, стекло AyuGlass.
- Импорт из чата, Файлов и буфера; файл с ошибкой показывает понятный текст и ничего не ломает.
- Поделиться на iPad (поповер), большие шрифты, VoiceOver на странице тем.
