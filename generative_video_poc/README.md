# Generative Video POC — isolated, zero-budget

This experiment is isolated on the POC branch. It does not replace or modify the production entrypoints, is not enabled in production, and does not create a second orchestration pipeline.

## Scope

- One project/clip contract describes portrait Shorts and landscape long-form.
- Long videos are planned as bounded clips rather than one giant model output.
- A ComfyUI API worker can be submitted to, polled with a deadline, and its video outputs downloaded atomically.
- Missing output, malformed responses and provider failures fail closed.

The ComfyUI client is only a transport adapter. It does not select a checkpoint, construct model nodes, validate model licenses, or prove that a GPU generated media. A model-specific workflow must be selected and reviewed separately.

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

1. Select an open model after checking code and weight licenses separately.
2. Confirm an actually free GPU/hosted runtime is available; this POC does not assume one exists or silently rent one.
3. Add one model-specific workflow and run one real 9:16 clip.
4. Run a small landscape long-form sample, validate clips and final audio/video with FFprobe, then measure time and cost.
5. Only after evidence, propose one adapter integration into the existing canonical orchestrator.
