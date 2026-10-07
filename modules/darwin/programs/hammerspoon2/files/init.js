const eventtap = hs.eventtap;
const types = eventtap.eventTypes;
const keycodes = hs.keycodes.map;

// Hammerspoon 2 only holds hotkeys weakly, so keep them referenced
const keepAlive = [];

// Vim bindings
const left = "h";
const down = "j";
const up = "k";
const right = "l";

// Utils
const strip = (string) => string.replace(/\n[^\n]*$/, "");

const alertStderr = ({ stderr }) => stderr && hs.ui.alert(strip(stderr)).show();

// Default (right cmd + vim keys to arrows, keeping the other left-side modifiers)
const arrows = {
  [keycodes[left]]: "left",
  [keycodes[down]]: "down",
  [keycodes[up]]: "up",
  [keycodes[right]]: "right",
};

const mods = [
  [],
  ["leftAlt"],
  ["leftAlt", "leftShift"],
  ["leftCmd"],
  ["leftCtrl"],
  ["leftShift"],
];

const genericMods = {
  leftAlt: "alt",
  leftCmd: "cmd",
  leftCtrl: "ctrl",
  leftShift: "shift",
};

const sideMods = new Set(Object.keys(eventtap.modifierFlags).filter((name) => /^(left|right)[A-Z]/.test(name)));

const sameMods = (a, b) => a.length === b.length && a.every((mod) => b.includes(mod));

const stroke = (modifiers, key) => {
  const flags = modifiers.reduce(
    (acc, mod) => acc | eventtap.modifierFlags[genericMods[mod]] | eventtap.modifierFlags[mod],
    eventtap.modifierFlags.fn | eventtap.modifierFlags.numpad,
  );

  for (const isDown of [true, false]) {
    const event = eventtap.makeKeyEvent(key, isDown);
    event.rawFlags = flags;
    event.post();
  }
};

// keyCodes whose keyDown was swallowed, so their keyUp is swallowed too
const swallowed = new Set();

// Keep referenced, or its callback is dropped on garbage collection
const vimTap = eventtap
  .addWatcher(
    [types.keyDown, types.keyUp],
    (event) => {
      if (event.type === types.keyUp) {
        return swallowed.delete(event.keyCode) ? eventtap.consume : eventtap.emit;
      }

      const held = event.flags.filter((flag) => sideMods.has(flag));

      // Default (ignore cmd+h)
      if (event.keyCode === keycodes["h"] && sameMods(held, ["leftCmd"])) {
        swallowed.add(event.keyCode);
        return eventtap.consume;
      }

      const arrow = arrows[event.keyCode];
      if (!arrow || !held.includes("rightCmd")) {
        return eventtap.emit;
      }

      const mod = mods.find((m) => sameMods(held, ["rightCmd", ...m]));
      if (!mod) {
        return eventtap.emit;
      }

      // Key repeat arrives as repeated keyDown events, so this also covers holding the key
      stroke(mod, arrow);
      swallowed.add(event.keyCode);
      return eventtap.consume;
    },
    false,
  )
  .start();

const bin = {
  yabai: hs.task.runAsync("/usr/bin/command", ["-v", "yabai"]).then((result) => strip(result.stdout)),
};

// Text replacement
const textReplacement = hs.loadSpoon("TextReplacement");
textReplacement.rules = {
  "->": "→",
  "<-": "←",
};
textReplacement.excludedApps = [];
textReplacement.start();

// Hammerspoon
const bind = (modifiers, key, fn) => keepAlive.push(hs.hotkey.bind(modifiers, key, fn));

bind(["alt", "shift"], "r", () => {
  hs.task
    .shell("launchctl kickstart -k gui/$(id -u)/org.nixos.yabai")
    .catch(alertStderr)
    .finally(() => hs.reload());
});

// Terminal
bind(["alt"], "return", () => {
  hs.task.runAsync("/usr/bin/open", ["-na", "WezTerm.app"]).catch(alertStderr);
});

// Yabai
const yabai = (args) =>
  bin.yabai
    .then((path) => hs.task.runAsync(path, args))
    .catch((result) => result)
    .then(alertStderr);

// Yabai (focus window)
bind(["alt"], left, () => yabai(["-m", "window", "--focus", "west"]));
bind(["alt"], down, () => yabai(["-m", "window", "--focus", "south"]));
bind(["alt"], up, () => yabai(["-m", "window", "--focus", "north"]));
bind(["alt"], right, () => yabai(["-m", "window", "--focus", "east"]));
bind(["alt", "shift"], "space", () => {
  yabai(["-m", "window", "--toggle", "float"]).then(() => yabai(["-m", "window", "--grid", "4:4:1:1:2:2"]));
});

// Yabai (move window)
bind(["alt", "shift"], left, () => yabai(["-m", "window", "--swap", "west"]));
bind(["alt", "shift"], down, () => yabai(["-m", "window", "--swap", "south"]));
bind(["alt", "shift"], up, () => yabai(["-m", "window", "--swap", "north"]));
bind(["alt", "shift"], right, () => yabai(["-m", "window", "--swap", "east"]));

// Yabai (switch workspace, move to workspace)
for (let space = 1; space <= 10; space++) {
  const key = String(space % 10);
  bind(["alt"], key, () => yabai(["-m", "space", "--focus", String(space)]));
  bind(["alt", "shift"], key, () => yabai(["-m", "window", "--space", String(space)]));
}

// Yabai (split, layout)
bind(["alt"], "b", () => yabai(["-m", "window", "--insert", "south"]));
bind(["alt"], "v", () => yabai(["-m", "window", "--insert", "east"]));
bind(["alt"], "e", () => yabai(["-m", "window", "--toggle", "split"]));

// Yabai (fullscreen)
bind(["alt"], "f", () => yabai(["-m", "window", "--toggle", "zoom-fullscreen"]));

hs.ui.alert("Config loaded").show();
