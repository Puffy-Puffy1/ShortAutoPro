# ShortAutoPro — Termux-first generative video POC

**The Android phone running Termux is the brain and primary machine.** The production controller, project state, prompts, scene plan, model registry, queue, logs, file management, FFmpeg assembly, FFprobe validation and exports must run on the phone. No external orchestrator is required. Remote GPU execution is disabled by default and is not part of this zero-budget POC.

## What this POC adds

- A Termux/Android ARM64 preflight: RAM, free storage, required binaries and optional local inference binaries.
- A safe local-process adapter: invokes an explicitly reviewed native executable without a shell, enforces a timeout, refuses output overwrite, and requires FFprobe validation.
- One project/clip contract shared by 9:16 Shorts and 16:9 long-form output.
- Automated tests use fake local executables; no paid API, GPU rental, remote worker or external model download is used.

## Candidate local video engine

The upstream stable-diffusion.cpp project lists Android via Termux, Vulkan support, and video families including Wan2.1/2.2 and LTX-2.3/2.5. This confirms a plausible Termux path, not that every video model runs on every phone. Model weights, RAM, GPU driver, Vulkan support, thermals and battery require a device-specific smoke test.

Reference: https://github.com/leejet/stable-diffusion.cpp

The code deliberately does not hardcode CLI flags for a video model: those flags differ by model and upstream revision. A reviewed command template must be supplied after testing the selected binary's help output and model guide. The adapter does not fetch models or run arbitrary shell strings.

## Install base dependencies in Termux

Run this manually inside the Termux app. ShortAutoPro does not install packages automatically:

    pkg update
    pkg install python ffmpeg git clang cmake ninja pkg-config

Grant shared-storage access only when needed:

    termux-setup-storage

Keep models, cache and active generation files in Termux private HOME/.shortautopro/. Copy final MP4s to shared Movies/ShortAutoPro/ only after validation. Do not execute downloaded native binaries from shared storage; install reviewed executables under PREFIX/bin/.

Run the POC checks:

    python -m unittest discover -s tests_generative_video -v
    python -m generative_video_poc.termux_runtime

## Local execution constraints

- Termux controller and media assembly are always local.
- Model generation is local only when the device has a compatible executable/backend and enough available memory.
- Vulkan/NPU availability is reported, never assumed. A shell process cannot automatically use a handset's NPU just because the chip has one; the runtime must explicitly support it.
- Long-form projects are a queue of short generated clips, assembled locally by FFmpeg. Store each clip on disk and checkpoint after each completed scene; do not keep the full video in RAM.
- If the model does not fit, stop with a clear hardware diagnostic. No silent cloud fallback, paid service, laptop or PC dependency.

## Next gate

1. Run the Termux preflight on the target phone and inspect chipset, ABI, RAM, free storage and binaries.
2. Build or install a pinned stable-diffusion.cpp Android/Termux executable only after checking its exact release/build instructions.
3. Verify the model-specific command with a tiny clip, then record timing, peak memory if observable, resolution and FFprobe metadata.
4. Only after a real local MP4 passes, wire the single local backend into the existing ShortAutoPro orchestration. Do not create another pipeline or modify the production entrypoints as part of this POC.
