from __future__ import annotations

from dataclasses import dataclass

from models.build_model import ARMOR_SLOTS, GearSlot, PlayerBuild


@dataclass(frozen=True)
class CharacterCreationRequest:
    name: str
    eso_class: str
    race: str
    role: str
    gamertag: str = ""
    alliance: str = ""
    body_set: str = ""
    weapons_jewelry_set: str = ""
    vampire: bool = False
    werewolf: bool = False


class CharacterCreationService:
    """Create the first usable build for a newly entered ESO character.

    The quick-create path deliberately asks only for character identity plus two
    optional starter set assignments. Everything else remains editable later in
    the full Builds workspace.
    """

    DEFAULT_BUILD_NAME = "Default"

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    def create(self, request: CharacterCreationRequest) -> PlayerBuild:
        name = self._clean(request.name)
        eso_class = self._clean(request.eso_class)
        race = self._clean(request.race)
        role = self._clean(request.role)

        missing = [
            label
            for label, value in (
                ("Character name", name),
                ("Class", eso_class),
                ("Race", race),
                ("Primary role", role),
            )
            if not value
        ]
        if missing:
            raise ValueError("Required field(s) missing: " + ", ".join(missing))
        if request.vampire and request.werewolf:
            raise ValueError("A character cannot be both Vampire and Werewolf.")

        body_set = self._clean(request.body_set)
        weapons_jewelry_set = self._clean(request.weapons_jewelry_set)

        build = PlayerBuild(
            Name=name,
            Gamertag=self._clean(request.gamertag),
            BuildName=self.DEFAULT_BUILD_NAME,
            Race=race,
            EsoClass=eso_class,
            Role=role,
            Alliance=self._clean(request.alliance),
            Vampire=bool(request.vampire),
            Werewolf=bool(request.werewolf),
        )

        if body_set:
            for slot in ARMOR_SLOTS:
                build.Armor[slot]["Set"] = body_set

        if weapons_jewelry_set:
            build.FrontBarWeapon = GearSlot(Set=weapons_jewelry_set)
            build.BackBarWeapon = GearSlot(Set=weapons_jewelry_set)
            build.Necklace = GearSlot(Set=weapons_jewelry_set)
            build.Ring1 = GearSlot(Set=weapons_jewelry_set)
            build.Ring2 = GearSlot(Set=weapons_jewelry_set)

        return build
