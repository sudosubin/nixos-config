// System-wide text replacement (e.g. `->` to `→`) with Backspace to undo.

const eventtap = hs.eventtap;
const types = eventtap.eventTypes;
const keys = hs.keycodes.map;

// Tracks our own events so the tap skips them (no eventSourceUserData in Hammerspoon 2 yet)
const OWN_EVENT_TIMEOUT_MS = 500;
let ownEvents = [];

const expectOwn = (keyCode, characters) => {
  ownEvents.push({ keyCode, characters, expires: Date.now() + OWN_EVENT_TIMEOUT_MS });
};

const isOwn = (event) => {
  const now = Date.now();
  ownEvents = ownEvents.filter((own) => own.expires > now);

  const own = ownEvents[0];
  if (own && own.keyCode === event.keyCode && (own.characters === null || own.characters === event.characters)) {
    ownEvents.shift();
    return true;
  }
  return false;
};

const resetKeys = new Set(
  [
    "return",
    "padenter",
    "tab",
    "escape",
    "left",
    "right",
    "up",
    "down",
    "home",
    "end",
    "pageup",
    "pagedown",
    "forwarddelete",
  ].map((name) => keys[name]),
);

const backspaces = (count) => {
  for (let i = 0; i < count; i++) {
    expectOwn(keys["delete"], null);
    for (const isDown of [true, false]) {
      const event = eventtap.makeKeyEventWithCode(keys["delete"], isDown);
      event.rawFlags = 0;
      event.post();
    }
  }
};

const type = (text) => {
  // keyStrokes() posts BMP characters only, as keyCode 0
  for (const char of text) {
    if (char.codePointAt(0) <= 0xffff) expectOwn(0, char);
  }
  eventtap.keyStrokes(text);
};

let tap = null;

const obj = {
  // Table of `trigger = replacement`.
  rules: {},

  // List of bundle identifiers where nothing is replaced.
  excludedApps: [],

  start: () => {
    obj.stop();

    // Longest first, so the longest suffix wins
    const triggers = Object.keys(obj.rules).sort((a, b) => b.length - a.length);
    // At least 1, as slice(-0) keeps everything
    const maxLength = Math.max(1, ...triggers.map((trigger) => [...trigger].length));
    const excluded = new Set(obj.excludedApps);

    let buffer = "";
    let last = null;

    const reset = () => {
      buffer = "";
      last = null;
      return eventtap.emit;
    };

    const handleKey = (event) => {
      // No keyboardEventAutorepeat in Hammerspoon 2 yet
      if (["cmd", "ctrl", "alt"].some((mod) => event.flags.includes(mod)) || resetKeys.has(event.keyCode)) {
        return reset();
      }

      const app = hs.application.frontmost();
      if (app && excluded.has(app.bundleID)) return reset();

      if (event.keyCode === keys["delete"]) {
        const undo = last;
        reset();
        if (undo) {
          backspaces([...undo.replacement].length);
          type(undo.trigger);
          return eventtap.consume;
        }
        return eventtap.emit;
      }

      const characters = event.characters;
      if (!characters) return reset();

      last = null;
      buffer = [...(buffer + characters)].slice(-maxLength).join("");

      const trigger = triggers.find((t) => buffer.endsWith(t));
      if (!trigger) return eventtap.emit;

      const replacement = obj.rules[trigger];
      // The last key is swallowed, so one character less is on screen
      backspaces([...trigger].length - 1);
      type(replacement);
      buffer = "";
      last = { trigger, replacement };
      return eventtap.consume;
    };

    tap = eventtap.addWatcher(
      [types.keyDown, types.leftMouseDown, types.rightMouseDown, types.otherMouseDown],
      (event) => {
        if (event.type !== types.keyDown) return reset();
        if (isOwn(event)) return eventtap.emit;
        return handleKey(event);
      },
      false,
    );
    tap.start();

    return obj;
  },

  stop: () => {
    // Event taps are not garbage collected
    if (tap) eventtap.removeWatcher(tap);
    tap = null;
    ownEvents = [];
    return obj;
  },
};

module.exports = obj;
