# Generative Video POC — isolated, zero-budget

This experiment is isolated on the POC branch. It does not replace or modify the production entrypoints, is not enabled in production, and does not create a second orchestration pipeline.

## Scope

- One project/clip contract describes portrait Shorts and landscape long-form.
- Long videos are planned as bounded generated clips rather than one giant model output.
- A ComfyUI API worker can be submitted to, polled with a deadline, and its video outputs downloaded atomically.
- Missing output, malformed responses and provider failures fail closed.

The ComfyUI client is only a transport adapter. It does not select a checkpoint, construct model nodes, validate model licenses, or prove that a GPU generated media. A model-specific workflow must be selected and reviewed separately.

## Zero-budget model and GPU candidate

First candidate for the real smoke test: Wan2.2 TI2V-5B. Its official model card declares Apache-2.0 and describes text/image-to-video at up to 720p/24fps. The official Wan inference script documents a 24GB VRAM requirement, while the ComfyUI workflow documentation says its native offloading path can fit 8GB VRAM; these are different execution paths, so we will test the ComfyUI route rather than assume the official script fits a small GPU.

Kaggle Notebooks currently documents free NVIDIA P100 GPU access, a weekly GPU quota (commonly 30 hours), and per-session limits; free capacity can be queued and is not guaranteed. This is a no-cost compute option, not a paid rental. Google Colab also offers free GPU access, but explicitly says availability and limits are dynamic and not guaranteed. If neither grants a GPU session, the real generation test must wait — no paid fallback will be started.

## Free automated validation

Run from repository root:

    python -m unittest discover -s tests_generative_video -v
    python -m compileall -q generative_video_poc tests_generative_video

Tests use a local fake HTTP server and a byte fixture. The fixture is not a real MP4 and is not evidence of AI video generation. No paid API, GPU rental, secret, or external network is used.

## Shared project contract

- Shorts: kind=shorts, aspect_ratio=9:16, target up to 180 seconds.
- Long-form: kind=longform, aspect_ratio=16:9, target above 180 seconds.
- Both use the same clip planner; a 30-minute project at 10 seconds per clip plans 180 clips. Continuity, dialogue/audio and final editing still require model-specific workflows and integration tests.

## Next gate — not yet approved

1. Run one real 5-second 9:16 Wan2.2 TI2V-5B clip on a free Kaggle GPU session using the ComfyUI workflow.
2. Validate the actual MP4 with FFprobe, inspect visual quality, and record GPU type, runtime, resolution, frame count and exact model/workflow revisions.
3. Run a small 16:9 long-form assembly test using multiple clips; do not infer that a 30–40 minute render is feasible from one clip.
4. Only after evidence, propose one adapter integration into the existing canonical orchestrator.
