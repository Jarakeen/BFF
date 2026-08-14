
obs=obslua
local JSON_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\CurrentExpedition.json]]
local COUNTER_FILE = [[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\FieldNoteCounter.txt]]
local WEATHER_FOLDER=[[C:\Users\nourg\OneDrive\Desktop\Black Feather Foundry\40_Stream Studio\OBS\Scripts\Foundry\Weather\]]

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


function script_update(settings)

    office.expedition =
        obs.obs_data_get_string(settings,"expedition")

    office.difficulty =
        obs.obs_data_get_string(settings,"difficulty")

    office.objective =
        obs.obs_data_get_string(settings,"objective")

    office.weather =
        obs.obs_data_get_string(settings,"weather")

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
        FieldNoteNumber = "NOTE_FieldNoteNumber",
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
end

function script_description()
    return "Black Feather Foundry v1.3"
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
    print("Incident Report")
    return true
end

function script_load(settings)
    obs.timer_add(update, 1000)
end

function script_unload()
    obs.timer_remove(update)
end

