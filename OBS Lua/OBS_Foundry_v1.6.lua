-- ==========================================================
-- Black Feather Foundry
-- OBS_Foundry_v1.6.lua
--
-- Compatibility wrapper around v1.5 that moves Broadcast
-- defaults out of core data while preserving custom OBS paths.
-- ==========================================================

local obs = obslua

dofile(script_path() .. "OBS_Foundry_v1.5.lua")

local legacy_script_update = script_update
local legacy_script_load = script_load
local legacy_script_description = script_description

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

local function default_broadcast_state_folder()
    return path_join(script_path(), "..\\user_data\\broadcast")
end

local function default_broadcast_resource_folder()
    return path_join(script_path(), "..\\modules\\broadcast\\resources")
end

local function migrate_legacy_setting(settings, key, replacement)
    local current = trim(obs.obs_data_get_string(settings, key))
    if current == "" or normalize_path(current) == normalize_path(legacy_data_folder()) then
        obs.obs_data_set_string(settings, key, replacement)
    end
end

local function migrate_broadcast_settings(settings)
    migrate_legacy_setting(
        settings,
        "broadcast_state_folder",
        default_broadcast_state_folder()
    )
    migrate_legacy_setting(
        settings,
        "broadcast_resource_folder",
        default_broadcast_resource_folder()
    )
end

function script_description()
    local original = legacy_script_description and legacy_script_description() or "Black Feather Foundry"
    return original .. "\n\nVersion 1.6 defaults Broadcast state to user_data/broadcast and resources to modules/broadcast/resources."
end

function script_defaults(settings)
    obs.obs_data_set_default_bool(settings, "auto_chapters", true)
    obs.obs_data_set_default_string(
        settings,
        "broadcast_state_folder",
        default_broadcast_state_folder()
    )
    obs.obs_data_set_default_string(
        settings,
        "broadcast_resource_folder",
        default_broadcast_resource_folder()
    )
end

function script_update(settings)
    migrate_broadcast_settings(settings)
    legacy_script_update(settings)
end

function script_load(settings)
    migrate_broadcast_settings(settings)
    legacy_script_load(settings)
end
