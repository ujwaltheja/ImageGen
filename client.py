#!/usr/bin/env python3
"""One still from the RunPod kids image endpoint.

  export RUNPOD_API_KEY=...
  export IMAGE_EP=your-endpoint-id
  python client.py "Milo holds a red apple. Rosie claps. Ollie watches." out.jpg
  python client.py --preset short "Ollie holds up one shiny apple" out.jpg
  python client.py --lock tight "close-up of Rosie smiling" out.jpg
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request

API = "https://api.runpod.ai/v2"


def _req(method: str, url: str, key: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    p = argparse.ArgumentParser(description="Kids stills on RunPod (FLUX.2 Klein 4B)")
    p.add_argument("prompt")
    p.add_argument("out")
    p.add_argument("--preset", choices=("landscape", "short", "draft"), default="landscape")
    p.add_argument("--width", type=int, default=0)
    p.add_argument("--height", type=int, default=0)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--lock", choices=("fast", "tight"), default="fast")
    p.add_argument("--steps", type=int, default=4)
    args = p.parse_args()

    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    ep = os.environ.get("IMAGE_EP", "").strip()
    if not key or not ep:
        sys.exit("Set RUNPOD_API_KEY and IMAGE_EP")

    payload = {
        "input": {
            "prompt": args.prompt,
            "preset": args.preset,
            "seed": args.seed,
            "lock": args.lock,
            "steps": args.steps,
        },
        "policy": {"ttl": 600000},
    }
    if args.width:
        payload["input"]["width"] = args.width
    if args.height:
        payload["input"]["height"] = args.height

    job = _req("POST", f"{API}/{ep}/run", key, payload)
    jid = job["id"]
    print(f"job {jid}", file=sys.stderr)
    waited = 0
    while True:
        status = _req("GET", f"{API}/{ep}/status/{jid}", key)
        st = status.get("status")
        if st == "COMPLETED":
            break
        if st in ("FAILED", "CANCELLED", "TIMED_OUT"):
            sys.exit(str(status.get("error") or status)[:1200])
        time.sleep(2)
        waited += 2
        if waited > 900:
            sys.exit("timeout waiting for the worker")
    out = status["output"]
    if out.get("error"):
        sys.exit(out["error"])
    raw = base64.b64decode(out["image_b64"])
    with open(args.out, "wb") as f:
        f.write(raw)
    meta = {k: v for k, v in out.items() if k != "image_b64"}
    print(f"saved {args.out} {meta} delay_ms={status.get('delayTime')} exec_ms={status.get('executionTime')}")
    try:
        _req("POST", f"{API}/{ep}/purge-queue", key, {})
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
