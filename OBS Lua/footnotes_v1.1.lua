-- ==========================================================
-- Black Feather Footnotes
-- footnotes_v1.1.lua
--
-- Compatibility wrapper around footnotes.lua that moves the
-- default notes file into the optional Broadcast module while
-- preserving custom selections and data-based cover art.
-- ==========================================================

local obs = obslua

dofile(script_path() .. "footnotes.lua")

local legacy_script_defaults = script_defaults
local legacy_script_update = script_update

local function trim(value)
    return (value or ""):gsub("^%s+", ""):gsub("%s+$", "")
end

local function path_join(base, child)
    if not base or base == "" then
        return child
    end
    if base:sub(-1) == "\\" or base:sub(-1) == "/" then
        return base .. child
    end
    return base .. "\\" .. child
end

local function normalize_path(value)
    local normalized = trim(value):gsub("/", "\\"):gsub("\\+$", "")
    return normalized:lower()
end

local function legacy_data_folder()
    return path_join(script_path(), "..\\data")
end

local function default_footnotes_file()
    return path_join(script_path(), "..\\modules\\broadcast\\resources\\footnotes.txt")
end

local function is_legacy_default(path_value)
    local current = normalize_path(path_value)
    if current == "" then
        return true
    end

    local legacy = legacy_data_folder()
    local candidates = {
        path_join(legacy, "footnotes.json"),
        path_join(legacy, "footnotes.txt"),
        path_join(legacy, "notes.json"),
        path_join(legacy, "notes.txt"),
    }

    for _, candidate in ipairs(candidates) do
        if current == normalize_path(candidate) then
            return true
        end
    end
    return false
end

function script_defaults(settings)
    legacy_script_defaults(settings)
    obs.obs_data_set_default_string(settings, "footnotes_file", default_footnotes_file())
end

function script_update(settings)
    local current = obs.obs_data_get_string(settings, "footnotes_file")
    if is_legacy_default(current) then
        obs.obs_data_set_string(settings, "footnotes_file", default_footnotes_file())
    end
    legacy_script_update(settings)
end
