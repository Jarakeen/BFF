from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from services.eso_icon_resolver import EsoIconResolver
from services.scribing_icons import texture_for_scribed_skill
from services.scribing_u51_service import U51ScribingService


def main() -> int:
    service = U51ScribingService(DEFAULT_DATABASE)
    resolver = EsoIconResolver()
    if not service.available:
        print('U51 scribing catalog is not available in data/eso.db.')
        return 2

    total = 0
    found = 0
    missing: list[tuple[str, str, str]] = []

    for grimoire in service.grimoire_names():
        for focus in service.compatible_focus(grimoire):
            total += 1
            texture = texture_for_scribed_skill(grimoire, focus)
            path = resolver.resolve(texture)
            if path is not None:
                found += 1
            else:
                missing.append((grimoire, focus, texture))

    print('========================================')
    print(' U51 SCRIBING ABILITY ICON AUDIT')
    print('========================================')
    print(f'Icon root:          {resolver.icon_root}')
    print(f'Grimoire+Focus:     {total}')
    print(f'Icons resolved:     {found}')
    print(f'Icons missing:      {len(missing)}')

    if missing:
        print()
        print('Missing mappings/assets:')
        for grimoire, focus, texture in missing:
            print(f'  {grimoire} + {focus}')
            print(f'    {texture or "NO TEXTURE MAPPING"}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
