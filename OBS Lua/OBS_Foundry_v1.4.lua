
obs=obslua
local JSON_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\CurrentExpedition.json]]
local JSON_INCIDENT_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\CurrentIncident.json]]
local COUNTER_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\FieldNoteCounter.txt]]
local WEATHER_FOLDER=[[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\Weather\]]
local MARKER_LOG_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\MarkerLog.md]]
local STREAM_EVENTS_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\StreamEvents.json]]

----------------------------------------------------------
-- Chapter Marker Tracking
----------------------------------------------------------

local auto_chapters_enabled = true

local marker_state = {
    field_note_number = nil,
    field_note_initialized = false,
    incident_report_number = nil,
    incident_initialized = false,
}

-- Tracks elapsed time ourselves, since the frontend API doesn't expose
-- "current position" directly to scripts. Streaming has no pause concept in
-- OBS, so only recording needs pause tracking.
local stream_started_at = nil

local recording_started_at = nil
local recording_paused_at = nil
local recording_paused_total = 0

local function get_stream_elapsed_seconds()
    if not stream_started_at then return nil end
    return os.time() - stream_started_at
end

local function get_recording_elapsed_seconds()
    if not recording_started_at then return nil end
    local paused = recording_paused_total
    if recording_paused_at then
        paused = paused + (os.time() - recording_paused_at)
    end
    return os.time() - recording_started_at - paused
end

local function format_elapsed(seconds, inactive_label)
    if not seconds then return inactive_label end
    local h = math.floor(seconds / 3600)
    local m = math.floor((seconds % 3600) / 60)
    local s = seconds % 60
    return string.format("%02d:%02d:%02d", h, m, s)
end

local function log_marker(label)
    local stream_elapsed = format_elapsed(get_stream_elapsed_seconds(), "not streaming")
    local recording_elapsed = format_elapsed(get_recording_elapsed_seconds(), "not recording")
    local line = string.format(
        "%s | %s | Stream: %s | Recording: %s\n",
        os.date("%Y-%m-%d %H:%M:%S"),
        label,
        stream_elapsed,
        recording_elapsed
    )
    local f = io.open(MARKER_LOG_FILE, "a")
    if f then
        f:write(line)
        f:close()
    end
end

local function on_recording_frontend_event(event)
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED then
        stream_started_at = os.time()
    elseif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED then
        stream_started_at = nil
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED then
        recording_started_at = os.time()
        recording_paused_at = nil
        recording_paused_total = 0
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED then
        recording_started_at = nil
        recording_paused_at = nil
        recording_paused_total = 0
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_PAUSED then
        recording_paused_at = os.time()
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_UNPAUSED then
        if recording_paused_at then
            recording_paused_total = recording_paused_total + (os.time() - recording_paused_at)
            recording_paused_at = nil
        end
    end
end

----------------------------------------------------------
-- Field Office State
----------------------------------------------------------

local office = {

    expedition = "",
    difficulty = "",
    objective = "",

    weather = "Clear",


}

----------------------------------------------------------
-- Write Current Expedition
----------------------------------------------------------

local function save_json()

    local f = io.open(JSON_FILE,"w")

    if not f then
        print("Couldn't open JSON file!")
        return
    end

    f:write("{\n")

    f:write(string.format('    "Expedition":"%s",\n', office.expedition))
    f:write(string.format('    "Difficulty":"%s",\n', office.difficulty))
    f:write(string.format('    "Objective":"%s",\n', office.objective))
    f:write(string.format('    "Weather":"%s"\n', office.weather))

    f:write("}")

    f:close()

    print("JSON Saved.")

end

--------------------------------------------------
-- Weather Engine
--------------------------------------------------
local WEATHER_FILES={
["Clear"]="clear.png",
["Partly Cloudy"]="partly_cloudy.png",
["Cloudy"]="cloudy.png",
["Light Rain"]="rain_light.png",
["Heavy Rain"]="rain_heavy.png",
["Storm"]="storm.png",
["Fog"]="fog.png",
["Snow"]="snow.png",
["Windy"]="wind.png"
}

local function read_file(path)
 local f=io.open(path,"r")
 if not f then return nil end
 local t=f:read("*all")
 f:close()
 return t
end

local function extract(key,text)
 if not text then return "" end
 return string.match(text,'"'..key..'"%s*:%s*"([^"]*)"') or ""
end

local function extract_num(key, text)
    if not text then return nil end
    local val = string.match(text, '"'..key..'"%s*:%s*(-?%d+)')
    if val then return tonumber(val) end
    return nil
end

local function switch_scene(name)
    -- DISABLED: calling obs_frontend_set_current_scene() from a script timer
    -- callback is a confirmed, long-standing OBS crash/freeze bug (OBS GitHub
    -- issues #3385, #6151, #7516). Scene switching now goes through
    -- ObsWebSocketService on the Python side (SetCurrentProgramScene over
    -- OBS's WebSocket server), which doesn't have this problem. This
    -- function is kept only so nothing breaks if StreamEvents.json ever
    -- has a SceneName again; it deliberately no-ops instead of switching.
    if name and name ~= "" then
        print("Foundry: scene switch to '" .. name .. "' requested via Lua but is disabled - use OBS WebSocket instead")
    end
end

local function set_text(name,val)
 local s=obs.obs_get_source_by_name(name)
 if not s then return end
 local d=obs.obs_data_create()
 obs.obs_data_set_string(d,"text",tostring(val))
 obs.obs_source_update(s,d)
 obs.obs_data_release(d)
 obs.obs_source_release(s)
end

local function set_image(name,file)
 local s=obs.obs_get_source_by_name(name)
 if not s then return end
 local d=obs.obs_source_get_settings(s)
 obs.obs_data_set_string(d,"file",file)
 obs.obs_source_update(s,d)
 obs.obs_data_release(d)
 obs.obs_source_release(s)
end

----------------------------------------------------------
-- Tamriel Calendar
----------------------------------------------------------

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

----------------------------------------------------------
-- Field Note Counter
----------------------------------------------------------

local function get_field_note_number()

    local file = io.open(COUNTER_FILE, "r")

    if file == nil then
        return 1
    end

    local number = tonumber(file:read("*all")) or 1

    file:close()

    return number

end

local function save_field_note_number(number)

    local file = io.open(COUNTER_FILE, "w")

    if file then
        file:write(tostring(number))
        file:close()
    end

end

local function next_field_note()

    local number = get_field_note_number()

    number = number + 1

    save_field_note_number(number)

    return number

end

----------------------------------------------------------
-- Checkbox Image
----------------------------------------------------------

local CHECK_FOLDER = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\]]

function set_checkbox(source_name, checked)

    local filename

    if checked then
        filename = "check.png"
    else
        filename = "blank.png"
    end

    local source = obs.obs_get_source_by_name(source_name)

    if source ~= nil then

        local settings = obs.obs_source_get_settings(source)

        obs.obs_data_set_string(
            settings,
            "file",
            CHECK_FOLDER .. filename
        )

        obs.obs_source_update(source, settings)

        obs.obs_data_release(settings)
        obs.obs_source_release(source)

    end

end

----------------------------------------------------------
-- Tamriel Date
----------------------------------------------------------

local function get_tamriel_date()

    ------------------------------------------------------
    -- Anchor Date
    ------------------------------------------------------

    local anchorEarth = os.time({
        year = 2026,
        month = 7,
        day = 23,
        hour = 12
    })

    local anchorDay = 23
    local anchorMonth = 7      -- Sun's Height
    local anchorYear = 582

    ------------------------------------------------------

    local today = os.time()

    local days = math.floor((today - anchorEarth) / 86400)

    local day = anchorDay + days
    local month = anchorMonth
    local year = anchorYear

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

    local weekday = TAMRIEL_WEEKDAYS[((days % 7) + 7) % 7 + 1]

    local suffix = "th"

    if day % 10 == 1 and day ~= 11 then
        suffix = "st"
    elseif day % 10 == 2 and day ~= 12 then
        suffix = "nd"
    elseif day % 10 == 3 and day ~= 13 then
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


function script_defaults(settings)
    obs.obs_data_set_default_bool(settings, "auto_chapters", true)
end

function script_update(settings)

    office.expedition =
        obs.obs_data_get_string(settings,"expedition")

    office.difficulty =
        obs.obs_data_get_string(settings,"difficulty")

    office.objective =
        obs.obs_data_get_string(settings,"objective")

    office.weather =
        obs.obs_data_get_string(settings,"weather")

    auto_chapters_enabled =
        obs.obs_data_get_bool(settings,"auto_chapters")

end


local function update()
    local json = read_file(JSON_FILE)
    if not json then return end

    local fields = {
        Expedition = "TOP_Expedition",
        Difficulty = "TOP_Difficulty",
        Objective = "TOP_Objective",
        Weather = "TOP_Weather",
        Coffee = "TOP_Coffee",
        CoffeeLevel = "TOP_CoffeeLevel",
        Engineering = "TOP_Engineering",
        Incidents = "TOP_Incidents",
        Date = "CLIP_Date",
        Assignment = "CLIP_Assignment",
        FieldNoteNumber = "FN_Note_Number",
        Observation = "NOTE_Observation",
        Context = "NOTE_Context",
        NextSteps = "NOTE_NextSteps"
    }

    for key, source in pairs(fields) do
        if key == "Date" then
            set_text(source, get_tamriel_date())
        elseif key == "FieldNoteNumber" then
            set_text(source, tostring(get_field_note_number()))
        else
            set_text(source, extract(key, json))
        end
    end

    -- Field Note section mirrors the Top Bar's Expedition/Objective values
    set_text("FN_Expedition", extract("Expedition", json))
    set_text("FN_Location", extract("Objective", json))

    local w = extract("Weather", json)
    local f = WEATHER_FILES[w]
    if f then
        set_image("TOP_Weather_Icon", WEATHER_FOLDER .. f)
    end

    local status = json:match('"Status"%s*:%s*{(.-)}')
    if status then
        set_checkbox("CHK_Status_Observe", status:match('"Observe"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Document", status:match('"Document"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Learn", status:match('"Learn"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Share_the_Lesson", status:match('"ShareTheLesson"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_In_Progress", status:match('"InProgress"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Complete", status:match('"Complete"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Under_Review", status:match('"UnderReview"%s*:%s*true') ~= nil)
    end

    local field_note_number = get_field_note_number()
    if marker_state.field_note_initialized then
        if auto_chapters_enabled and field_note_number ~= marker_state.field_note_number then
            obs.obs_frontend_recording_add_chapter("Field Note " .. tostring(field_note_number))
            log_marker("Field Note " .. tostring(field_note_number))
        end
    else
        marker_state.field_note_initialized = true
    end
    marker_state.field_note_number = field_note_number
end

----------------------------------------------------------
-- Incident Report
----------------------------------------------------------

local SEVERITY_CHECKBOXES = {
    Minor = "CHK_Sev_Minor",
    Moderate = "CHK_Sev_Moderate",
    Major = "CHK_Sev_Major",
    Critical = "CHK_Sev_Critical",
}

local function update_incident()
    local json = read_file(JSON_INCIDENT_FILE)
    if not json then return end

    local fields = {
        Location = "IR_Location",
        Department = "IR_Dept",
        Summary = "IR_Suamary",
        SuspectedCause = "IR_Suspected_Cause",
        EngineeringAssessment = "IR_Engineering_Assessment",
        CoffeeRecommendation = "IR_Coffee_Reccomendation",
        Observations = "IR_Observations",
        ActionsTaken = "IR_Actions_Taken",
        Recommendations = "IR_Reccomendations",
        ReportNumber = "IR_Note_Number",
        OutstandingQuestions = "IR_Outstanding_Questions"
    }

    for key, source in pairs(fields) do
        set_text(source, extract(key, json))
    end

    local severity = extract("Severity", json)
    for level, source in pairs(SEVERITY_CHECKBOXES) do
        set_checkbox(source, level == severity)
    end

    local party = json:match('"ResponsibleParty"%s*:%s*{(.-)}')
    if party then
        set_checkbox("CHK_Moose_Gremlin", party:match('"MooseGremlin"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Lag", party:match('"Lag"%s*:%s*true') ~= nil)
        set_checkbox("CHK_User_Error", party:match('"UserError"%s*:%s*true') ~= nil)
        set_checkbox("CHK_ESO", party:match('"ESO"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Unknown", party:match('"Unknown"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Under_Investigation", party:match('"UnderInvestigation"%s*:%s*true') ~= nil)
    end

    local status = json:match('"Status"%s*:%s*{(.-)}')
    if status then
        set_checkbox("CHK_Filed", status:match('"Filed"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Pending_Review", status:match('"PendingReview"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Requires_Follow_Up", status:match('"RequiresFollowUp"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Archived", status:match('"Archived"%s*:%s*true') ~= nil)
    end

    local report_number = extract("ReportNumber", json)
    if report_number ~= "" then
        if marker_state.incident_initialized then
            if auto_chapters_enabled and report_number ~= marker_state.incident_report_number then
                obs.obs_frontend_recording_add_chapter("Incident " .. report_number)
                log_marker("Incident " .. report_number)
            end
        else
            marker_state.incident_initialized = true
        end
        marker_state.incident_report_number = report_number
    end
end

----------------------------------------------------------
-- Stream Events (Stream Events tab buttons)
----------------------------------------------------------

local stream_event_state = {
    sequence = nil,
    initialized = false,
}

local NARRATOR_GROUP_NAME = "NAR Note"
local NARRATOR_HIDE_DELAY_MS = 30000

local function set_group_visible(group_name, visible)
    local scenes = obs.obs_frontend_get_scenes()
    if not scenes then return end
    for _, scene_source in ipairs(scenes) do
        local scene = obs.obs_scene_from_source(scene_source)
        if scene then
            local item = obs.obs_scene_find_source(scene, group_name)
            if item then
                obs.obs_sceneitem_set_visible(item, visible)
            end
        end
    end
    obs.source_list_release(scenes)
end

local function hide_narrator_note()
    set_group_visible(NARRATOR_GROUP_NAME, false)
    obs.remove_current_callback()
end

local function show_narrator_note()
    set_group_visible(NARRATOR_GROUP_NAME, true)
    -- Remove any previously pending hide so back-to-back notes each get
    -- their own full 30 seconds rather than being cut short by an older timer.
    obs.timer_remove(hide_narrator_note)
    obs.timer_add(hide_narrator_note, NARRATOR_HIDE_DELAY_MS)
end

local function update_stream_events()
    local json = read_file(STREAM_EVENTS_FILE)
    if not json then return end

    local sequence = extract_num("Sequence", json)
    if sequence == nil then return end

    if not stream_event_state.initialized then
        stream_event_state.initialized = true
        stream_event_state.sequence = sequence
        return
    end

    if sequence == stream_event_state.sequence then
        return
    end
    stream_event_state.sequence = sequence

    local chapter_label = extract("ChapterLabel", json)
    if chapter_label ~= "" then
        if auto_chapters_enabled then
            obs.obs_frontend_recording_add_chapter(chapter_label)
        end
        log_marker(chapter_label)
    else
        local log_label = extract("LogLabel", json)
        if log_label ~= "" then
            log_marker(log_label)
        end
    end

    -- Scene changes are intentionally not performed from this timer callback.
    -- FoundryDock uses OBS WebSocket instead, keeping this timer deadlock-free.

    local narrator_text = extract("NarratorText", json)
    if narrator_text ~= "" then
        set_text("NR_Note", narrator_text)
        show_narrator_note()
    end
end

local function update_all()
    update()
    update_incident()
    update_stream_events()
end

function script_description()
    return "Black Feather Foundry v1.5 (WebSocket scene switching)"
end

function script_properties()
    local props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "expedition", "Expedition", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "difficulty", "Difficulty", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "objective", "Objective", obs.OBS_TEXT_DEFAULT)

    local weather = obs.obs_properties_add_list(
        props,
        "weather",
        "Weather",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING
    )

    obs.obs_property_list_add_string(weather, "Clear", "Clear")
    obs.obs_property_list_add_string(weather, "Partly Cloudy", "Partly Cloudy")
    obs.obs_property_list_add_string(weather, "Cloudy", "Cloudy")
    obs.obs_property_list_add_string(weather, "Light Rain", "Light Rain")
    obs.obs_property_list_add_string(weather, "Heavy Rain", "Heavy Rain")
    obs.obs_property_list_add_string(weather, "Storm", "Storm")
    obs.obs_property_list_add_string(weather, "Fog", "Fog")
    obs.obs_property_list_add_string(weather, "Snow", "Snow")
    obs.obs_property_list_add_string(weather, "Windy", "Windy")

    obs.obs_properties_add_button(props, "save", "Save Expedition", save_pressed)
    obs.obs_properties_add_button(props, "incident", "Refresh Incident Report", incident_pressed)
    obs.obs_properties_add_bool(props, "auto_chapters", "Auto chapter marker on new Field Note / Incident")

    return props
end

function save_pressed(props, property)
    save_json()
    update()
    return true
end

function new_field_note_pressed(props, property)
    print("New Field Note")
    return true
end

function incident_pressed(props, property)
    update_incident()
    print("Incident Report refreshed")
    return true
end

function script_load(settings)
    obs.timer_add(update_all, 1000)
    obs.obs_frontend_add_event_callback(on_recording_frontend_event)
end

function script_unload()
    obs.timer_remove(update_all)
    obs.obs_frontend_remove_event_callback(on_recording_frontend_event)
end
