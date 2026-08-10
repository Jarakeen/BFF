local obs = obslua

local script_state = {
    source_name = "",
    footnotes_file = "",
    cover_art_file = "",
    interval = 30,
    min_interval = 15,
    max_interval = 45,
    max_chars_per_line = 48,
    variable_timing = false,
    enable_rare_notes = false,
    rare_note_chance = 15,
    auto_reload = true,

    notes = {},
    rare_notes = {},
    normal_order = {},
    normal_index = 1,
    displayed_count = 0,
    current_cycle = 0,
    current_note = nil,
    previous_note = nil,
    file_signature = nil,
    last_reload = "Never",
    last_error = "",
    last_status = "Waiting for notes.",
    settings = nil,
    timer_active = false,
}

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

local function find_default_footnotes_path()
    local scripts_dir = "C:\\Users\\nourg\\OneDrive\\Desktop\\BFF\\40_Stream Studio\\OBS\\Scripts\\FoundryDock\\Data"
    local candidates = {
        path_join(scripts_dir, "footnotes.json"),
        path_join(scripts_dir, "footnotes.txt"),
        path_join(scripts_dir, "notes.json"),
        path_join(scripts_dir, "notes.txt"),
    }

    for _, candidate in ipairs(candidates) do
        local file = io.open(candidate, "rb")
        if file then
            file:close()
            return candidate
        end
    end

    return path_join(scripts_dir, "footnotes.txt")
end

local function resolve_footnotes_path(path_value)
    local trimmed = trim(path_value)
    if trimmed ~= "" then
        return trimmed
    end

    return find_default_footnotes_path()
end

local function find_default_cover_art_path()
    local scripts_dir = "C:\\Users\\nourg\\OneDrive\\Desktop\\Black Feather Foundry\\40_Stream Studio\\OBS\\Scripts\\Foundrydock\\data"
    local candidates = {
        path_join(scripts_dir, "current_cover.png"),
        path_join(scripts_dir, "cover.png"),
        path_join(scripts_dir, "cover.jpg"),
        path_join(scripts_dir, "cover.jpeg"),
        path_join(scripts_dir, "cover.webp"),
    }

    for _, candidate in ipairs(candidates) do
        local file = io.open(candidate, "rb")
        if file then
            file:close()
            return candidate
        end
    end

    return path_join(scripts_dir, "current_cover.png")
end

local function resolve_cover_art_path(path_value)
    local trimmed = trim(path_value)
    if trimmed ~= "" then
        return trimmed
    end

    return find_default_cover_art_path()
end

local function normalize_newlines(text)
    return (text or ""):gsub("\r\n", "\n"):gsub("\r", "\n")
end

local function seed_random()
    math.randomseed(os.time() + math.floor((os.clock() or 0) * 1000000))
end

local function format_number(number)
    return string.format("%03d", tonumber(number) or 0)
end

local function choose_header(tag)
    local header_map = {
        RAMSEY = "RAMSEY REPORT",
        OONA = "OONA MEMORANDUM",
        DWEMER = "DWEMER OBSERVATION",
        WILDLIFE = "WILDLIFE LOG",
        CAMP = "CAMP INVENTORY",
        ARCHIVE = "ARCHIVIST'S NOTE",
    }

    if tag then
        local normalized = string.upper(trim(tag))
        if header_map[normalized] then
            return header_map[normalized]
        end
    end

    return "FIELD NOTE"
end

local function shuffle_list(list, avoid_first_id)
    if not list then
        return {}
    end

    local shuffled = {}
    for _, item in ipairs(list) do
        table.insert(shuffled, item)
    end

    if #shuffled <= 1 then
        return shuffled
    end

    seed_random()
    for i = #shuffled, 2, -1 do
        local j = math.random(i)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    end

    local attempts = 0
    while avoid_first_id and #shuffled > 1 and shuffled[1] and shuffled[1].id == avoid_first_id and attempts < 12 do
        for i = #shuffled, 2, -1 do
            local j = math.random(i)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
        end
        attempts = attempts + 1
    end

    return shuffled
end

local function assign_numbers(note_list)
    for index, note in ipairs(note_list) do
        note.number = index
    end
end

local function build_note_id(note_text, tag)
    return string.upper(trim(tag or "")) .. "::" .. string.lower(trim(note_text or ""))
end

local function wrap_text(text, max_width)
    if not text or text == "" then
        return {}
    end

    local tokens = {}
    local current = ""
    for i = 1, #text do
        local char = text:sub(i, i)
        if char:match("[%s,;%.%:%?!]") then
            if current ~= "" then
                table.insert(tokens, current)
                current = ""
            end
            if not char:match("%s") then
                table.insert(tokens, char)
            end
        else
            current = current .. char
        end
    end

    if current ~= "" then
        table.insert(tokens, current)
    end

    if #tokens == 0 then
        return {}
    end

    local lines = {}
    current = ""
    for _, token in ipairs(tokens) do
        local candidate = current == "" and token or current .. " " .. token
        if #candidate <= max_width then
            current = candidate
        else
            if current ~= "" then
                table.insert(lines, current)
            end
            current = token
        end
    end

    if current ~= "" then
        table.insert(lines, current)
    end

    return lines
end

local function render_note(note)
    if not note then
        return ""
    end

    local header = choose_header(note.tag)
    local prefix = header .. " " .. format_number(note.number) .. " • "
    local body_width = math.max(12, (script_state.max_chars_per_line or 48) - #prefix)
    local body_lines = wrap_text(note.text, body_width)

    if #body_lines == 0 then
        return prefix
    end

    local output = {}
    output[1] = prefix .. body_lines[1]
    for i = 2, #body_lines do
        output[#output + 1] = body_lines[i]
    end

    return table.concat(output, "\n")
end

local function update_status_text()
    local interval_text = script_state.variable_timing and
        string.format("%d-%d s", script_state.min_interval, script_state.max_interval) or
        string.format("%d s", script_state.interval)

    script_state.last_status = table.concat({
        "Loaded Notes: " .. tostring(#script_state.notes),
        "Displayed: " .. tostring(script_state.displayed_count),
        "Current Cycle: " .. tostring(script_state.current_cycle),
        "Last Reload: " .. tostring(script_state.last_reload),
        "Current Interval: " .. interval_text,
    }, "\n")

    if script_state.last_error ~= "" then
        script_state.last_status = script_state.last_status .. "\nLast Error: " .. script_state.last_error
    end

    if script_state.settings then
        obs.obs_data_set_string(script_state.settings, "status_display", script_state.last_status)
    end
end

local function start_new_cycle()
    if #script_state.notes == 0 then
        script_state.normal_order = {}
        script_state.normal_index = 1
        return
    end

    local previous_last_id = nil
    if script_state.previous_note then
        previous_last_id = script_state.previous_note.id
    end

    script_state.normal_order = shuffle_list(script_state.notes, previous_last_id)
    local first_note = script_state.normal_order[1]
    if first_note and script_state.previous_note and first_note.id == script_state.previous_note.id and #script_state.normal_order > 1 then
        local swapped = false
        for i = 2, #script_state.normal_order do
            if script_state.normal_order[i] and script_state.normal_order[i].id ~= script_state.previous_note.id then
                script_state.normal_order[1], script_state.normal_order[i] = script_state.normal_order[i], script_state.normal_order[1]
                swapped = true
                break
            end
        end
        if not swapped then
            script_state.normal_order = shuffle_list(script_state.notes, previous_last_id)
        end
    end

    script_state.normal_index = 1
    script_state.current_cycle = script_state.current_cycle + 1
end

local function schedule_next()
    local delay = script_state.interval
    if script_state.variable_timing then
        local minimum = math.max(1, math.min(script_state.interval, script_state.min_interval))
        local maximum = math.max(minimum, script_state.max_interval)
        delay = math.random(minimum, maximum)
    end

    script_state.current_interval = delay
    obs.timer_remove(next_note)
    obs.timer_add(next_note, delay * 1000)
end

local function update_obs(note)
    if not note then
        return
    end

    local source = obs.obs_get_source_by_name(script_state.source_name)
    if not source then
        script_state.last_error = "Source not found: " .. tostring(script_state.source_name)
        update_status_text()
        return
    end

    local rendered = render_note(note)
    local settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "text", rendered)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)
end

local function choose_next_note()
    if #script_state.notes == 0 then
        return nil
    end

    if #script_state.normal_order == 0 or script_state.normal_index > #script_state.normal_order then
        start_new_cycle()
    end

    local note = nil
    if script_state.enable_rare_notes and #script_state.rare_notes > 0 and math.random(100) <= script_state.rare_note_chance then
        local rare_index = math.random(#script_state.rare_notes)
        note = script_state.rare_notes[rare_index]
    else
        note = script_state.normal_order[script_state.normal_index]
        script_state.normal_index = script_state.normal_index + 1
    end

    if not note then
        return nil
    end

    script_state.displayed_count = script_state.displayed_count + 1
    script_state.previous_note = note
    script_state.current_note = note
    return note
end

function next_note()
    if script_state.auto_reload then
        reload_if_changed()
    end

    local note = choose_next_note()
    if note then
        update_obs(note)
    end

    update_status_text()
    if script_state.timer_active then
        schedule_next()
    end
end

local function parse_note_block(block)
    local lines = {}
    for line in normalize_newlines(block):gmatch("([^\n]+)") do
        table.insert(lines, line)
    end

    local tag = nil
    local content_lines = {}
    local seen_tag = false

    for _, raw_line in ipairs(lines) do
        local line = trim(raw_line)
        if line ~= "" then
            if line:match("^%[[^%]]+%]$") then
                local parsed_tag = line:match("^%[(.-)%]$")
                if parsed_tag and parsed_tag ~= "" then
                    tag = parsed_tag
                    seen_tag = true
                end
            else
                table.insert(content_lines, line)
            end
        end
    end

    local content = trim(table.concat(content_lines, " "))
    content = content:gsub("%s+", " ")

    if content == "" then
        return nil, "Skipped empty or malformed note"
    end

    if seen_tag and not tag then
        return nil, "Skipped malformed tag"
    end

    return {
        text = content,
        tag = tag,
        number = 0,
        rare = (tag and string.upper(trim(tag)) == "RARE") or false,
        id = build_note_id(content, tag),
    }
end

local function parse_json_note_records(text)
    local notes = {}
    local seen = {}

    for block in text:gmatch("%b{}") do
        local note_text = block:match('"text"%s*:%s*"(.-)"')
        local note_tag = block:match('"tag"%s*:%s*"(.-)"')
        if note_text and note_text ~= "" then
            local note = {
                text = note_text,
                tag = note_tag,
                number = 0,
                rare = (note_tag and string.upper(trim(note_tag)) == "RARE") or false,
                id = build_note_id(note_text, note_tag),
            }
            if not seen[note.id] then
                seen[note.id] = true
                table.insert(notes, note)
            end
        end
    end

    return notes
end

local function load_note_records()
    local notes = {}
    local duplicates = 0
    local malformed = 0
    local file_signature = nil
    local file = io.open(script_state.footnotes_file, "rb")

    if not file then
        script_state.last_error = "Footnotes file is missing or unreadable."
        script_state.last_reload = "Failed"
        return false
    end

    local text = file:read("*a")
    file:close()

    if not text or text == "" then
        script_state.last_error = "Footnotes file is empty."
        script_state.last_reload = "Failed"
        return false
    end

    file_signature = 0
    for i = 1, #text do
        file_signature = (file_signature * 33 + string.byte(text, i)) % 4294967296
    end

    local blocks = {}
    local current_block = {}
    local is_json = script_state.footnotes_file:lower():match("%.json$") ~= nil

    if is_json then
        local parsed_notes = parse_json_note_records(text)
        if #parsed_notes > 0 then
            for _, note in ipairs(parsed_notes) do
                table.insert(notes, note)
            end
        else
            malformed = malformed + 1
        end
    else
        for line in normalize_newlines(text):gmatch("([^\n]+)") do
            local trimmed = trim(line)
            if trimmed == "===" then
                local block_text = table.concat(current_block, "\n")
                if trim(block_text) ~= "" then
                    table.insert(blocks, block_text)
                end
                current_block = {}
            else
                table.insert(current_block, line)
            end
        end

        if #current_block > 0 then
            local block_text = table.concat(current_block, "\n")
            if trim(block_text) ~= "" then
                table.insert(blocks, block_text)
            end
        end

        local seen = {}
        for _, block in ipairs(blocks) do
            local note, error_message = parse_note_block(block)
            if note then
                if seen[note.id] then
                    duplicates = duplicates + 1
                else
                    seen[note.id] = true
                    table.insert(notes, note)
                end
            else
                malformed = malformed + 1
            end
        end
    end

    if #notes == 0 then
        script_state.last_error = "No usable notes were found."
        script_state.last_reload = "Failed"
        return false
    end

    assign_numbers(notes)
    return notes, duplicates, malformed, file_signature
end

function load_notes(is_reload)
    local previous_note_count = #script_state.notes
    local previous_current_id = script_state.current_note and script_state.current_note.id or nil
    local previous_order = script_state.normal_order

    local loaded_notes, duplicates, malformed, file_signature = load_note_records()
    if not loaded_notes then
        if previous_note_count > 0 then
            script_state.last_reload = is_reload and "Reload preserved existing notes" or "Loaded preserved notes"
            script_state.last_error = script_state.last_error or "Notes were preserved from the previous successful load."
            update_status_text()
            return false
        end

        script_state.notes = {}
        script_state.rare_notes = {}
        script_state.normal_order = {}
        script_state.normal_index = 1
        script_state.current_cycle = 0
        script_state.current_note = nil
        script_state.previous_note = nil
        update_status_text()
        return false
    end

    local new_notes = loaded_notes
    local new_rare_notes = {}
    for _, note in ipairs(new_notes) do
        if note.rare then
            table.insert(new_rare_notes, note)
        end
    end

    script_state.notes = new_notes
    script_state.rare_notes = new_rare_notes
    script_state.last_reload = os.date("%Y-%m-%d %H:%M:%S")
    script_state.last_error = ""
    script_state.file_signature = file_signature

    if previous_current_id then
        for _, note in ipairs(new_notes) do
            if note.id == previous_current_id then
                script_state.current_note = note
                break
            end
        end
    end

    local rebuilt_order = {}
    if previous_order and #previous_order > 0 then
        local lookup = {}
        for _, note in ipairs(new_notes) do
            lookup[note.id] = note
        end
        for _, note in ipairs(previous_order) do
            if lookup[note.id] then
                table.insert(rebuilt_order, lookup[note.id])
            end
        end
        for _, note in ipairs(new_notes) do
            local seen = false
            for _, existing in ipairs(rebuilt_order) do
                if existing.id == note.id then
                    seen = true
                    break
                end
            end
            if not seen then
                table.insert(rebuilt_order, note)
            end
        end
    end

    if #rebuilt_order == #new_notes then
        script_state.normal_order = rebuilt_order
        script_state.normal_index = math.min(script_state.normal_index, #script_state.normal_order)
    else
        script_state.normal_order = shuffle_list(new_notes, script_state.previous_note and script_state.previous_note.id or nil)
        script_state.normal_index = 1
        script_state.current_cycle = 0
    end

    if #script_state.normal_order == 0 then
        script_state.normal_order = shuffle_list(new_notes, nil)
    end

    if script_state.normal_index < 1 then
        script_state.normal_index = 1
    end

    if script_state.current_cycle == 0 then
        script_state.current_cycle = 1
    end

    update_status_text()
    return true, duplicates, malformed
end

function reload_if_changed()
    if not script_state.auto_reload or script_state.footnotes_file == "" then
        return false
    end

    local file = io.open(script_state.footnotes_file, "rb")
    if not file then
        return false
    end

    local content = file:read("*a")
    file:close()
    if not content then
        return false
    end

    local signature = 0
    for i = 1, #content do
        signature = (signature * 33 + string.byte(content, i)) % 4294967296
    end

    if script_state.file_signature ~= nil and signature == script_state.file_signature then
        return false
    end

    script_state.file_signature = signature
    load_notes(true)
    return true
end

function script_description()
    return [[Black Feather Footnotes

A rotating field journal and footnote system for OBS Studio.
Version 1.0.0
]]
end

function script_defaults(settings)
    obs.obs_data_set_default_string(settings, "source_name", "")
    obs.obs_data_set_default_string(settings, "footnotes_file", find_default_footnotes_path())
    obs.obs_data_set_default_string(settings, "cover_art_file", find_default_cover_art_path())
    obs.obs_data_set_default_int(settings, "interval", 30)
    obs.obs_data_set_default_int(settings, "min_interval", 15)
    obs.obs_data_set_default_int(settings, "max_interval", 45)
    obs.obs_data_set_default_int(settings, "max_chars_per_line", 48)
    obs.obs_data_set_default_bool(settings, "variable_timing", false)
    obs.obs_data_set_default_bool(settings, "enable_rare_notes", false)
    obs.obs_data_set_default_int(settings, "rare_note_chance", 15)
    obs.obs_data_set_default_bool(settings, "auto_reload", true)
    obs.obs_data_set_default_string(settings, "status_display", "Waiting for notes.")
end

function script_properties()
    local props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "source_name", "Text Source", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_path(props, "footnotes_file", "Footnotes File", obs.OBS_PATH_FILE, "*.txt;*.json", nil)
    obs.obs_properties_add_path(props, "cover_art_file", "Cover Art Image", obs.OBS_PATH_FILE, "*.png;*.jpg;*.jpeg;*.webp;*.bmp", nil)
    obs.obs_properties_add_int(props, "interval", "Seconds Between Notes", 5, 300, 1)
    obs.obs_properties_add_int(props, "min_interval", "Minimum Seconds", 1, 300, 1)
    obs.obs_properties_add_int(props, "max_interval", "Maximum Seconds", 1, 300, 1)
    obs.obs_properties_add_int(props, "max_chars_per_line", "Maximum Characters Per Line", 20, 120, 1)
    obs.obs_properties_add_bool(props, "variable_timing", "Enable Variable Timing")
    obs.obs_properties_add_bool(props, "enable_rare_notes", "Enable Rare Notes")
    obs.obs_properties_add_int(props, "rare_note_chance", "Rare Note Chance (%)", 0, 100, 1)
    obs.obs_properties_add_bool(props, "auto_reload", "Auto Reload File")
    obs.obs_properties_add_text(props, "status_display", "Status", obs.OBS_TEXT_MULTILINE)

    obs.obs_properties_add_button(props, "reload_notes", "Reload Notes", function()
        if script_state.footnotes_file ~= "" then
            load_notes(true)
            next_note()
        end
    end)

    obs.obs_properties_add_button(props, "shuffle_now", "Shuffle Now", function()
        if #script_state.notes > 0 then
            start_new_cycle()
            update_status_text()
        end
    end)

    obs.obs_properties_add_button(props, "next_note", "Next Note", function()
        next_note()
    end)

    return props
end

function script_update(settings)
    script_state.settings = settings

    script_state.source_name = obs.obs_data_get_string(settings, "source_name")
    script_state.footnotes_file = resolve_footnotes_path(obs.obs_data_get_string(settings, "footnotes_file"))
    script_state.cover_art_file = resolve_cover_art_path(obs.obs_data_get_string(settings, "cover_art_file"))
    script_state.interval = math.max(1, obs.obs_data_get_int(settings, "interval"))
    script_state.min_interval = math.max(1, obs.obs_data_get_int(settings, "min_interval"))
    script_state.max_interval = math.max(script_state.min_interval, obs.obs_data_get_int(settings, "max_interval"))
    script_state.max_chars_per_line = math.max(20, obs.obs_data_get_int(settings, "max_chars_per_line"))
    script_state.variable_timing = obs.obs_data_get_bool(settings, "variable_timing")
    script_state.enable_rare_notes = obs.obs_data_get_bool(settings, "enable_rare_notes")
    script_state.rare_note_chance = math.max(0, math.min(100, obs.obs_data_get_int(settings, "rare_note_chance")))
    script_state.auto_reload = obs.obs_data_get_bool(settings, "auto_reload")

    if script_state.footnotes_file ~= "" then
        local loaded = load_notes(false)
        if loaded then
            script_state.timer_active = true
            obs.timer_remove(next_note)
            next_note()
        else
            script_state.timer_active = true
            obs.timer_remove(next_note)
            schedule_next()
        end
    else
        script_state.notes = {}
        script_state.normal_order = {}
        script_state.normal_index = 1
        script_state.current_cycle = 0
        script_state.last_error = "No footnotes file selected."
        update_status_text()
    end
end

function script_unload()
    obs.timer_remove(next_note)
end