"""Laptop checks for size and prompt rules. No GPU."""
from prompt_build import build_prompt, clamp_steps, resolve_size


def test_defaults_match_studio():
    assert resolve_size(None, None, None) == (1216, 832)
    assert resolve_size(None, None, "short") == (832, 1216)
    assert resolve_size(None, None, "draft") == (832, 480)


def test_explicit_size_wins_and_snaps():
    assert resolve_size(1000, 500, "draft") == (992, 496)
    assert resolve_size(4000, 10, None) == (1280, 480)


def test_steps_stay_on_the_fast_schedule():
    assert clamp_steps(None) == 4
    assert clamp_steps(28) == 4
    assert clamp_steps(2) == 2


def test_prompt_keeps_the_scene_and_the_lock():
    text = build_prompt("Milo holds a red apple. Rosie claps.")
    assert text.startswith("Milo holds a red apple.")
    assert "Ollie is the owl" in text
    assert "No text" in text
    long = build_prompt("apple " * 800)
    assert len(long) < 1600


if __name__ == "__main__":
    test_defaults_match_studio()
    test_explicit_size_wins_and_snaps()
    test_steps_stay_on_the_fast_schedule()
    test_prompt_keeps_the_scene_and_the_lock()
    print("ok")
