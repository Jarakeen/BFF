from services.asylum_sanctorium_timer import (
    AsylumPerfectaTimer,
    MINI_ENRAGE_SECONDS,
    MINI_RESPAWN_SECONDS,
    MiniState,
    format_clock,
)


def test_mini_enrages_after_three_active_minutes():
    timer = AsylumPerfectaTimer()
    timer.llothis.mark_active()
    timer.start()

    timer.advance(MINI_ENRAGE_SECONDS)

    assert timer.llothis.state == MiniState.ENRAGED
    assert timer.llothis.enrage_remaining == 0
    assert timer.llothis.enrage_stack == 1


def test_mini_deactivation_reactivates_after_one_minute():
    timer = AsylumPerfectaTimer()
    timer.felms.mark_inactive()
    timer.start()

    timer.advance(MINI_RESPAWN_SECONDS - 1)
    assert timer.felms.state == MiniState.INACTIVE
    assert timer.felms.respawn_remaining == 1

    timer.advance(1)
    assert timer.felms.state == MiniState.ACTIVE
    assert timer.felms.activation_count == 1


def test_mini_callouts_cover_health_check_execute_and_respawn_warning():
    timer = AsylumPerfectaTimer()
    timer.llothis.mark_active()
    timer.start()

    timer.advance(91)
    assert "Health check" in timer.llothis.callout

    timer.advance(60)
    assert timer.llothis.callout == "Execute Llothis"

    timer.llothis.mark_inactive()
    timer.advance(45)
    assert timer.llothis.callout == "Llothis back soon"


def test_perfecta_status_fails_on_death_or_time():
    timer = AsylumPerfectaTimer()
    assert timer.perfecta_status == "READY"

    timer.start()
    timer.add_death()
    assert timer.perfecta_status == "FAILED · DEATH"

    timer.reset()
    timer.start()
    timer.advance(901)
    assert timer.perfecta_status == "FAILED · TIME"


def test_olms_next_jump_threshold_tracks_manual_health():
    timer = AsylumPerfectaTimer()
    assert timer.next_olms_jump == 90
    timer.olms_health_percent = 89
    assert timer.next_olms_jump == 75
    timer.olms_health_percent = 49
    assert timer.next_olms_jump == 25
    timer.olms_health_percent = 24
    assert timer.next_olms_jump is None


def test_clock_format_is_console_readable():
    assert format_clock(900) == "15:00"
    assert format_clock(47) == "00:47"
