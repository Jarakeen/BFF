"""UESP formula conversions.

This package holds readable, typed Python translations of the raw formulas
documented in ``services/minmax/equations.py``. Each module in this package
should correspond to a related group of UESP formulas (e.g. ``core_stats``
for character resource/damage/mitigation formulas).

These functions are intentionally NOT wired into ``Build`` or
``EffectResolver`` yet. They are pure math translations of UESP's published
equations and take already-resolved numeric inputs (the caller is
responsible for figuring out what ``Item.X``, ``Set.X``, ``Skill.X``, etc.
resolve to for a given build).

Do not edit ``services/minmax/equations.py`` -- it is the raw UESP formula
reference and must remain intact for future conversion batches to diff
against.
"""
