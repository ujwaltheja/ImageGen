[![Runpod](https://api.runpod.io/badge/ujwaltheja/ImageGen)](https://console.runpod.io/hub/listing/ujwaltheja/ImageGen)

# Kids stills — Runpod serverless

Scene pictures for Tiny Tales (Milo, Rosie, Ollie). One cast sheet is baked into the worker and attached on every job, the same way Kids Video Studio already describes the cast in `cast_string`.

## Model

**FLUX.2 [klein] 4B** (`black-forest-labs/FLUX.2-klein-4B`).

| | |
|---|---|
| Why this one | Fastest open model that can take a reference image and still draw a new scene. Four distilled steps. Apache-2.0, so a monetised kids channel can use it. |
| Not used | Klein 9B and 9B KV. Those are quicker on multi-reference edits, and they are under the FLUX non-commercial licence. |
| Speed | One reference (the sheet), 4 steps, guidance 1.0, no CPU offload. On a warm RTX 4090 a 1216×832 still is about a second of GPU time. |
| Faces | `lock=fast` (default) sends only `cast/cast_sheet.jpg`. `lock=tight` also sends the Milo, Ollie and Rosie crops. Tight is slower. Use it when a close-up drifts. |

The sheet in `cast/cast_sheet.jpg` is the three-character reference: Milo (yellow shirt, blue shorts, red sneakers), Ollie (glasses, cream belly), Rosie (pigtails, pink bows, pink polka-dot dress).

## Deploy

GPU: **RTX 4090** (24 GB). Same class as the Wan endpoint. Container disk **50 GB** (the image holds the weights). Workers **min 0, max 1**, idle timeout **5 s**, FlashBoot **on**. Set the CUDA floor to **12.8** so the worker does not land on an old host.

```bash
cd ~/AI/ImageGen
docker build -t yourname/tinytales-stills:klein4b .
docker push yourname/tinytales-stills:klein4b
```

In the RunPod console: Serverless → New endpoint → that image → GPU 4090 → the limits above. Copy the endpoint id.

```bash
export RUNPOD_API_KEY="..."          # same key as music / i2v, never commit it
export IMAGE_EP="the-endpoint-id"
python3 client.py "Milo holds a red apple. Rosie claps. Ollie watches from the grass." out.jpg
python3 client.py --preset short "Ollie holds up one shiny apple" short.jpg
python3 client.py --preset draft "wide garden, all three waving" draft.jpg
```

First job after idle is the cold start (container plus loading Klein into GPU memory, often one to two minutes). The next stills on that warm worker are the fast ones. `client.py` purges the queue after the download, same as `kids-video-studio/runpod/rp.sh`.

## Request

`POST https://api.runpod.ai/v2/$IMAGE_EP/run`

```json
{
  "input": {
    "prompt": "Milo holds a red apple. Rosie claps. Ollie watches.",
    "preset": "landscape",
    "lock": "fast",
    "steps": 4,
    "seed": -1
  },
  "policy": {"ttl": 600000}
}
```

| Field | Default | Meaning |
|---|---|---|
| `prompt` | required | The scene. The worker adds a short identity line. A long studio `full_prompt` is trimmed so the scene is not cut off by the 512-token cap. |
| `preset` | `landscape` | `landscape` 1216×832 (studio stills), `short` 832×1216, `draft` 832×480 (fastest, matches the Wan frame). |
| `width`, `height` | from the preset | Multiples of 16, clamped to 480–1280. If you set either, it overrides that side of the preset. |
| `lock` | `fast` | `fast` = cast sheet only. `tight` = sheet plus the three crops. |
| `steps` | 4 | Clamped to 1–4. |
| `seed` | random | `0` or higher repeats a take. |
| `health` | | `{"health": true}` returns without drawing. |

## Response

```json
{
  "image_b64": "...",
  "format": "jpg",
  "width": 1216,
  "height": 832,
  "seed": 7,
  "steps": 4,
  "lock": "fast",
  "gen_s": 0.9,
  "model": "FLUX.2-klein-4B"
}
```

`gen_s` is GPU time for that still, not the cold start. Save with `base64.b64decode` on `image_b64`.

## What you pay

Roughly, a warm 4090 at community rates (~$0.34/hr) and ~1 s of work is well under a tenth of a cent per still. A cold start of about a minute is about half a cent. Draft (832×480) is the cheap option when you are sketching a shot. Landscape is what the studio's picture step expects before Wan.

## Checks on a laptop

```bash
python3 test_prompt.py
```

That does not load the model. The model runs only inside the worker.
