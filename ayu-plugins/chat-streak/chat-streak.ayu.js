// ==AyuPlugin==
// @id chat-streak
// @name Chat Streak
// @name:ru Огонёк
// @author @your_telegram
// @version 1.0
// @description TikTok-style chat streaks: 🔥 N means you and your contact have both written to each other N days in a row.
// @description:ru Огонёк как в TikTok: 🔥 N — сколько дней подряд вы с собеседником оба писали друг другу.
// @permissions messages.read, badges, profile, ui, commands, overlay
// @tags chats, fun
// ==/AyuPlugin==
'use strict';

// Огонёк считается только на этом устройстве: у Telegram нет серверных серий, а плагину не приходят
// входящие сообщения и список чатов. Поэтому чат попадает в учёт, когда вы его открываете или пишете в
// него, а входящие проверяются через ayu.messages.get при открытии чата, приложения и раз в 15 минут.

const DAY_MS = 24 * 60 * 60 * 1000;
const HISTORY_LIMIT = 500;               // сколько последних сообщений чата читать за раз
const RECHECK_MS = 10 * 60 * 1000;       // фоновое обновление одного чата — не чаще раза в 10 минут
const POLL_MS = 15 * 60 * 1000;          // как часто проверять чаты, где сегодня ещё не переписывались
const STALE_DAYS = 7;                    // чаты без огонька и без переписки дольше — забываем
const STORAGE_BUDGET = 60000;            // хранилище плагина — 64 КБ
const MILESTONES = [10, 30, 50, 100, 200, 365, 500, 1000];

// ---------- Язык ----------

const ru = () => ayu.i18n.language === 'ru';
const t = (ruText, enText) => (ru() ? ruText : enText);

function plural(n, one, few, many) {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
}
const daysWord = (n) => (ru() ? plural(n, 'день', 'дня', 'дней') : (n === 1 ? 'day' : 'days'));
const chatsWord = (n) => (ru() ? plural(n, 'чате', 'чатах', 'чатах') : (n === 1 ? 'chat' : 'chats'));

// ---------- Настройки ----------

ayu.settings.declare([
    {
        key: 'display', type: 'select', default: 'badge',
        title: t('Где показывать огонёк', 'Where to show the streak'),
        options: [
            { value: 'badge', title: t('Бейдж «🔥 N» у имени чата', '“🔥 N” badge next to the chat name') },
            { value: 'avatar', title: t('🔥 на аватарке', '🔥 on the avatar') },
            { value: 'both', title: t('И там, и там', 'Both') }
        ]
    },
    {
        key: 'minDays', type: 'slider', min: 1, max: 7, step: 1, default: 2,
        title: t('Показывать с … дней подряд', 'Show from … days in a row')
    },
    {
        key: 'profileBlock', type: 'toggle', default: true,
        title: t('Блок в профиле собеседника', 'Block in the contact’s profile'),
        subtitle: t('Длина серии, рекорд и статус за сегодня', 'Streak length, record and today’s status')
    },
    {
        key: 'warn', type: 'toggle', default: true,
        title: t('Предупреждать, что огонёк гаснет', 'Warn when a streak is about to end'),
        subtitle: t('Когда приложение открыто после указанного часа', 'When the app is open after the hour below')
    },
    {
        key: 'warnHour', type: 'slider', min: 12, max: 23, step: 1, default: 21,
        title: t('Час предупреждения', 'Warning hour')
    },
    {
        key: 'celebrate', type: 'toggle', default: true,
        title: t('Конфетти на 10, 30, 100… днях', 'Confetti at 10, 30, 100… days')
    },
    {
        key: 'groups', type: 'toggle', default: false,
        title: t('Считать огонёк в группах', 'Count streaks in groups'),
        subtitle: t('В группе день засчитывается, если писали вы и кто-то ещё', 'In a group a day counts if you and anyone else wrote')
    },
    {
        key: 'about', type: 'preview',
        title: t('Как это работает', 'How it works'),
        subtitle: t(
            'День засчитывается, если в этот день писали и вы, и собеседник. ⏳ — сегодня ещё не переписывались, огонёк погаснет в полночь. Огонёк считается только на этом устройстве, собеседник его не видит. Команда .streak в чате показывает подробности.',
            'A day counts when both you and the contact wrote that day. ⏳ means you haven’t talked today yet and the streak ends at midnight. Streaks are counted on this device only; the contact doesn’t see them. Type .streak in a chat for details.'
        )
    }
]);

function setting(key, fallback) {
    const value = ayu.settings.get(key);
    return value === null || value === undefined || value === '' ? fallback : value;
}
const flag = (key, fallback) => {
    const value = setting(key, fallback);
    return value === true || value === 1 || value === '1' || value === 'true';
};
const num = (key, fallback) => {
    const value = Number(setting(key, fallback));
    return Number.isFinite(value) ? value : fallback;
};
const minDays = () => Math.max(1, Math.round(num('minDays', 2)));

// ---------- Дни ----------

/** Дата сообщения в мс: приложение может отдавать секунды. */
const toMs = (date) => { const n = Number(date); return n < 1e12 ? n * 1000 : n; };
/** Номер дня по местному времени. */
const dayKey = (ms) => Math.floor((ms - new Date(ms).getTimezoneOffset() * 60000) / DAY_MS);
const today = () => dayKey(Date.now());

// ---------- Состояние ----------
// peers[peerId] = { n, last, best, active, checked, celebrated }
//   n — длина серии, last — номер последнего засчитанного дня, best — рекорд,
//   active — последний день с любой перепиской, checked — когда читали историю (мс),
//   celebrated — длина серии, для которой уже показали конфетти.

let state = { peers: {}, muted: {}, warned: 0 };
try {
    const saved = JSON.parse(ayu.storage.get('state') || 'null');
    if (saved && typeof saved === 'object') {
        state = { peers: saved.peers || {}, muted: saved.muted || {}, warned: saved.warned || 0 };
    }
} catch (e) {
    ayu.warn('streak: stored state is broken, starting over');
}

function save() {
    let json = JSON.stringify(state);
    if (json.length > STORAGE_BUDGET) {
        // Сначала выбрасываем самые давние чаты без огонька.
        const victims = Object.keys(state.peers)
            .filter((p) => current(state.peers[p]) === 0)
            .sort((a, b) => (state.peers[a].active || 0) - (state.peers[b].active || 0));
        while (json.length > STORAGE_BUDGET && victims.length) {
            delete state.peers[victims.shift()];
            json = JSON.stringify(state);
        }
    }
    ayu.storage.set('state', json);
}

/** Серия, которая жива сейчас: засчитан сегодняшний или вчерашний день. */
function current(rec) {
    return rec && rec.n > 0 && rec.last >= today() - 1 ? rec.n : 0;
}

// ---------- Отображение ----------

const shown = {}; // что уже нарисовано для чата, чтобы не дёргать приложение зря

function describe(peerId) {
    const rec = state.peers[peerId];
    if (state.muted[peerId]) return t('Огонёк в этом чате не считается.', 'Streaks are off for this chat.');
    const n = current(rec);
    const best = rec ? Math.max(rec.best || 0, n) : 0;
    const record = best > n ? t(`\nРекорд: ${best} ${daysWord(best)}.`, `\nRecord: ${best} ${daysWord(best)}.`) : '';
    if (n === 0) {
        return t('Огонька пока нет. Пишите друг другу каждый день, и он появится.', 'No streak yet. Write to each other every day to start one.') + record;
    }
    const status = rec.last === today()
        ? t('сегодня уже засчитан ✅', 'today already counts ✅')
        : t('сегодня ещё не переписывались — огонёк погаснет в полночь ⏳', 'you haven’t talked today yet — the streak ends at midnight ⏳');
    return t(`🔥 ${n} ${daysWord(n)} подряд, ${status}.`, `🔥 ${n} ${daysWord(n)} in a row, ${status}.`) + record;
}

function render(peerId) {
    const rec = state.peers[peerId];
    const n = state.muted[peerId] ? 0 : current(rec);
    const visible = n >= minDays();
    const display = setting('display', 'badge');
    const emoji = visible && rec.last !== today() ? '⏳' : '🔥';
    const next = {
        badge: visible && display !== 'avatar' ? `${emoji} ${n}` : null,
        avatar: visible && display !== 'badge' ? emoji : null,
        block: visible && flag('profileBlock', true) ? describe(peerId) : null
    };
    const prev = shown[peerId] || { badge: null, avatar: null, block: null };
    if (next.badge !== prev.badge) {
        if (next.badge) ayu.ui.badge.add({ peerId, badge: { text: next.badge } });
        else ayu.ui.badge.remove({ peerId });
    }
    if (next.avatar !== prev.avatar) {
        if (next.avatar) ayu.ui.avatar.decorate(peerId, next.avatar);
        else ayu.ui.avatar.clear(peerId);
    }
    if (next.block !== prev.block) {
        if (next.block) ayu.ui.profile.addBlock({ id: 'streak-' + peerId, peerId, title: t('Огонёк', 'Streak'), text: next.block });
        else ayu.ui.profile.removeBlock('streak-' + peerId);
    }
    if (next.badge || next.avatar || next.block) shown[peerId] = next;
    else delete shown[peerId];
}

function renderAll() {
    const peers = new Set([...Object.keys(state.peers), ...Object.keys(shown)]);
    peers.forEach(render);
}

// ---------- Подсчёт ----------

function analyze(messages) {
    const out = new Set(), inc = new Set(), authors = new Set();
    let oldest = Infinity, newest = -Infinity;
    for (const m of messages) {
        if (!m || m.date === undefined || m.date === null) continue;
        const day = dayKey(toMs(m.date));
        if (day < oldest) oldest = day;
        if (day > newest) newest = day;
        if (m.outgoing) out.add(day);
        else {
            inc.add(day);
            if (m.authorId !== undefined && m.authorId !== null) authors.add(String(m.authorId));
        }
    }
    return { out, inc, authors, oldest, newest };
}

function celebrate(previous, n) {
    if (!flag('celebrate', true)) return;
    const hit = MILESTONES.filter((m) => m > previous && m <= n).pop();
    if (!hit) return;
    ayu.ui.animation.play('confetti', 3);
    ayu.toast(t(`🔥 ${hit} ${daysWord(hit)} подряд!`, `🔥 ${hit} ${daysWord(hit)} in a row!`));
}

async function refresh(peerId, force) {
    if (state.muted[peerId]) { render(peerId); return; }
    const old = state.peers[peerId];
    if (!force && old && Date.now() - (old.checked || 0) < RECHECK_MS) return;

    let messages;
    try {
        messages = await ayu.messages.get({ peerId, limit: HISTORY_LIMIT });
    } catch (e) {
        ayu.warn('streak: cannot read chat', peerId, e && e.message);
        return;
    }
    if (!Array.isArray(messages)) return;

    const a = analyze(messages);
    if (!flag('groups', false) && a.authors.size > 1) {
        // Несколько авторов входящих — это группа.
        delete state.peers[peerId];
        save();
        render(peerId);
        return;
    }

    const day = today();
    const both = (d) => a.out.has(d) && a.inc.has(d);
    const end = both(day) ? day : day - 1;       // за сегодня серия ещё не сгорела
    let start = end + 1;
    while (both(start - 1)) start--;
    let n = end - start + 1;

    // История могла упереться в лимит: самый старый день в окне неполный, а серия может быть длиннее.
    // Тогда продолжаем её по сохранённому счётчику, если он стыкуется с найденным отрезком.
    const truncated = messages.length >= HISTORY_LIMIT;
    if (n > 0 && truncated && start <= a.oldest + 1 && old && old.n > 0 && old.last >= start - 1 && old.last <= end) {
        const storedStart = old.last - old.n + 1;
        if (storedStart < start) n = end - storedStart + 1;
    }

    const rec = {
        n,
        last: n > 0 ? end : 0,
        best: Math.max(old ? old.best || 0 : 0, n),
        active: Number.isFinite(a.newest) ? a.newest : (old ? old.active || 0 : 0),
        checked: Date.now(),
        celebrated: n
    };
    // Первый подсчёт (например, сразу после установки) не празднуем.
    if (old) celebrate(old.celebrated || 0, n);

    if (n === 0 && rec.active < day - STALE_DAYS) delete state.peers[peerId];
    else state.peers[peerId] = rec;
    save();
    render(peerId);
}

// Чаты обновляются по одному, чтобы не заваливать приложение запросами.
let chain = Promise.resolve();
const queued = new Map();
function schedule(peerId, force) {
    if (peerId === undefined || peerId === null || peerId === '') return chain;
    peerId = String(peerId);
    if (queued.has(peerId)) {
        if (force) queued.set(peerId, true);
        return chain;
    }
    queued.set(peerId, !!force);
    chain = chain
        .then(() => {
            const f = queued.get(peerId);
            queued.delete(peerId);
            return refresh(peerId, f);
        })
        .catch((e) => ayu.warn('streak: refresh failed', peerId, e && e.message));
    return chain;
}

/** Чаты, которые есть смысл перепроверять: с живым огоньком или с недавней перепиской. */
function trackedPeers() {
    const day = today();
    return Object.keys(state.peers).filter((p) => !state.muted[p] && (current(state.peers[p]) > 0 || (state.peers[p].active || 0) >= day - 1));
}

function refreshAll(force) {
    let done = chain;
    for (const peerId of trackedPeers()) done = schedule(peerId, force);
    return done;
}

// ---------- Предупреждение ----------

function warnIfNeeded() {
    if (!flag('warn', true)) return;
    const day = today();
    if (state.warned === day || new Date().getHours() < num('warnHour', 21)) return;
    const pending = Object.keys(state.peers).filter((p) => {
        const rec = state.peers[p];
        return !state.muted[p] && current(rec) >= minDays() && rec.last !== day;
    });
    if (!pending.length) return;
    state.warned = day;
    save();
    const longest = Math.max(...pending.map((p) => state.peers[p].n));
    ayu.toast(t(
        `⏳ Огонёк погаснет в полночь в ${pending.length} ${chatsWord(pending.length)} (самый длинный — ${longest} ${daysWord(longest)}). Такие чаты отмечены ⏳.`,
        `⏳ Streaks end at midnight in ${pending.length} ${chatsWord(pending.length)} (longest: ${longest} ${daysWord(longest)}). They are marked ⏳.`
    ));
}

let warnSchedule = null;
function armWarning() {
    if (warnSchedule !== null) ayu.scheduler.cancel(warnSchedule);
    const hour = String(Math.min(23, Math.max(0, Math.round(num('warnHour', 21))))).padStart(2, '0');
    warnSchedule = ayu.scheduler.daily(`${hour}:00`, () => refreshAll(true).then(warnIfNeeded));
}

// ---------- Отключение для чата ----------

function profileButton(peerId) {
    if (!state.peers[peerId] && !state.muted[peerId]) return;
    ayu.ui.profile.addButton({
        id: 'streak-mute-' + peerId,
        peerId,
        title: state.muted[peerId] ? t('Снова считать огонёк', 'Count the streak again') : t('Не считать огонёк', 'Stop counting the streak')
    });
}

function toggleMute(peerId) {
    if (state.muted[peerId]) delete state.muted[peerId];
    else state.muted[peerId] = true;
    save();
    render(peerId);
    profileButton(peerId);
    if (!state.muted[peerId]) schedule(peerId, true);
}

function showInfo(peerId) {
    ayu.ui.alert({
        title: t('🔥 Огонёк', '🔥 Streak'),
        message: describe(peerId),
        buttons: [
            { id: 'ok', title: 'OK', style: 'default' },
            {
                id: 'mute',
                title: state.muted[peerId] ? t('Снова считать в этом чате', 'Count in this chat again') : t('Не считать в этом чате', 'Stop counting in this chat'),
                style: state.muted[peerId] ? 'default' : 'destructive'
            }
        ]
    }, (choice) => { if (choice === 'mute') toggleMute(peerId); });
}

// ---------- События ----------

ayu.commands.register('streak', t('Огонёк этого чата', 'Streak in this chat'), (args, ctx) => {
    const peerId = ctx && ctx.peerId;
    if (peerId !== undefined && peerId !== null) schedule(peerId, true).then(() => showInfo(String(peerId)));
    return null; // сама команда не отправляется
});

ayu.hooks.after(ayu.hooks.points.outgoingText, (value, ctx) => {
    // Хук должен ответить быстро: только откладываем пересчёт, пока сообщение уйдёт.
    if (value !== '\u0000' && ctx && ctx.peerId !== undefined && !ctx.isSecret) {
        const peerId = ctx.peerId;
        setTimeout(() => schedule(peerId, true), 1500);
    }
});

ayu.on('chatOpen', (payload) => { if (payload) schedule(payload.peerId, true); });
ayu.on('chatClose', (payload) => { if (payload) schedule(payload.peerId, true); });
ayu.on('profileOpen', (payload) => { if (payload && payload.peerId !== undefined) profileButton(String(payload.peerId)); });
ayu.on('profileButton', (payload) => {
    if (payload && typeof payload.buttonId === 'string' && payload.buttonId.indexOf('streak-mute-') === 0) toggleMute(String(payload.peerId));
});
ayu.on('appForeground', () => { renderAll(); refreshAll(false).then(warnIfNeeded); });
ayu.on('settingsChange', () => { renderAll(); armWarning(); });
ayu.on('unload', save);

// После полуночи 🔥 становится ⏳, а несохранённые серии исчезают — перерисовываем без запросов.
ayu.scheduler.daily('00:00:05', () => { renderAll(); save(); });

// Входящие сообщения плагину не приходят, поэтому периодически проверяем чаты, где огонёк ещё не засчитан сегодня.
setInterval(() => {
    const day = today();
    for (const peerId of trackedPeers()) {
        if (state.peers[peerId].last !== day) schedule(peerId, false);
    }
}, POLL_MS);

ayu.on('load', () => {
    renderAll();
    armWarning();
    refreshAll(false).then(warnIfNeeded);
});
