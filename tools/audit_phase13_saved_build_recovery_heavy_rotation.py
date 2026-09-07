from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.resource_costs import ResourceType
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind
from services.build_service import BuildService
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _load_saved_build(path: Path, *, character: str, build_name: str):
    roster = BuildService(path).load()
    matches = [
        build
        for build in roster.Members
        if _character_name(build).casefold() == character.casefold()
        and str(getattr(build, "BuildName", "") or "").strip().casefold()
        == build_name.casefold()
    ]
    if not matches:
        raise ValueError(
            f"Saved build not found: character={character!r}, build={build_name!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Saved build identity is ambiguous: character={character!r}, build={build_name!r}"
        )
    return matches[0]


def build_verified_heavy_restore_resolver(
    *,
    amount: int,
    channel_seconds: float,
    bar: str | None = None,
):
    """Create an audit-only resolver from explicit caller-supplied restore evidence.

    The resolver does not claim the supplied amount is a canonical ESO value. It
    simply turns the caller's test/verified amount into the restoration event shape
    required by the Phase 4 sustain replay.
    """

    restore_amount = int(amount)
    channel = float(channel_seconds)
    target_bar = str(bar or "").strip().casefold() or None
    if restore_amount <= 0:
        raise ValueError("heavy restore amount must be positive")
    if channel <= 0:
        raise ValueError("heavy channel seconds must be positive")
    if target_bar not in {None, "front", "back"}:
        raise ValueError("heavy restore bar must be 'front', 'back', or omitted")

    def resolve(action: RotationAction) -> ResourceRestorationEvent | None:
        if action.kind is not RotationActionKind.HEAVY_ATTACK:
            return None
        action_bar = str(action.bar or "").strip().casefold() or None
        if target_bar is not None and action_bar != target_bar:
            return None
        return ResourceRestorationEvent(
            time_seconds=float(action.time_seconds) + channel,
            resource=ResourceType.MAGICKA,
            amount=restore_amount,
            source=(
                "Caller-supplied Phase 13 audit heavy restore "
                f"({restore_amount} magicka)"
            ),
        )

    return resolve


def _heavy_signature(plan) -> tuple[tuple[float, str | None, str | None], ...]:
    return tuple(
        (float(action.time_seconds), action.bar, action.name)
        for action in plan.actions
        if action.kind is RotationActionKind.HEAVY_ATTACK
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and stabilize a real saved healer rotation using an explicit "
            "caller-supplied Magicka restore amount for fully charged heavy attacks."
        )
    )
    parser.add_argument("--character", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--maximum-magicka", type=int, required=True)
    parser.add_argument("--trigger-fraction", type=float, required=True)
    parser.add_argument("--restore-amount", type=int, required=True)
    parser.add_argument("--restore-bar", choices=("front", "back"))
    parser.add_argument("--channel-seconds", type=float, default=1.8)
    parser.add_argument("--max-iterations", type=int, default=6)
    args = parser.parse_args()

    build = _load_saved_build(
        args.builds,
        character=args.character,
        build_name=args.build,
    )
    resolver = build_verified_heavy_restore_resolver(
        amount=args.restore_amount,
        channel_seconds=args.channel_seconds,
        bar=args.restore_bar,
    )

    result = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=float(args.duration),
            required_heavy_channel_seconds=float(args.channel_seconds),
            stabilize_recovery_heavies=True,
            recovery_stabilization_resource=ResourceType.MAGICKA,
            recovery_maximum_amount=int(args.maximum_magicka),
            recovery_trigger_fraction=float(args.trigger_fraction),
            recovery_restoration_resolver=resolver,
            recovery_stabilization_max_iterations=int(args.max_iterations),
        ),
    )
    stabilization = result.recovery_stabilization
    if stabilization is None:
        raise RuntimeError("recovery-heavy stabilization evidence was not returned")

    print("=" * 68)
    print(" PHASE 13 SAVED-BUILD RECOVERY HEAVY ROTATION AUDIT")
    print("=" * 68)
    print(f"Character:          {_character_name(build) or 'unnamed'}")
    print(f"Build:              {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Role:               {getattr(build, 'Role', '') or 'Unspecified'}")
    print(f"Duration:           {float(args.duration):g}s")
    print(f"Maximum Magicka:    {int(args.maximum_magicka)}")
    print(f"Recovery trigger:   {float(args.trigger_fraction):.1%}")
    print(f"Heavy restore:      {int(args.restore_amount)} Magicka (caller supplied)")
    print(f"Heavy channel:      {float(args.channel_seconds):g}s")
    print(f"Restore bar:        {args.restore_bar or 'any scheduled heavy'}")
    print("Boundary:           scheduling validation only; restore amount is not canonicalized here")
    print()

    print("STABILIZATION")
    print("-------------")
    for iteration in stabilization.iterations:
        print(f"Pass {iteration.iteration}: heavies={len(iteration.heavy_signature)}")
        if iteration.heavy_signature:
            for time_seconds, bar, name in iteration.heavy_signature:
                print(
                    f"  {time_seconds:6.1f}s | {(bar or 'unbarred'):5s} | "
                    f"{name or 'Heavy Attack'}"
                )
        else:
            print("  none")
        timeline = iteration.replay.final_projection.run.timeline
        print(
            f"  Magicka: start={timeline.starting_amount} "
            f"end={timeline.ending_amount} shortfall={timeline.total_shortfall}"
        )
    print()
    print(f"Converged:          {stabilization.converged}")
    print(f"Iterations:         {len(stabilization.iterations)}")
    print()

    final_timeline = stabilization.replay.final_projection.run.timeline
    final_heavies = _heavy_signature(stabilization.plan)
    print("FINAL HEAVY SCHEDULE")
    print("--------------------")
    if final_heavies:
        for time_seconds, bar, name in final_heavies:
            print(
                f"{time_seconds:6.1f}s | {(bar or 'unbarred'):5s} | "
                f"{name or 'Heavy Attack'}"
            )
    else:
        print("none")
    print()
    print("FINAL SUSTAIN")
    print("-------------")
    print(f"Starting Magicka:   {final_timeline.starting_amount}")
    print(f"Ending Magicka:     {final_timeline.ending_amount}")
    print(f"Total shortfall:    {final_timeline.total_shortfall}")
    print(f"Verified restores:  {len(stabilization.replay.restoration_events)}")

    unresolved = tuple(stabilization.replay.final_projection.unresolved)
    print()
    print("UNRESOLVED")
    print("----------")
    if unresolved:
        for item in unresolved:
            print(item)
    else:
        print("none")

    return 0 if stabilization.converged else 2


if __name__ == "__main__":
    raise SystemExit(main())
