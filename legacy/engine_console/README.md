# Legacy Console Engine

This directory preserves the retired FastAPI/prototype operations-console path that previously lived under `engine/main.py` and `engine/operations.py`.

It is not a canonical ESO mechanics authority and normal runtime code must not import from it. The preserved implementation contains standalone capability/armor calculations that predate the current shared mechanics architecture.

The files remain only for forensic comparison and historical reference. Any supported replacement must use the active `engine/`, `services/`, and canonical mechanics/runtime contracts instead of reviving this path.
