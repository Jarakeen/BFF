# Black Feather Foundry Field Office

A lightweight desktop editor for the expedition JSON contract and stream events used by the OBS overlay.

## Safe OBS scene switching

BRB and End of Stream now switch scenes through OBS WebSocket, not the OBS Lua polling timer. In OBS, enable **Tools → WebSocket Server Settings**. In FoundryDock's **Settings** tab, enter the host, port, and password from OBS, then save. Scene names must match OBS exactly.

The bundled Lua script deliberately ignores `SceneName` requests from its timer. Replace the previously loaded copy of `OBS_Foundry_v1.4.lua` with the updated file in this package before using the buttons.
