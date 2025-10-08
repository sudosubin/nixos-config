-- Vim bindings
local left = "h";
local down = "j";
local up = "k";
local right = "l";

-- Utils
function merge(a, b)
  local merged = {}
  for _, v in ipairs(a) do
    table.insert(merged, v)
  end
  for _, v in ipairs(b) do
    table.insert(merged, v)
  end
  return merged
end

function strip(string)
  return string:gsub("\n[^\n]*$", "")
end

function stroke(modifiers, character)
  local app = hs.application.frontmostApplication()
  hs.eventtap.event.newKeyEvent(modifiers, character, true):post()
  hs.eventtap.event.newKeyEvent(modifiers, character, false):post()
end

-- Prepare
local lrhk = hs.loadSpoon("LeftRightHotkey"):start()

local bin = {
  yabai = strip(hs.execute("command -v yabai", true)),
}

-- Default
local mods = {
  {},
  {"lAlt"},
  {"lAlt", "lShift"},
  {"lCmd"},
  {"lCtrl"},
  {"lShift"},
}

for _, mod in ipairs(mods) do
  lrhk:bind(merge({"rCmd"}, mod), left, function() stroke(mod, "left") end, nil, function() stroke(mod, "left") end)
  lrhk:bind(merge({"rCmd"}, mod), down, function() stroke(mod, "down") end, nil, function() stroke(mod, "down") end)
  lrhk:bind(merge({"rCmd"}, mod), up, function() stroke(mod, "up") end, nil, function() stroke(mod, "up") end)
  lrhk:bind(merge({"rCmd"}, mod), right, function() stroke(mod, "right") end, nil, function() stroke(mod, "right") end)
end

-- Default (ignore cmd+h)
lrhk:bind({"lCmd"}, "h", function() end, nil, function() end)

-- Hammerspoon
hs.hotkey.bind({"alt", "shift"}, "r", function()
  local home = os.getenv("HOME")
  local plist = home .. "/Library/LaunchAgents/org.nix-community.home.yabai.plist"
  hs.execute("launchctl unload " .. plist)
  hs.execute("launchctl load " .. plist)
  hs.reload()
end)

-- Terminal
hs.hotkey.bind({"alt"}, "Return", function() hs.execute("open -na Alacritty.app") end)

-- Yabai
function yabai(args)
  hs.task.new(
    bin.yabai,
    function(exitCode, stdOut, stdErr)
      if stdErr ~= "" then
        hs.alert.show(strip(stdErr))
      end
    end,
    function(task, stdOut, stdErr)
      if stdErr ~= "" then
        hs.alert.show(strip(stdErr))
      end
    end,
    args
  ):start()
end

-- Yabai (focus window)
hs.hotkey.bind({"alt"}, left, function() yabai({"-m", "window", "--focus", "west"}) end)
hs.hotkey.bind({"alt"}, down, function() yabai({"-m", "window", "--focus", "south"}) end)
hs.hotkey.bind({"alt"}, up, function() yabai({"-m", "window", "--focus", "north"}) end)
hs.hotkey.bind({"alt"}, right, function() yabai({"-m", "window", "--focus", "east"}) end)
hs.hotkey.bind({"alt", "shift"}, "Space", function()
  yabai({"-m", "window", "--toggle", "float"})
  yabai({"-m", "window", "--grid", "4:4:1:1:2:2"})
end)

-- Yabai (move window)
hs.hotkey.bind({"alt", "shift"}, left, function() yabai({"-m", "window", "--swap", "west"}) end)
hs.hotkey.bind({"alt", "shift"}, down, function() yabai({"-m", "window", "--swap", "south"}) end)
hs.hotkey.bind({"alt", "shift"}, up, function() yabai({"-m", "window", "--swap", "north"}) end)
hs.hotkey.bind({"alt", "shift"}, right, function() yabai({"-m", "window", "--swap", "east"}) end)

-- Yabai (switch workspace)
hs.hotkey.bind({"alt"}, "1", function() yabai({"-m", "space", "--focus", "1"}) end)
hs.hotkey.bind({"alt"}, "2", function() yabai({"-m", "space", "--focus", "2"}) end)
hs.hotkey.bind({"alt"}, "3", function() yabai({"-m", "space", "--focus", "3"}) end)
hs.hotkey.bind({"alt"}, "4", function() yabai({"-m", "space", "--focus", "4"}) end)
hs.hotkey.bind({"alt"}, "5", function() yabai({"-m", "space", "--focus", "5"}) end)
hs.hotkey.bind({"alt"}, "6", function() yabai({"-m", "space", "--focus", "6"}) end)
hs.hotkey.bind({"alt"}, "7", function() yabai({"-m", "space", "--focus", "7"}) end)
hs.hotkey.bind({"alt"}, "8", function() yabai({"-m", "space", "--focus", "8"}) end)
hs.hotkey.bind({"alt"}, "9", function() yabai({"-m", "space", "--focus", "9"}) end)
hs.hotkey.bind({"alt"}, "0", function() yabai({"-m", "space", "--focus", "10"}) end)

-- Yabai (move to workspace)
hs.hotkey.bind({"alt", "shift"}, "1", function() yabai({"-m", "window", "--space", "1"}) end)
hs.hotkey.bind({"alt", "shift"}, "2", function() yabai({"-m", "window", "--space", "2"}) end)
hs.hotkey.bind({"alt", "shift"}, "3", function() yabai({"-m", "window", "--space", "3"}) end)
hs.hotkey.bind({"alt", "shift"}, "4", function() yabai({"-m", "window", "--space", "4"}) end)
hs.hotkey.bind({"alt", "shift"}, "5", function() yabai({"-m", "window", "--space", "5"}) end)
hs.hotkey.bind({"alt", "shift"}, "6", function() yabai({"-m", "window", "--space", "6"}) end)
hs.hotkey.bind({"alt", "shift"}, "7", function() yabai({"-m", "window", "--space", "7"}) end)
hs.hotkey.bind({"alt", "shift"}, "8", function() yabai({"-m", "window", "--space", "8"}) end)
hs.hotkey.bind({"alt", "shift"}, "9", function() yabai({"-m", "window", "--space", "9"}) end)
hs.hotkey.bind({"alt", "shift"}, "0", function() yabai({"-m", "window", "--space", "10"}) end)

-- Yabai (split, layout)
hs.hotkey.bind({"alt"}, "b", function() yabai({"-m", "window", "--insert", "south"}) end)
hs.hotkey.bind({"alt"}, "v", function() yabai({"-m", "window", "--insert", "east"}) end)
hs.hotkey.bind({"alt"}, "e", function() yabai({"-m", "window", "--toggle", "split"}) end)

-- Yabai (fullscreen)
hs.hotkey.bind({"alt"}, "f", function() yabai({"-m", "window", "--toggle", "zoom-fullscreen"}) end)

hs.alert.show("Config loaded")
