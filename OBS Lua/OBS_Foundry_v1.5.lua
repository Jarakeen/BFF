-- ==========================================================
-- Black Feather Foundry
--
-- OBS_Foundry_v1.5.lua
--
-- CurrentBroadcast.json is the live source of truth.
--
-- Updates:
--   Broadcast header
--   Top Bar
--   Clipboard
--   Field Notes
--   Field Note status checkboxes
--   Weather icon
--
-- ==========================================================

obs = obslua


-- ==========================================================
-- FILE PATHS
-- ==========================================================

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

local function default_data_folder()
    return path_join(script_path(), "..\\data")
end

local broadcast_state_folder = default_data_folder()
local broadcast_resource_folder = default_data_folder()

local BROADCAST_FILE = ""
local COUNTER_FILE = ""
local WEATHER_FOLDER = ""
local MARKER_LOG_FILE = ""
local CHECK_FOLDER = ""

local function configure_paths(state_folder, resource_folder)
    local state = trim(state_folder)
    local resources = trim(resource_folder)

    if state == "" then
        state = default_data_folder()
    end
    if resources == "" then
        resources = default_data_folder()
    end

    broadcast_state_folder = state
    broadcast_resource_folder = resources
    BROADCAST_FILE = path_join(state, "CurrentBroadcast.json")
    COUNTER_FILE = path_join(state, "FieldNoteCounter.txt")
    MARKER_LOG_FILE = path_join(state, "MarkerLog.md")
    WEATHER_FOLDER = path_join(resources, "Weather") .. "\\"
    CHECK_FOLDER = resources .. (resources:sub(-1) == "\\" and "" or "\\")
end

configure_paths(broadcast_state_folder, broadcast_resource_folder)


-- ==========================================================
-- SETTINGS
-- ==========================================================

local auto_chapters_enabled = true


-- ==========================================================
-- MARKER STATE
-- ==========================================================

local marker_state = {
    field_note_number = nil,
    field_note_initialized = false,
}


-- ==========================================================
-- STREAM / RECORDING TIMING
-- ==========================================================

local stream_started_at = nil

local recording_started_at = nil
local recording_paused_at = nil
local recording_paused_total = 0


local function get_stream_elapsed_seconds()

    if not stream_started_at then
        return nil
    end

    return os.time() - stream_started_at

end


local function get_recording_elapsed_seconds()

    if not recording_started_at then
        return nil
    end

    local paused = recording_paused_total

    if recording_paused_at then
        paused = paused + (
            os.time() - recording_paused_at
        )
    end

    return os.time() - recording_started_at - paused

end


local function format_elapsed(
    seconds,
    inactive_label
)

    if not seconds then
        return inactive_label
    end

    local h = math.floor(
        seconds / 3600
    )

    local m = math.floor(
        (seconds % 3600) / 60
    )

    local s = seconds % 60

    return string.format(
        "%02d:%02d:%02d",
        h,
        m,
        s
    )

end


local function log_marker(label)

    local stream_elapsed =
        format_elapsed(
            get_stream_elapsed_seconds(),
            "not streaming"
        )

    local recording_elapsed =
        format_elapsed(
            get_recording_elapsed_seconds(),
            "not recording"
        )

    local line = string.format(
        "%s | %s | Stream: %s | Recording: %s\n",
        os.date("%Y-%m-%d %H:%M:%S"),
        label,
        stream_elapsed,
        recording_elapsed
    )

    local f = io.open(
        MARKER_LOG_FILE,
        "a"
    )

    if f then

        f:write(line)

        f:close()

    end

end


-- ==========================================================
-- OBS FRONTEND EVENTS
-- ==========================================================

function script_load_frontend_event(event)

    if event ==
        obs.OBS_FRONTEND_EVENT_STREAMING_STARTED then

        stream_started_at = os.time()

    elseif event ==
        obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED then

        stream_started_at = nil

    elseif event ==
        obs.OBS_FRONTEND_EVENT_RECORDING_STARTED then

        recording_started_at = os.time()

        recording_paused_at = nil

        recording_paused_total = 0

    elseif event ==
        obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED then

        recording_started_at = nil

        recording_paused_at = nil

        recording_paused_total = 0

    elseif event ==
        obs.OBS_FRONTEND_EVENT_RECORDING_PAUSED then

        recording_paused_at = os.time()

    elseif event ==
        obs.OBS_FRONTEND_EVENT_RECORDING_UNPAUSED then

        if recording_paused_at then

            recording_paused_total =
                recording_paused_total
                + (
                    os.time()
                    - recording_paused_at
                )

            recording_paused_at = nil

        end

    end

end


-- ==========================================================
-- FILE READING
-- ==========================================================

local function read_file(path)

    local f = io.open(
        path,
        "r"
    )

    if not f then
        return nil
    end

    local text = f:read("*all")

    f:close()

    return text

end


-- ==========================================================
-- SIMPLE JSON EXTRACTION
-- ==========================================================

local function extract(
    key,
    text
)

    if not text then
        return ""
    end

    return string.match(
        text,
        '"' .. key .. '"%s*:%s*"([^"]*)"'
    ) or ""

end


-- ==========================================================
-- OBS TEXT
-- ==========================================================

local function set_text(
    source_name,
    value
)

    local source =
        obs.obs_get_source_by_name(
            source_name
        )

    if not source then

        print(
            "Foundry: OBS text source not found: "
            .. source_name
        )

        return

    end

    local settings =
        obs.obs_data_create()

    obs.obs_data_set_string(
        settings,
        "text",
        tostring(value or "")
    )

    obs.obs_source_update(
        source,
        settings
    )

    obs.obs_data_release(
        settings
    )

    obs.obs_source_release(
        source
    )

end


-- ==========================================================
-- WEATHER
-- ==========================================================

local WEATHER_FILES = {

    ["Clear"] =
        "clear.png",

    ["Partly Cloudy"] =
        "partly_cloudy.png",

    ["Cloudy"] =
        "cloudy.png",

    ["Light Rain"] =
        "rain_light.png",

    ["Heavy Rain"] =
        "rain_heavy.png",

    ["Storm"] =
        "storm.png",

    ["Fog"] =
        "fog.png",

    ["Snow"] =
        "snow.png",

    ["Windy"] =
        "wind.png",

}


local function set_image(
    source_name,
    file
)

    local source =
        obs.obs_get_source_by_name(
            source_name
        )

    if not source then

        print(
            "Foundry: OBS image source not found: "
            .. source_name
        )

        return

    end

    local settings =
        obs.obs_source_get_settings(
            source
        )

    obs.obs_data_set_string(
        settings,
        "file",
        file
    )

    obs.obs_source_update(
        source,
        settings
    )

    obs.obs_data_release(
        settings
    )

    obs.obs_source_release(
        source
    )

end


-- ==========================================================
-- CHECKBOX IMAGES
-- ==========================================================

local function set_checkbox(
    source_name,
    checked
)

    local filename

    if checked then

        filename = "check.png"

    else

        filename = "blank.png"

    end


    local source =
        obs.obs_get_source_by_name(
            source_name
        )

    if not source then

        print(
            "Foundry: checkbox source not found: "
            .. source_name
        )

        return

    end


    local settings =
        obs.obs_source_get_settings(
            source
        )

    obs.obs_data_set_string(
        settings,
        "file",
        CHECK_FOLDER .. filename
    )

    obs.obs_source_update(
        source,
        settings
    )

    obs.obs_data_release(
        settings
    )

    obs.obs_source_release(
        source
    )

end


-- ==========================================================
-- TAMRIEL CALENDAR
-- ==========================================================

local TAMRIEL_MONTHS = {

    "Morning Star",
    "Sun's Dawn",
    "First Seed",
    "Rain's Hand",
    "Second Seed",
    "Mid Year",
    "Sun's Height",
    "Last Seed",
    "Hearthfire",
    "Frostfall",
    "Sun's Dusk",
    "Evening Star"

}


local TAMRIEL_WEEKDAYS = {

    "Morndas",
    "Tirdas",
    "Middas",
    "Turdas",
    "Fredas",
    "Loredas",
    "Sundas"

}


local function get_tamriel_date()

    local anchorEarth =
        os.time({
            year = 2026,
            month = 7,
            day = 23,
            hour = 12
        })

    local anchorDay = 23
    local anchorMonth = 7
    local anchorYear = 582

    local today = os.time()

    local days =
        math.floor(
            (today - anchorEarth)
            / 86400
        )

    local day =
        anchorDay + days

    local month =
        anchorMonth

    local year =
        anchorYear


    while day > 30 do

        day = day - 30

        month = month + 1

        if month > 12 then

            month = 1

            year = year + 1

        end

    end


    while day < 1 do

        month = month - 1

        if month < 1 then

            month = 12

            year = year - 1

        end

        day = day + 30

    end


    local weekday =
        TAMRIEL_WEEKDAYS[
            ((days % 7) + 7) % 7 + 1
        ]


    local suffix = "th"


    if day % 10 == 1
        and day ~= 11 then

        suffix = "st"

    elseif day % 10 == 2
        and day ~= 12 then

        suffix = "nd"

    elseif day % 10 == 3
        and day ~= 13 then

        suffix = "rd"

    end


    return string.format(
        "%s, %d%s of %s\n2E %d",
        weekday,
        day,
        suffix,
        TAMRIEL_MONTHS[month],
        year
    )

end


-- ==========================================================
-- FIELD NOTE COUNTER
-- ==========================================================

local function get_field_note_number()

    local file =
        io.open(
            COUNTER_FILE,
            "r"
        )

    if not file then
        return 1
    end

    local number =
        tonumber(
            file:read("*all")
        ) or 1

    file:close()

    return number

end


local function save_field_note_number(
    number
)

    local file =
        io.open(
            COUNTER_FILE,
            "w"
        )

    if file then

        file:write(
            tostring(number)
        )

        file:close()

    end

end


local function next_field_note()

    local number =
        get_field_note_number()

    number =
        number + 1

    save_field_note_number(
        number
    )

    return number

end


-- ==========================================================
-- BROADCAST UPDATE
-- ==========================================================

local function update_broadcast()

    local json =
        read_file(
            BROADCAST_FILE
        )


    if not json then

        print(
            "Foundry: couldn't read CurrentBroadcast.json:"
        )

        print(
            BROADCAST_FILE
        )

        return

    end


    ----------------------------------------------------------
    -- Broadcast Header
    ----------------------------------------------------------

    set_text(
        "TXT_title",
        extract(
            "Title",
            json
        )
    )


    set_text(
        "TXT_team",
        extract(
            "Team",
            json
        )
    )


    set_text(
        "TXT_notify",
        extract(
            "Notification",
            json
        )
    )


    ----------------------------------------------------------
    -- Top Bar
    ----------------------------------------------------------

    set_text(
        "TOP_Expedition",
        extract(
            "Expedition",
            json
        )
    )


    set_text(
        "TOP_Location",
        extract(
            "Location",
            json
        )
    )


    set_text(
        "TOP_Objective",
        extract(
            "Objective",
            json
        )
    )


    set_text(
        "TOP_Weather",
        extract(
            "Weather",
            json
        )
    )


    set_text(
        "TOP_Coffee",
        extract(
            "Coffee",
            json
        )
    )


    set_text(
        "TOP_CoffeeLevel",
        extract(
            "CoffeeLevel",
            json
        )
    )


    set_text(
        "TOP_Incidents",
        extract(
            "Incidents",
            json
        )
    )


    set_text(
        "TOP_Difficulty",
        extract(
            "Difficulty",
            json
        )
    )


    set_text(
        "TOP_Engineering",
        extract(
            "Engineering",
            json
        )
    )


    ----------------------------------------------------------
    -- Clipboard
    ----------------------------------------------------------

    set_text(
        "CLIP_Assignment",
        extract(
            "Assignment",
            json
        )
    )


    ----------------------------------------------------------
    -- Field Notes
    ----------------------------------------------------------

    set_text(
        "NOTE_Observation",
        extract(
            "Observation",
            json
        )
    )


    set_text(
        "NOTE_Context",
        extract(
            "Context",
            json
        )
    )


    set_text(
        "NOTE_NextSteps",
        extract(
            "NextSteps",
            json
        )
    )

----------------------------------------------------------
-- Field Notes
----------------------------------------------------------

set_text(
    "FN_Expedition",
    extract(
        "Objective",
        json
    )
)

set_text(
    "FN_Location",
    extract(
        "Location",
        json
    )
)


    ----------------------------------------------------------
    -- Weather Icon
    ----------------------------------------------------------

    local weather =
        extract(
            "Weather",
            json
        )

    local weather_file =
        WEATHER_FILES[weather]


    if weather_file then

        set_image(
            "TOP_Weather_Icon",
            WEATHER_FOLDER
            .. weather_file
        )

    end


    ----------------------------------------------------------
    -- Field Note Status
    ----------------------------------------------------------

    local status =
        json:match(
            '"Status"%s*:%s*{(.-)}'
        )


    if status then

        set_checkbox(
            "CHK_Status_Observe",

            status:match(
                '"Observe"%s*:%s*true'
            ) ~= nil

        )


        set_checkbox(
            "CHK_Status_Document",

            status:match(
                '"Document"%s*:%s*true'
            ) ~= nil

        )


        set_checkbox(
            "CHK_Status_Learn",

            status:match(
                '"Learn"%s*:%s*true'
            ) ~= nil

        )


        set_checkbox(
            "CHK_Status_Share_the_Lesson",

            status:match(
                '"ShareTheLesson"%s*:%s*true'
            ) ~= nil

        )

    end


    print(
        "Foundry: CurrentBroadcast updated."
    )

end


-- ==========================================================
-- UPDATE LOOP
-- ==========================================================

local function update_all()

    update_broadcast()

end


-- ==========================================================
-- SCRIPT DESCRIPTION
-- ==========================================================

function script_description()

    return [[
Black Feather Foundry

Reads CurrentBroadcast.json and updates
the Foundry OBS overlay.

Broadcast state and resource folders are configurable,
so the script does not depend on a machine-specific path.

Updates once per second.
]]

end


-- ==========================================================
-- SCRIPT DEFAULTS
-- ==========================================================

function script_defaults(settings)

    obs.obs_data_set_default_bool(
        settings,
        "auto_chapters",
        true
    )

    obs.obs_data_set_default_string(
        settings,
        "broadcast_state_folder",
        default_data_folder()
    )

    obs.obs_data_set_default_string(
        settings,
        "broadcast_resource_folder",
        default_data_folder()
    )

end


-- ==========================================================
-- SCRIPT PROPERTIES
-- ==========================================================

function script_properties()

    local props =
        obs.obs_properties_create()

    obs.obs_properties_add_path(
        props,
        "broadcast_state_folder",
        "Broadcast State Folder",
        obs.OBS_PATH_DIRECTORY,
        nil,
        nil
    )

    obs.obs_properties_add_path(
        props,
        "broadcast_resource_folder",
        "Broadcast Resource Folder",
        obs.OBS_PATH_DIRECTORY,
        nil,
        nil
    )

    obs.obs_properties_add_bool(
        props,
        "auto_chapters",
        "Automatic chapter markers"
    )

    return props

end


-- ==========================================================
-- SCRIPT UPDATE
-- ==========================================================

function script_update(settings)

    auto_chapters_enabled =
        obs.obs_data_get_bool(
            settings,
            "auto_chapters"
        )

    configure_paths(
        obs.obs_data_get_string(settings, "broadcast_state_folder"),
        obs.obs_data_get_string(settings, "broadcast_resource_folder")
    )

end


-- ==========================================================
-- SCRIPT LOAD
-- ==========================================================

function script_load(settings)

    print(
        ">>> FOUNDRY SCRIPT_LOAD <<<"
    )

    configure_paths(
        obs.obs_data_get_string(settings, "broadcast_state_folder"),
        obs.obs_data_get_string(settings, "broadcast_resource_folder")
    )

    obs.timer_add(
        update_all,
        1000
    )

end


-- ==========================================================
-- SCRIPT UNLOAD
-- ==========================================================

function script_unload()

    obs.timer_remove(
        update_all
    )

    print(
        ">>> FOUNDRY SCRIPT_UNLOAD <<<"
    )

end