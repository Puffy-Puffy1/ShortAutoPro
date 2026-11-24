# ShortAutoPro — Termux-first generative video POC

**The Android phone running Termux is the brain and primary machine.** Project creation, queue, persistent state, clip claims, lease recovery, checkpoints, prompts, storage, FFmpeg, FFprobe and export orchestration belong on the phone. Remote compute remains disabled by default.

## Local controller and queue

The POC uses Python's built-in SQLite; no extra database server or service is needed. Project schedules support up to 120 minutes per run, with bounded clip counts and prompt payloads.

Run from the repository root in Termux:

    python -m generative_video_poc.brain device
    python -m generative_video_poc.brain create meu-short --spec-file generative_video_poc/examples/shorts.json
    python -m generative_video_poc.brain create meu-documentario --spec-file generative_video_poc/examples/longform.json
    python -m generative_video_poc.brain list
    python -m generative_video_poc.brain show meu-short
    python -m generative_video_poc.brain claim --project-id meu-short
    # after configuring a compatible local video generator:
    python -m generative_video_poc.brain work --project-id meu-short --backend-config generative_video_poc/local_video_backend.json

The device report inspects Android manufacturer/model, platform properties from an allow-list, RAM, free internal storage, installed tools and optional Vulkan information. It does not collect serial numbers or account/network identifiers. Controller readiness is checked separately from availability of local text/video inference.

## Local AI brain and video generator are separate

The local text model acts as the director: outline, narration, scene prompts, continuity notes and production instructions. The video model generates the actual visual clips. Both are optional until installed and hardware-tested; no cloud service is assumed.

The official Termux package repository contains a llama-cpp package. Its current package build enables Vulkan and OpenCL backends and suggests optional backend packages. On the target device, check package availability first, then install manually:

    pkg update
    pkg search llama-cpp
    pkg install llama-cpp
    llama-cli --version

Do not download a GGUF model until the device report is available. Model size and quantization must match RAM, free storage, CPU/GPU and thermal constraints. The presence of llama-cli does not itself mean that model weights are present or that an accelerator is working.

Package recipe: https://github.com/termux/termux-packages/tree/master/packages/llama-cpp

## Local video engine candidate

The upstream stable-diffusion.cpp project lists Android through Termux and video model families including Wan2.1/2.2 and LTX. It is under active development, and its CLI options may change.

Important build caveat: the upstream Android build section documents an Android NDK path for arm64-v8a and OpenCL setup; it does not provide a one-command Termux package installation for every Android GPU. Its OpenCL instructions are specifically for Adreno GPUs. The general Vulkan instructions do not prove that a particular handset's Termux environment has a compatible Vulkan driver or build. This POC therefore detects tools but does not blindly compile, install or download models.

References:
- https://github.com/leejet/stable-diffusion.cpp
- https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/build.md

## Storage and recovery

- Database: $HOME/.shortautopro/state/queue.sqlite3.
- Project workspace: $HOME/.shortautopro/projects/<project_id>/.
- Every clip has PENDING, RUNNING, READY or FAILED status.
- The worker claims one clip with a unique lease token and sets the lease longer than the bounded model timeout; stale workers cannot commit results.
- Expired leases return to the queue up to the fixed per-project retry limit; stale workers cannot complete a clip.
- Each attempt gets its own suggested output filename. Completion requires an in-project file and FFprobe validation metadata.
- Project specs are immutable and create is idempotent. Each spec includes either a visual `prompt_template` or a `clip_prompts` list with exactly one prompt per scheduled clip; supported placeholders are `{clip_index}`, `{start_seconds}` and `{duration_seconds}`.
- The worker writes generated clips only into the project workspace and marks them READY after FFprobe, resolution and duration checks. A completed project receives an integrity-checked `generated_manifest.json` containing clip order, timing, prompts, checksums and FFprobe metadata. This manifest is a handoff contract, not a finished MP4.

## Configure a real local video model

Copy `local_video_backend.example.json` to `local_video_backend.json` and edit the executable path, model name and argument list to match the CLI of a model that is actually installed on the phone. The example is a template, not an installed generator: the backend deliberately does not guess model-specific flags. It invokes the executable without a shell and requires FFprobe-valid video output.

The project JSON must contain a meaningful `prompt_template`. Replace the bracketed subject in the sample Shorts/long-form specs before creating a project. Use `--drain` to process the entire project automatically in one session; without it, the command processes only one clip. The SQLite checkpoints make interrupted projects resumable:

    python -m generative_video_poc.brain work --project-id meu-documentario --backend-config generative_video_poc/local_video_backend.json --drain
    python -m generative_video_poc.brain show meu-documentario
    python -m generative_video_poc.brain verify-manifest ~/.shortautopro/projects/meu-documentario/generated_manifest.json

A READY clip is a generated asset checkpoint, not a finished exported video. The manifest is the interchange contract for the canonical media/long-form pipeline; final assembly remains a separate integration gate, and no parallel renderer is introduced here.

## Base packages

Install the media/controller dependencies manually:

    pkg install python ffmpeg git clang cmake ninja pkg-config
    termux-setup-storage

Models, database and intermediate files stay in Termux private storage. Copy finished MP4s to shared storage only after final validation. Never execute downloaded binaries from shared storage.

## Automated checks

    python -m compileall -q generative_video_poc tests_generative_video
    python -m unittest discover -s tests_generative_video -v

Tests use fake local processes and fixture data; they validate contracts, concurrency and recovery, not actual AI inference. No paid API, GPU rental, remote worker or cloud orchestrator is used.

## Next gate

1. Run the Termux device report.
2. Test the local text runtime with a small model only after checking device RAM and free storage.
3. Identify the exact GPU/driver before choosing a video runtime and model quantization.
4. Generate a real local clip, inspect it and validate with FFprobe; measure time, peak memory and heat.
5. Run the queue worker against the actual installed local model and test interruption/recovery.
6. Connect READY clip assets to the existing media manifest and long-form chapter timeline without creating another renderer.
7. Validate the complete MP4 in Termux with FFprobe before declaring the feature ready.
