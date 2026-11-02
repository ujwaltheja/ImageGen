"""RunPod serverless stills for Tiny Tales.

Model: FLUX.2 [klein] 4B (Apache-2.0). Four steps, one cast sheet.
Warm on a 4090 this is about a second. The 9B Klein weights are non-commercial, so they are not used.
"""
from __future__ import annotations

import base64
import io
import os
import random
import time
from pathlib import Path

import runpod
import torch
from PIL import Image

from prompt_build import LOCK, build_prompt, clamp_steps, resolve_size

MODEL_ID = os.environ.get("MODEL_ID", "black-forest-labs/FLUX.2-klein-4B")
CAST_DIR = Path(os.environ.get("CAST_DIR", str(Path(__file__).resolve().parent / "cast")))
JPEG_QUALITY = 88

pipe = None
refs_fast: list[Image.Image] = []
refs_tight: list[Image.Image] = []


def _open(name: str) -> Image.Image:
    path = CAST_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"missing cast reference {path}")
    return Image.open(path).convert("RGB")


def load_refs() -> None:
    global refs_fast, refs_tight
    sheet = _open("cast_sheet.jpg")
    refs_fast = [sheet]
    portraits = []
    for name in ("milo.jpg", "ollie.jpg", "rosie.jpg"):
        path = CAST_DIR / name
        if path.is_file():
            portraits.append(Image.open(path).convert("RGB"))
    # One sheet is the fast path. Tight adds the three crops (Klein allows 4 references).
    refs_tight = [sheet, *portraits] if portraits else [sheet]


def load_pipeline() -> None:
    global pipe
    if pipe is not None:
        return
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    from diffusers import Flux2KleinPipeline

    pipe = Flux2KleinPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)
    load_refs()
    if os.environ.get("WARMUP", "1") == "1":
        _generate(
            "Milo, Ollie and Rosie stand on green grass under a blue sky",
            1216,
            832,
            seed=0,
            steps=4,
            lock="fast",
        )
        torch.cuda.synchronize()


def _generate(scene: str, width: int, height: int, seed: int, steps: int, lock: str) -> Image.Image:
    prompt = build_prompt(scene)
    refs = refs_tight if lock == "tight" else refs_fast
    generator = torch.Generator(device="cuda").manual_seed(seed)
    with torch.inference_mode():
        out = pipe(
            prompt=prompt,
            image=refs,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=1.0,
            generator=generator,
        ).images[0]
    return out


def _jpeg_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode()


def process_data(input_data: dict) -> dict:
    """One still. Runpod stores this dict as the job output."""
    if input_data.get("health"):
        return {"ok": True, "model": "FLUX.2-klein-4B", "steps": 4, "lock_line": LOCK[:80]}
    scene = str(input_data.get("prompt") or "").strip()
    width, height = resolve_size(input_data.get("width"), input_data.get("height"), input_data.get("preset"))
    steps = clamp_steps(input_data.get("steps"))
    seed = int(input_data.get("seed", -1))
    if seed < 0:
        seed = random.randint(0, 2**31 - 1)
    lock = "tight" if str(input_data.get("lock", "fast")).lower() == "tight" else "fast"
    t0 = time.perf_counter()
    image = _generate(scene, width, height, seed, steps, lock)
    torch.cuda.synchronize()
    return {
        "image_b64": _jpeg_b64(image),
        "format": "jpg",
        "width": width,
        "height": height,
        "seed": seed,
        "steps": steps,
        "lock": lock,
        "gen_s": round(time.perf_counter() - t0, 3),
        "model": "FLUX.2-klein-4B",
    }


def handler(event):
    """Queue-based worker. Runpod calls this once per job.

    https://docs.runpod.io/serverless/overview#handler-functions
    """
    input_data = event["input"]
    return process_data(input_data)


# Load Klein before the worker accepts jobs. This time is the cold start.
load_pipeline()
runpod.serverless.start({"handler": handler})
