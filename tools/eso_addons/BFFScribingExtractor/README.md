# BFF Scribing Extractor

Small ESO addon used to observe the official client result name for every available Grimoire + Focus pair.

## Why this exists

The ESO client exposes crafted-ability and script APIs, including:

- `GetCraftedAbilityDisplayName`
- `GetCraftedAbilityScriptDisplayName`
- `IsScribableScriptCombinationForCraftedAbility`
- `SetCraftedAbilityScriptSelectionOverride`
- `GetCraftedAbilityRepresentativeAbilityId`
- `GetAbilityIdForCraftedAbilityId`
- `GetAbilityName`

The extractor chooses one legal Signature + Affix pair for each Grimoire + Focus pair, applies the official selection override, and records the resulting representative/base ability names. It does not scribe anything, spend ink, or change the character's active scribed configuration.

## Install

Copy the whole `BFFScribingExtractor` folder into the ESO AddOns directory:

`Documents\Elder Scrolls Online\live\AddOns\BFFScribingExtractor\`

Enable it at character select. If ESO marks it out of date after an API bump, enable "Allow out of date add-ons" long enough to run the extractor, then update the manifest API version in the repo.

## Run

In chat:

`/bffscribing scan`

The scan is deliberately throttled. Watch chat for completion, then run:

`/bffscribing status`

After completion, `/reloadui` or log out so ESO flushes SavedVariables to disk.

Useful commands:

- `/bffscribing scan`
- `/bffscribing status`
- `/bffscribing clear`

## SavedVariables

ESO writes:

`Documents\Elder Scrolls Online\live\SavedVariables\BFFScribingExtractorSavedVariables.lua`

Import it into FoundryDock with:

```powershell
python tools\import_scribing_result_names.py `
  "$HOME\Documents\Elder Scrolls Online\live\SavedVariables\BFFScribingExtractorSavedVariables.lua"
```

The importer stores raw client observations in `data/eso.db` and only promotes them to canonical result names if the known verification probe resolves:

`Soul Burst + Damage Shield -> Warding Burst`

If that probe does not match, the raw data is kept for diagnosis but the simulator will not trust the extracted names.

## App behavior

After a verified import, the Scribing Simulator reads `scribing_result_skill` and displays the observed transformed result name for a selected Grimoire + Focus pair. Static explicit mappings remain as a fallback.
