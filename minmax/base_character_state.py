from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import ceil

from .character_progression import AttributeAllocation
from .stat_ids import StatId


BASE_MAX_HEALTH = 16_000.0
BASE_MAX_MAGICKA = 12_000.0
BASE_MAX_STAMINA = 12_000.0
BASE_HEALTH_RECOVERY = 309.0
BASE_MAGICKA_RECOVERY = 514.0
BASE_STAMINA_RECOVERY = 514.0

HEALTH_PER_ATTRIBUTE = 122.0
MAGICKA_PER_ATTRIBUTE = 111.0
STAMINA_PER_ATTRIBUTE = 111.0


@dataclass(frozen=True)
class CalculationStep:
    label: str
    operation: str
    value: float
    result: float


@dataclass(frozen=True)
class FlatContribution:
    """Named flat contribution retained for the Overview calculation trace."""

    label: str
    value: float


@dataclass
class CalculationTrace:
    stat: StatId
    steps: list[CalculationStep] = field(default_factory=list)
    raw_value: float = 0.0
    final_value: int = 0

    def add(self, label: str, operation: str, value: float, result: float) -> None:
        self.steps.append(CalculationStep(label, operation, value, result))


@dataclass(frozen=True)
class ResourceInputs:
    """Explicit inputs to one primary resource/recovery calculation.

    Aggregate fields remain for backwards compatibility while optional named
    item/set contributions let the UI explain exactly which gear produced a
    value. When named contributions are supplied their sum is represented by
    the matching aggregate field but is traced only once.
    """

    attribute_points: int = 0
    item_flat: float = 0.0
    set_flat: float = 0.0
    food_flat: float = 0.0
    mundus_flat: float = 0.0
    champion_flat: float = 0.0
    skill_flat: float = 0.0
    race_flat: float = 0.0
    other_flat: float = 0.0
    skill_percent: float = 0.0
    buff_percent: float = 0.0
    other_percent: float = 0.0
    item_contributions: tuple[FlatContribution, ...] = ()
    set_contributions: tuple[FlatContribution, ...] = ()


@dataclass(frozen=True)
class BaseCharacterState:
    max_health: int
    max_magicka: int
    max_stamina: int
    health_recovery: int
    magicka_recovery: int
    stamina_recovery: int
    traces: dict[StatId, CalculationTrace]


class BaseCharacterCalculator:
    """Calculate the stable primary resource layer with an auditable trace."""

    @staticmethod
    def eso_round(value: float) -> int:
        return int(ceil(value))

    @staticmethod
    def _calculate(
        *,
        stat: StatId,
        base: float,
        attribute_points: int,
        attribute_value: float,
        inputs: ResourceInputs,
    ) -> CalculationTrace:
        trace = CalculationTrace(stat=stat)
        current = base
        trace.add("base", "set", base, current)

        attribute = attribute_points * attribute_value
        current += attribute
        trace.add("attribute points", "add", attribute, current)

        # Preserve exact gear provenance when available. The aggregate value is
        # still kept on ResourceInputs for existing callers/tests, but it is not
        # added a second time when named contributions describe that same total.
        if inputs.item_contributions:
            for contribution in inputs.item_contributions:
                current += contribution.value
                trace.add(contribution.label, "add", contribution.value, current)
        elif inputs.item_flat:
            current += inputs.item_flat
            trace.add("item flat", "add", inputs.item_flat, current)

        if inputs.set_contributions:
            for contribution in inputs.set_contributions:
                current += contribution.value
                trace.add(contribution.label, "add", contribution.value, current)
        elif inputs.set_flat:
            current += inputs.set_flat
            trace.add("set flat", "add", inputs.set_flat, current)

        for label, value in (
            ("food flat", inputs.food_flat),
            ("mundus flat", inputs.mundus_flat),
            ("Champion Point flat", inputs.champion_flat),
            ("skill flat", inputs.skill_flat),
            ("race", inputs.race_flat),
            ("other flat", inputs.other_flat),
        ):
            if value:
                current += value
                trace.add(label, "add", value, current)

        percent = inputs.skill_percent + inputs.buff_percent + inputs.other_percent
        if percent:
            current *= 1.0 + percent
            trace.add("percentage modifiers", "multiply", 1.0 + percent, current)

        trace.raw_value = current
        trace.final_value = BaseCharacterCalculator.eso_round(current)
        trace.add("ESO rounding", "ceil", trace.final_value, trace.final_value)
        return trace

    def max_health(self, inputs: ResourceInputs = ResourceInputs()) -> CalculationTrace:
        return self._calculate(stat=StatId.MAX_HEALTH, base=BASE_MAX_HEALTH, attribute_points=inputs.attribute_points, attribute_value=HEALTH_PER_ATTRIBUTE, inputs=inputs)

    def max_magicka(self, inputs: ResourceInputs = ResourceInputs()) -> CalculationTrace:
        return self._calculate(stat=StatId.MAX_MAGICKA, base=BASE_MAX_MAGICKA, attribute_points=inputs.attribute_points, attribute_value=MAGICKA_PER_ATTRIBUTE, inputs=inputs)

    def max_stamina(self, inputs: ResourceInputs = ResourceInputs()) -> CalculationTrace:
        return self._calculate(stat=StatId.MAX_STAMINA, base=BASE_MAX_STAMINA, attribute_points=inputs.attribute_points, attribute_value=STAMINA_PER_ATTRIBUTE, inputs=inputs)

    def health_recovery(self, inputs: ResourceInputs = ResourceInputs()) -> CalculationTrace:
        return self._calculate(stat=StatId.HEALTH_RECOVERY, base=BASE_HEALTH_RECOVERY, attribute_points=0, attribute_value=0.0, inputs=inputs)

    def magicka_recovery(self, inputs: ResourceInputs = ResourceInputs()) -> CalculationTrace:
        return self._calculate(stat=StatId.MAGICKA_RECOVERY, base=BASE_MAGICKA_RECOVERY, attribute_points=0, attribute_value=0.0, inputs=inputs)

    def stamina_recovery(self, inputs: ResourceInputs = ResourceInputs()) -> CalculationTrace:
        return self._calculate(stat=StatId.STAMINA_RECOVERY, base=BASE_STAMINA_RECOVERY, attribute_points=0, attribute_value=0.0, inputs=inputs)

    def calculate(
        self,
        *,
        attributes: AttributeAllocation | None = None,
        race_stats: dict[str, float] | None = None,
        health: ResourceInputs = ResourceInputs(),
        magicka: ResourceInputs = ResourceInputs(),
        stamina: ResourceInputs = ResourceInputs(),
        health_recovery: ResourceInputs = ResourceInputs(),
        magicka_recovery: ResourceInputs = ResourceInputs(),
        stamina_recovery: ResourceInputs = ResourceInputs(),
    ) -> BaseCharacterState:
        """Calculate all primary resources from one shared allocation."""
        if attributes is not None:
            health = replace(health, attribute_points=attributes.health)
            magicka = replace(magicka, attribute_points=attributes.magicka)
            stamina = replace(stamina, attribute_points=attributes.stamina)

        race_stats = race_stats or {}
        health = replace(health, race_flat=health.race_flat + float(race_stats.get("max_health", 0)))
        magicka = replace(magicka, race_flat=magicka.race_flat + float(race_stats.get("max_magicka", 0)))
        stamina = replace(stamina, race_flat=stamina.race_flat + float(race_stats.get("max_stamina", 0)))
        health_recovery = replace(health_recovery, race_flat=health_recovery.race_flat + float(race_stats.get("health_recovery", 0)))
        magicka_recovery = replace(magicka_recovery, race_flat=magicka_recovery.race_flat + float(race_stats.get("magicka_recovery", 0)))
        stamina_recovery = replace(stamina_recovery, race_flat=stamina_recovery.race_flat + float(race_stats.get("stamina_recovery", 0)))

        traces = {
            StatId.MAX_HEALTH: self.max_health(health),
            StatId.MAX_MAGICKA: self.max_magicka(magicka),
            StatId.MAX_STAMINA: self.max_stamina(stamina),
            StatId.HEALTH_RECOVERY: self.health_recovery(health_recovery),
            StatId.MAGICKA_RECOVERY: self.magicka_recovery(magicka_recovery),
            StatId.STAMINA_RECOVERY: self.stamina_recovery(stamina_recovery),
        }
        return BaseCharacterState(
            max_health=traces[StatId.MAX_HEALTH].final_value,
            max_magicka=traces[StatId.MAX_MAGICKA].final_value,
            max_stamina=traces[StatId.MAX_STAMINA].final_value,
            health_recovery=traces[StatId.HEALTH_RECOVERY].final_value,
            magicka_recovery=traces[StatId.MAGICKA_RECOVERY].final_value,
            stamina_recovery=traces[StatId.STAMINA_RECOVERY].final_value,
            traces=traces,
        )
