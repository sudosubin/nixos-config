--- === TextReplacement ===
---
--- System-wide text replacement (e.g. `->` to `→`) with Backspace to undo.

local eventtap = require("hs.eventtap")
local event    = eventtap.event
local types    = event.types
local props    = event.properties

local obj = {
  name     = "TextReplacement",
  version  = "0.1",
  author   = "sudosubin",
  homepage = "https://github.com/sudosubin/nixos-config",
  license  = "MIT - https://opensource.org/licenses/MIT",
}
obj.__index = obj

--- Table of `trigger = replacement`.
obj.rules = {}

--- List of bundle identifiers where nothing is replaced.
obj.excludedApps = {}

-- Tags our own events so the tap skips them
local MARKER = 0x7e57

local keys = hs.keycodes.map
local resetKeys = {}
for _, name in ipairs({ "return", "padenter", "tab", "escape", "left", "right", "up", "down", "home", "end", "pageup", "pagedown", "forwarddelete" }) do
  resetKeys[keys[name]] = true
end

local function length(s)
  return utf8.len(s) or #s
end

local function tail(s, count)
  local excess = length(s) - count
  return excess > 0 and s:sub(utf8.offset(s, excess + 1)) or s
end

-- Longest suffix of the buffer that is a trigger
local function findTrigger(rules, buffer)
  for count = length(buffer), 1, -1 do
    local suffix = buffer:sub(utf8.offset(buffer, -count))
    if rules[suffix] then return suffix end
  end
end

local function press(keyCode, text)
  for _, isDown in ipairs({ true, false }) do
    local e = event.newKeyEvent({}, keyCode, isDown)
    if text then e:setUnicodeString(text) end
    e:setProperty(props.eventSourceUserData, MARKER)
    e:post()
  end
end

local function backspaces(count)
  for _ = 1, count do press(keys["delete"]) end
end

function obj:start()
  self:stop()

  local maxLength = 0
  for trigger in pairs(self.rules) do
    maxLength = math.max(maxLength, length(trigger))
  end

  local excluded = {}
  for _, bundleID in ipairs(self.excludedApps) do excluded[bundleID] = true end

  local buffer, last = "", nil

  local function reset()
    buffer, last = "", nil
    return false
  end

  local function handleKey(e)
    local flags, keyCode = e:getFlags(), e:getKeyCode()
    if e:getProperty(props.keyboardEventAutorepeat) ~= 0 or flags.cmd or flags.ctrl or flags.alt or resetKeys[keyCode] then
      return reset()
    end

    local app = hs.application.frontmostApplication()
    if app and excluded[app:bundleID()] then return reset() end

    if keyCode == keys["delete"] then
      local undo = last
      reset()
      if undo then
        backspaces(length(undo.replacement))
        press(0, undo.trigger)
      end
      return undo ~= nil
    end

    local characters = e:getCharacters()
    if not characters or characters == "" then return reset() end

    last = nil
    buffer = tail(buffer .. characters, maxLength)

    local trigger = findTrigger(self.rules, buffer)
    if not trigger then return false end

    local replacement = self.rules[trigger]
    -- The last key is swallowed, so one character less is on screen
    backspaces(length(trigger) - 1)
    press(0, replacement)
    buffer, last = "", { trigger = trigger, replacement = replacement }
    return true
  end

  self._tap = eventtap.new({ types.keyDown, types.leftMouseDown, types.rightMouseDown, types.otherMouseDown }, function(e)
    if e:getProperty(props.eventSourceUserData) == MARKER then return false end
    if e:getType() ~= types.keyDown then return reset() end
    return handleKey(e)
  end):start()

  -- macOS silently disables slow eventtaps
  self._watchdog = hs.timer.doEvery(5, function()
    if not self._tap:isEnabled() then self._tap:start() end
  end)

  return self
end

function obj:stop()
  if self._watchdog then self._watchdog:stop() end
  if self._tap then self._tap:stop() end
  self._watchdog, self._tap = nil, nil
  return self
end

return obj
