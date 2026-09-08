from __future__ import annotations

"""Add known Major/Minor effect IDs to Performance Dashboard timeline matching.

ESO Logs aura summaries are useful but occasionally omit or rename an effect that
still exists in the raw event stream.  The timeline service therefore keeps its
report-derived IDs and adds the reviewed Major/Minor game IDs as a fallback.
Nothing is considered active unless a matching event is actually observed.
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services import performance_effect_timeline as timeline_module
    from services.performance_effect_id_catalog import id_to_name

    original_effect_ids = timeline_module._effect_ids
    known_ids = {
        **id_to_name(kind="buff"),
        **id_to_name(kind="debuff"),
    }

    def effect_ids_with_known_fallback(auras):
        # Report-derived names remain authoritative where present.  Known IDs
        # only fill gaps so raw apply/refresh/remove events can still be matched
        # when the aggregate aura table did not surface the effect.
        merged = dict(known_ids)
        merged.update(original_effect_ids(auras))
        return merged

    timeline_module._effect_ids = effect_ids_with_known_fallback
    _INSTALLED = True
