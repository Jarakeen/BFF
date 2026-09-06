local ADDON_NAME = "BFFScribingExtractor"
local SAVED_VARS_NAME = "BFFScribingExtractorSavedVariables"
local UPDATE_NAME = "BFFScribingExtractorScan"
local UPDATE_INTERVAL_MS = 40

local BFFScribingExtractor = {}
BFFScribingExtractor.name = ADDON_NAME
BFFScribingExtractor.version = 1
BFFScribingExtractor.saved = nil
BFFScribingExtractor.queue = {}
BFFScribingExtractor.index = 0
BFFScribingExtractor.running = false

local function SafeText(value)
    local text = tostring(value or "")
    text = text:gsub("[\r\n\t]", " ")
    text = text:gsub("|", "¦")
    return text
end

local function JoinFields(...)
    local parts = {}
    for i = 1, select("#", ...) do
        parts[i] = SafeText(select(i, ...))
    end
    return table.concat(parts, "|")
end

local function GetGameVersionSafe()
    if GetESOVersionString then
        local ok, value = pcall(GetESOVersionString)
        if ok then
            return value or ""
        end
    end
    return ""
end

local function BuildQueue()
    local queue = {}
    local numCraftedAbilities = GetNumCraftedAbilities()
    for abilityIndex = 1, numCraftedAbilities do
        local craftedAbilityId = GetCraftedAbilityIdAtIndex(abilityIndex)
        if craftedAbilityId and craftedAbilityId > 0 then
            local numFocus = GetNumScriptsInSlotForCraftedAbility(craftedAbilityId, SCRIBING_SLOT_PRIMARY)
            for focusIndex = 1, numFocus do
                local focusScriptId = GetScriptIdAtSlotIndexForCraftedAbility(
                    craftedAbilityId,
                    SCRIBING_SLOT_PRIMARY,
                    focusIndex
                )
                if focusScriptId and focusScriptId > 0 then
                    table.insert(queue, {
                        craftedAbilityId = craftedAbilityId,
                        focusScriptId = focusScriptId,
                    })
                end
            end
        end
    end
    return queue
end

local function FindLegalSupportingScripts(craftedAbilityId, focusScriptId)
    local numSignature = GetNumScriptsInSlotForCraftedAbility(craftedAbilityId, SCRIBING_SLOT_SECONDARY)
    local numAffix = GetNumScriptsInSlotForCraftedAbility(craftedAbilityId, SCRIBING_SLOT_TERTIARY)

    for signatureIndex = 1, numSignature do
        local signatureScriptId = GetScriptIdAtSlotIndexForCraftedAbility(
            craftedAbilityId,
            SCRIBING_SLOT_SECONDARY,
            signatureIndex
        )
        for affixIndex = 1, numAffix do
            local affixScriptId = GetScriptIdAtSlotIndexForCraftedAbility(
                craftedAbilityId,
                SCRIBING_SLOT_TERTIARY,
                affixIndex
            )
            if IsScribableScriptCombinationForCraftedAbility(
                craftedAbilityId,
                focusScriptId,
                signatureScriptId,
                affixScriptId
            ) then
                return signatureScriptId, affixScriptId
            end
        end
    end

    return 0, 0
end

local function CaptureResultRow(craftedAbilityId, focusScriptId)
    local signatureScriptId, affixScriptId = FindLegalSupportingScripts(craftedAbilityId, focusScriptId)
    if signatureScriptId == 0 or affixScriptId == 0 then
        return nil
    end

    SetCraftedAbilityScriptSelectionOverride(
        craftedAbilityId,
        focusScriptId,
        signatureScriptId,
        affixScriptId
    )

    local craftedAbilityName = GetCraftedAbilityDisplayName(craftedAbilityId) or ""
    local focusName = GetCraftedAbilityScriptDisplayName(focusScriptId) or ""
    local signatureName = GetCraftedAbilityScriptDisplayName(signatureScriptId) or ""
    local affixName = GetCraftedAbilityScriptDisplayName(affixScriptId) or ""

    local representativeAbilityId = GetCraftedAbilityRepresentativeAbilityId(craftedAbilityId) or 0
    local representativeName = ""
    if representativeAbilityId > 0 then
        representativeName = GetAbilityName(representativeAbilityId) or ""
    end

    local abilityId = GetAbilityIdForCraftedAbilityId(craftedAbilityId) or 0
    local abilityName = ""
    if abilityId > 0 then
        abilityName = GetAbilityName(abilityId) or ""
    end

    local craftedDescription = GetCraftedAbilityDescription(craftedAbilityId) or ""

    return JoinFields(
        craftedAbilityId,
        craftedAbilityName,
        focusScriptId,
        focusName,
        signatureScriptId,
        signatureName,
        affixScriptId,
        affixName,
        representativeAbilityId,
        representativeName,
        abilityId,
        abilityName,
        craftedDescription
    )
end

function BFFScribingExtractor:Finish()
    EVENT_MANAGER:UnregisterForUpdate(UPDATE_NAME)
    self.running = false

    for abilityIndex = 1, GetNumCraftedAbilities() do
        local craftedAbilityId = GetCraftedAbilityIdAtIndex(abilityIndex)
        if craftedAbilityId and craftedAbilityId > 0 then
            SetCraftedAbilityScriptSelectionOverride(craftedAbilityId, 0, 0, 0)
        end
    end

    self.saved.completed = true
    self.saved.completedAt = GetTimeStamp()
    self.saved.rowCount = #self.saved.exportRows
    d(string.format(
        "BFF Scribing Extractor complete: %d Grimoire + Focus rows captured. Reload UI or log out to flush SavedVariables.",
        self.saved.rowCount
    ))
end

function BFFScribingExtractor:ProcessNext()
    if not self.running then
        return
    end

    self.index = self.index + 1
    local work = self.queue[self.index]
    if not work then
        self:Finish()
        return
    end

    local row = CaptureResultRow(work.craftedAbilityId, work.focusScriptId)
    if row then
        table.insert(self.saved.exportRows, row)
    end

    self.saved.processed = self.index
    self.saved.total = #self.queue

    if self.index % 10 == 0 or self.index == #self.queue then
        d(string.format(
            "BFF Scribing Extractor: %d/%d Focus rows scanned",
            self.index,
            #self.queue
        ))
    end
end

function BFFScribingExtractor:Start()
    if self.running then
        d("BFF Scribing Extractor is already running.")
        return
    end

    self.queue = BuildQueue()
    self.index = 0
    self.running = true

    self.saved.exportRows = {}
    self.saved.completed = false
    self.saved.completedAt = 0
    self.saved.startedAt = GetTimeStamp()
    self.saved.processed = 0
    self.saved.total = #self.queue
    self.saved.rowCount = 0
    self.saved.apiVersion = GetAPIVersion and GetAPIVersion() or 0
    self.saved.gameVersion = GetGameVersionSafe()
    self.saved.formatVersion = 1

    d(string.format(
        "BFF Scribing Extractor started: %d Grimoire + Focus rows queued.",
        #self.queue
    ))

    EVENT_MANAGER:RegisterForUpdate(UPDATE_NAME, UPDATE_INTERVAL_MS, function()
        self:ProcessNext()
    end)
end

function BFFScribingExtractor:Status()
    if not self.saved then
        d("BFF Scribing Extractor SavedVariables are not initialized yet.")
        return
    end
    d(string.format(
        "BFF Scribing Extractor status: running=%s processed=%d/%d savedRows=%d complete=%s",
        tostring(self.running),
        tonumber(self.saved.processed or 0),
        tonumber(self.saved.total or 0),
        #(self.saved.exportRows or {}),
        tostring(self.saved.completed or false)
    ))
end

function BFFScribingExtractor:Clear()
    if self.running then
        EVENT_MANAGER:UnregisterForUpdate(UPDATE_NAME)
        self.running = false
    end
    self.saved.exportRows = {}
    self.saved.completed = false
    self.saved.completedAt = 0
    self.saved.startedAt = 0
    self.saved.processed = 0
    self.saved.total = 0
    self.saved.rowCount = 0
    d("BFF Scribing Extractor data cleared.")
end

local function OnAddOnLoaded(_, addonName)
    if addonName ~= ADDON_NAME then
        return
    end

    EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED)

    local defaults = {
        formatVersion = 1,
        apiVersion = 0,
        gameVersion = "",
        startedAt = 0,
        completedAt = 0,
        processed = 0,
        total = 0,
        rowCount = 0,
        completed = false,
        exportRows = {},
    }

    BFFScribingExtractor.saved = ZO_SavedVars:NewAccountWide(
        SAVED_VARS_NAME,
        1,
        nil,
        defaults
    )

    SLASH_COMMANDS["/bffscribing"] = function(argument)
        local command = string.lower(zo_strtrim(argument or ""))
        if command == "" or command == "scan" then
            BFFScribingExtractor:Start()
        elseif command == "status" then
            BFFScribingExtractor:Status()
        elseif command == "clear" then
            BFFScribingExtractor:Clear()
        else
            d("BFF Scribing Extractor commands: /bffscribing scan | status | clear")
        end
    end

    d("BFF Scribing Extractor loaded. Run /bffscribing scan to capture result-skill names.")
end

EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED, OnAddOnLoaded)
