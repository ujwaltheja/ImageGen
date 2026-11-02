"""Prompt and size rules for the kids stills worker. No torch, so this can be checked on a laptop."""
from __future__ import annotations

# Kids Video Studio asks for these (kvs/video_format.py image_gen_size).
PRESETS = {
    "landscape": (1216, 832),
    "short": (832, 1216),
    "draft": (832, 480),
}

# Klein 4B is step-distilled. More than 4 steps does not buy quality and only burns GPU time.
MAX_STEPS = 4
MIN_SIDE = 480
MAX_SIDE = 1280

LOCK = (
    "Use the reference only to copy identity. Draw a new scene, not the plain backdrop of the sheet. "
    "Milo is the boy, Ollie is the owl with round glasses, Rosie is the girl with pink bows. "
    "Keep their faces, hair, glasses and outfits the same as the reference. "
    "3D preschool cartoon, soft rounded shapes, warm sunlight. "
    "Children safe and happy, fully clothed, two arms, two hands, five fingers each. "
    "No text, no letters, no logos. Leave the top-right corner empty sky."
)


def snap(n: int, default: int) -> int:
    n = int(n if n else default)
    n = max(MIN_SIDE, min(MAX_SIDE, n))
    return n - (n % 16)


def resolve_size(width, height, preset: str | None) -> tuple[int, int]:
    """Explicit width or height wins. Otherwise the preset. Default is the landscape still."""
    preset = (preset or "").strip().lower()
    dw, dh = PRESETS.get(preset, PRESETS["landscape"])
    return snap(width, dw), snap(height, dh)


def clamp_steps(steps) -> int:
    if steps is None or steps == "":
        return MAX_STEPS
    return max(1, min(MAX_STEPS, int(steps)))


def build_prompt(scene: str) -> str:
    """Scene first, short identity lock after. The cast sheet carries the faces, so the text stays under 512 tokens."""
    scene = " ".join((scene or "").split())
    if not scene:
        raise ValueError("prompt is required")
    if len(scene) > 900:
        scene = scene[:900].rsplit(" ", 1)[0]
    return f"{scene} {LOCK}"
