// Tests for the chat-streak plugin on the real AyuGram prelude, via the SDK's mock-runner.
//   AYU_SDK=/path/to/AyuGramm-Plugin-SDK node --test ayu-plugins/chat-streak/chat-streak.test.ts
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { afterEach, test } from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const sdk = process.env.AYU_SDK;
if (!sdk) throw new Error("Set AYU_SDK to a checkout of https://github.com/murk-sus/AyuGramm-Plugin-SDK");
const { loadPrelude, Sandbox } = await import(path.join(path.resolve(sdk), "tools/mock-runner/mock.ts"));

// The mock host has no plugin settings; let tests set them through globalThis.__settings.
const prelude = loadPrelude(path.join(path.resolve(sdk), "prelude/prelude.swift")).replace(
  "const host = root.__ayuHost;",
  "const host = root.__ayuHost; host.settingGet = (key) => (root.__settings || {})[key];",
);
const plugin = fs.readFileSync(path.join(here, "chat-streak.ayu.js"), "utf8");

type Msg = { id: string; peerId: string; text: string; outgoing: boolean; date: number; authorId?: string };

/** Local noon `ago` days back, in seconds (the app's message date). */
function at(ago: number, hour = 12): number {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  d.setDate(d.getDate() - ago);
  return Math.floor(d.getTime() / 1000);
}

/** History where `days` lists [daysAgo, outgoing?, incoming?]; newest first like a chat. */
function history(peerId: string, days: [number, boolean, boolean][], author = peerId): Msg[] {
  const out: Msg[] = [];
  let id = 1;
  for (const [ago, me, them] of days) {
    if (me) out.push({ id: String(id++), peerId, text: "hi", outgoing: true, date: at(ago) });
    if (them) out.push({ id: String(id++), peerId, text: "hey", outgoing: false, date: at(ago, 13), authorId: author });
  }
  return out.sort((a, b) => b.date - a.date);
}

const mutual = (from: number, to: number): [number, boolean, boolean][] =>
  Array.from({ length: to - from + 1 }, (_, i) => [from + i, true, true] as [number, boolean, boolean]);

// Every sandbox is disposed after its test, even a failing one, so pending timers don't keep Node alive.
const live: any[] = [];
afterEach(() => { for (const s of live.splice(0)) s.dispose(); });

function start(chats: Record<string, Msg[]>, settings: Record<string, string> = {}, storage?: object) {
  const sandbox = new Sandbox({
    prelude,
    pluginId: "chat-streak",
    responders: {
      "messages.get": (args: { peerId: string; limit: number }) => {
        return (chats[args.peerId] ?? []).slice(0, args.limit);
      },
      "ui.alert": () => "ok",
    },
  });
  live.push(sandbox);
  if (storage) sandbox.storage.set("state", JSON.stringify(storage));
  sandbox.load(`globalThis.__settings = ${JSON.stringify(settings)};`, "settings.js");
  sandbox.load(plugin, "chat-streak.ayu.js");
  return sandbox;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 30));
const calls = (s: any, op: string) => s.calls.filter((c: any) => c.op === op).map((c: any) => c.args);
const lastBadge = (s: any, peerId: string) => calls(s, "ui.badge.add").filter((a: any) => a.peerId === peerId).pop()?.badge?.text;
const stored = (s: any) => JSON.parse(s.storage.get("state"));

test("a mutual streak that includes today shows 🔥 N in the chat list and the profile", async () => {
  const s = start({ "100": history("100", mutual(0, 4)) });
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), "🔥 5");
  const block = calls(s, "ui.profile.addBlock").pop();
  assert.equal(block.peerId, "100");
  assert.match(block.text, /5 дней подряд, сегодня уже засчитан/);
  assert.deepEqual(stored(s).peers["100"].n, 5);
  s.dispose();
});

test("if today is not done yet the streak is still alive and marked ⏳", async () => {
  const s = start({ "100": history("100", [[0, true, false], ...mutual(1, 4)]) });
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), "⏳ 4");
  assert.match(calls(s, "ui.profile.addBlock").pop().text, /погаснет в полночь/);
  s.dispose();
});

test("a missed day breaks the streak, and one-sided days never count", async () => {
  const s = start({
    "100": history("100", [...mutual(0, 1), ...mutual(3, 9)]),     // gap two days ago
    "200": history("200", [0, 1, 2, 3].map((d) => [d, true, false] as [number, boolean, boolean])),
  });
  s.emit("chatOpen", { peerId: "100" });
  s.emit("chatOpen", { peerId: "200" });
  await settle();
  assert.equal(lastBadge(s, "100"), "🔥 2");
  assert.equal(lastBadge(s, "200"), undefined);
  assert.equal(stored(s).peers["200"].n, 0);
  s.dispose();
});

test("a streak below minDays is counted but not shown", async () => {
  const s = start({ "100": history("100", mutual(0, 2)) }, { minDays: "4" });
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), undefined);
  assert.equal(stored(s).peers["100"].n, 3);
  s.dispose();
});

test("avatar display decorates the avatar instead of adding a badge", async () => {
  const s = start({ "100": history("100", mutual(0, 2)) }, { display: "avatar" });
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), undefined);
  assert.deepEqual(calls(s, "ui.avatar.decorate").pop(), { peerId: "100", emoji: "🔥" });
  s.dispose();
});

test("group chats (several incoming authors) are skipped unless enabled", async () => {
  const group = [...history("-5", mutual(0, 3), "1"), ...history("-5", mutual(0, 3), "2").map((m) => ({ ...m, id: "g" + m.id }))];
  const s = start({ "-5": group });
  s.emit("chatOpen", { peerId: "-5" });
  await settle();
  assert.equal(lastBadge(s, "-5"), undefined);
  assert.equal(stored(s).peers["-5"], undefined);
  s.dispose();

  const on = start({ "-5": group }, { groups: "1" });
  on.emit("chatOpen", { peerId: "-5" });
  await settle();
  assert.equal(lastBadge(on, "-5"), "🔥 4");
  on.dispose();
});

test("when history hits the read limit the stored streak is continued", async () => {
  // A busy chat: the 500 newest messages only cover the last three days.
  const busy: Msg[] = [];
  for (let i = 0; i < 500; i++) {
    const ago = Math.floor(i / 167);
    busy.push({ id: String(i), peerId: "100", text: "msg", outgoing: i % 2 === 0, date: at(ago, 20) - (i % 167) * 60, authorId: i % 2 ? "100" : undefined });
  }
  // The stored record already knew about 40 days ending yesterday.
  const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() - 1);
  const yesterday = Math.floor((d.getTime() - d.getTimezoneOffset() * 60000) / 86400000);
  const storage = { peers: { "100": { n: 40, last: yesterday, best: 40, active: yesterday, checked: 0, celebrated: 40 } }, muted: {}, warned: 0 };
  const s = start({ "100": busy }, {}, storage);
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), "🔥 41");                 // 40 days up to yesterday + today
  assert.equal(calls(s, "ui.animation.play").length, 0);       // no milestone between 40 and 41
  s.dispose();

  // Without the stored record the same window only proves three days.
  const fresh = start({ "100": busy });
  fresh.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(fresh, "100"), "🔥 3");
  fresh.dispose();
});

test("reaching a milestone plays confetti once; the first count after install does not", async () => {
  const chats = { "100": history("100", mutual(0, 9)) };
  const fresh = start(chats);
  fresh.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(calls(fresh, "ui.animation.play").length, 0);
  fresh.dispose();

  const yesterday9 = { peers: { "100": { n: 9, last: 0, best: 9, active: 0, checked: 0, celebrated: 9 } }, muted: {}, warned: 0 };
  const s = start(chats, {}, yesterday9);
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.deepEqual(calls(s, "ui.animation.play"), [{ name: "confetti", seconds: 3 }]);
  assert.ok(s.toasts.some((x: string) => x.includes("10 дней подряд")));
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(calls(s, "ui.animation.play").length, 1);
  s.dispose();
});

test("after the warning hour a pending streak raises one toast per day", async () => {
  const chats = { "100": history("100", [[0, true, false], ...mutual(1, 5)]) };
  const s = start(chats, { warnHour: "0" });
  await settle();                      // load → refreshAll has nothing tracked yet
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  s.emit("appForeground", {});
  await settle();
  s.emit("appForeground", {});
  await settle();
  const warnings = s.toasts.filter((x: string) => x.startsWith("⏳"));
  assert.equal(warnings.length, 1);
  assert.match(warnings[0], /в 1 чате \(самый длинный — 5 дней\)/);
  s.dispose();
});

test("the profile button stops and resumes counting for a chat", async () => {
  const s = start({ "100": history("100", mutual(0, 2)) });
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), "🔥 3");

  s.emit("profileOpen", { peerId: "100" });
  const button = calls(s, "ui.profile.addButton").pop();
  assert.equal(button.title, "Не считать огонёк");
  s.emit("profileButton", { buttonId: button.id, peerId: "100" });
  await settle();
  assert.deepEqual(calls(s, "ui.badge.remove").pop(), { peerId: "100" });
  assert.equal(stored(s).muted["100"], true);
  assert.equal(calls(s, "ui.profile.addButton").pop().title, "Снова считать огонёк");

  s.emit("profileButton", { buttonId: button.id, peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), "🔥 3");
});

test("the plugin registers no dot commands", () => {
  const s = start({});
  assert.equal(calls(s, "commands.register").length, 0);
  assert.equal(s.send(".streak", { peerId: "100" }), ".streak");
});

test("sending a message re-counts the chat shortly after", async () => {
  const chats: Record<string, Msg[]> = { "100": history("100", mutual(1, 3)) };
  const s = start(chats);
  s.emit("chatOpen", { peerId: "100" });
  await settle();
  assert.equal(lastBadge(s, "100"), "⏳ 3");
  chats["100"] = history("100", mutual(0, 3));
  assert.equal(s.send("привет", { peerId: "100" }), "привет");
  await new Promise((resolve) => setTimeout(resolve, 1600));
  assert.equal(lastBadge(s, "100"), "🔥 4");
  s.dispose();
});
