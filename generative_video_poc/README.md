# ShortAutoPro — Termux-first generative video POC

**The Android phone running Termux is the brain and primary machine.** Project creation, queue, persistent state, clip claims, lease recovery, checkpoints, prompts, storage, FFmpeg, FFprobe and export orchestration belong on the phone. Remote compute remains disabled by default.

## Local controller and queue

The POC uses Python's built-in SQLite; no extra database server or service is needed.

Run these commands from the repository root in Termux:

    python -m generative_video_poc.brain device
    python -m generative_video_poc.brain create meu-short --spec-file generative_video_poc/examples/shorts.json
    python -m generative_video_poc.brain create meu-documentario --spec-file generative_video_poc/examples/longform.json
    python -m generative_video_poc.brain list
    python -m generative_video_poc.brain show meu-short
    python -m generative_video_poc.brain claim --project-id meu-short

The device report inspects Android manufacturer/model, platform identifiers from an allow-list, RAM, free internal storage, installed tools and optional Vulkan information. It does not collect serial numbers or account/network identifiers. Termux readiness for controlling projects is checked separately from whether a local video inference executable is present and compatible.

## Persistent state and recovery

- Database: $HOME/.shortautopro/state/queue.sqlite3.
- Project workspace: $HOME/.shortautopro/projects/<project_id>/.
- Every scene/clip has PENDING, RUNNING, READY or FAILED status.
- A worker claims a clip with a unique lease token. Heartbeats renew the lease.
- An expired lease returns to the queue up to the retry limit; the former worker cannot complete it.
- Retry limits are stored with each clip, not accepted as an override during retry.
- Each attempt gets its own suggested output filename; a retry cannot silently overwrite the previous attempt.
- Completion is accepted only when the file is inside the project workspace and metadata says FFprobe validated a real video stream.
- Project IDs are validated; project specs are immutable once created. Repeating the same create command is idempotent.

This is the controller/state foundation. A model worker is not yet wired into it, and the real device must still be used for the first local generation test.

## Local generation engine candidate

The upstream stable-diffusion.cpp project lists Android through Termux and video model families including Wan2.1/2.2 and LTX. It also warns that the project is under active development and command-line options may change. That makes it a candidate to evaluate, not a pre-certified mobile backend.

Important build caveat: the upstream Android build section documents an Android NDK path for arm64-v8a and OpenCL setup; it does not provide a one-command Termux package installation for every Android GPU. Its OpenCL notes are specifically for Adreno GPUs. The general Vulkan build instructions do not by themselves prove that the handset's Termux environment has a compatible Vulkan driver or build. Therefore this POC only detects local tools and reports hardware; it does not attempt to build or download a model blindly.

References:
- https://github.com/leejet/stable-diffusion.cpp
- https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/build.md

## Base packages

Install manually in Termux (the app does not install anything automatically):

    pkg update
    pkg install python ffmpeg git clang cmake ninja pkg-config
    termux-setup-storage

Keep models and intermediate files in Termux private storage. Copy finished videos to shared storage only after final validation. Never execute downloaded binaries from shared storage.

## Automated checks

    python -m compileall -q generative_video_poc tests_generative_video
    python -m unittest discover -s tests_generative_video -v

The automated tests use fake local processes and fixture data. They validate state, concurrency, recovery and contracts; they are not evidence of AI model inference. No paid API, GPU rental, external worker or cloud orchestrator is used.

## Next gate

1. Run the device report on the target phone.
2. Identify the exact chipset and GPU driver; only then choose the build backend and model quantization.
3. Pin/build one native inference backend for the reported Android ABI and test its model-specific flags.
4. Generate a real short clip locally; validate with FFprobe and record time, memory and thermal behavior.
5. Connect the model worker to this durable queue and test resume after terminating Termux mid-job.
6. Only after the above gates pass, propose integration with the existing canonical pipeline. Do not add another production orchestrator.
