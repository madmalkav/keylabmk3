-- Load a KeyLab script the way Logic/GarageBand or MainStage would, with stub
-- host constants, and print/compare what controller_info() returns.
-- usage: lua harness.lua <logic|mainstage> <script> [reference script]

local mode, script, reference = ...

local function host_env()
	local env = {
		print = function() end, -- scripts print a lot; keep output clean
		MIDI_LSB = -1, MIDI_MSB = -2, MIDI_Wildcard = -3, MIDI_CtrChange = 0xB0,
		FB_OFF = 100, FB_TEXTONLY = 101,
	}
	if mode == "logic" then -- names only Logic/GarageBand define
		local n = 200
		for _, k in ipairs({"AUPAN", "AUVOLUME", "CS_COLOR", "CS_INSTRUMENT", "CS_INSTRUMENTPAR1",
			"CS_MUTE", "CS_NAME", "CS_RECRDY", "CS_SMARTCONTROL1", "CS_SOLO", "CS_INSTOPEN",
			"kAssign1sComplement", "kAssignRelative"}) do
			n = n + 1; env[k] = n
		end
	end
	return setmetatable(env, {__index = _G})
end

local function load_script(path)
	local env = host_env()
	local chunk = assert(loadfile(path, "t", env))
	chunk()
	return env
end

local function same(a, b, path)
	if type(a) ~= type(b) then return false, path .. ": " .. tostring(a) .. " vs " .. tostring(b) end
	if type(a) ~= "table" then
		if a == b then return true end
		return false, path .. ": " .. tostring(a) .. " vs " .. tostring(b)
	end
	for k, v in pairs(a) do
		local ok, why = same(v, b[k], path .. "." .. tostring(k))
		if not ok then return false, why end
	end
	for k in pairs(b) do
		if a[k] == nil then return false, path .. "." .. tostring(k) .. " missing" end
	end
	return true
end

local env = load_script(script)
local info = env.controller_info()
local ports, nassign = {}, info.assignments and #info.assignments or 0
for _, item in ipairs(info.items) do
	local key = "inport=" .. tostring(item.inport) .. " outport=" .. tostring(item.outport)
	ports[key] = (ports[key] or 0) + 1
end
print(("mode=%s  IS_MAINSTAGE=%s  model=%s  items=%d  assignments=%d  logicprox=%s"):format(
	mode, tostring(env.IS_MAINSTAGE), info.model, #info.items, nassign, tostring(info.logicprox)))
for k, v in pairs(ports) do print("  ports: " .. k .. "  x" .. v) end

local cbs = {}
for _, f in ipairs({"controller_info", "controller_initialize", "controller_finalize", "controller_midi_in",
	"controller_select_patch", "CSLongLabel", "CSFeedback", "CSFeedbackText"}) do
	if type(rawget(env, f)) == "function" then cbs[#cbs + 1] = f end
end
print("  callbacks: " .. table.concat(cbs, " "))

local init = env.controller_initialize(mode == "logic" and "GarageBand" or "MainStage", true)
print(("  initialize -> outport=%s, %d message(s)"):format(tostring(init.outport), #init.midi))

if reference then
	local ref = load_script(reference)
	local ok, why = same(info, ref.controller_info(), "info")
	print("  controller_info identical to " .. reference .. ": " .. (ok and "yes" or ("NO  " .. why)))
	local ok2, why2 = same(init, ref.controller_initialize(mode == "logic" and "GarageBand" or "MainStage", true), "init")
	print("  controller_initialize identical: " .. (ok2 and "yes" or ("NO  " .. why2)))
end
