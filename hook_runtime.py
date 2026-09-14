#!/usr/bin/env python3

"""Supervise hook_engine.py and guarantee a factual hook artifact on soft failure."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
ENGINE = BASE / "hook_engine.py"


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def normalize_space(text: str) -> str:
    return " ".join(str(text).split())


def derive_fallback_hook(script: str) -> str:
    """Return a short prefix made only from words already present in the script."""
    clean = normalize_space(script)
    if not clean:
        raise ValueError("roteiro vazio")

    first_sentence = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)[0].strip()
    sentence_words = re.findall(r"\S+", first_sentence)
    if 6 <= len(sentence_words) <= 18:
        return first_sentence

    words = re.findall(r"\S+", clean)
    if not words:
        raise ValueError("roteiro sem palavras")
    return " ".join(words[: min(16, len(words))]).strip()


def artifact_paths(base: Path, short_id: str):
    roteiros = base / "roteiros"
    return (
        roteiros / f"short_{short_id}.txt",
        roteiros / f"hook_{short_id}.txt",
        roteiros / f"hook_{short_id}.json",
    )


def read_nonempty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def ensure_hook_artifact(base: Path, short_id: str, reason: str) -> str:
    script_path, hook_txt, hook_json = artifact_paths(base, short_id)
    existing = read_nonempty(hook_txt)
    if existing:
        return existing

    script = read_nonempty(script_path)
    if not script:
        raise RuntimeError(f"roteiro ausente ou vazio: {script_path}")

    fallback = derive_fallback_hook(script)
    atomic_text(hook_txt, fallback)
    atomic_json(
        hook_json,
        {
            "runtime_fallback": True,
            "reason": reason,
            "chosen": 1,
            "hooks": [
                {
                    "text": fallback,
                    "source": "script_prefix",
                    "factuality": "inherited_from_approved_script",
                }
            ],
        },
    )
    return fallback


def engine_timeout() -> int:
    try:
        value = int(os.getenv("SHORT_HOOK_RUNTIME_TIMEOUT", "600"))
    except (TypeError, ValueError):
        value = 600
    return max(120, min(value, 900))


def clear_hook_artifacts(base: Path, short_id: str) -> None:
    _, hook_txt, hook_json = artifact_paths(base, short_id)
    for path in (hook_txt, hook_json):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run_engine(base: Path, timeout: int) -> int:
    process = subprocess.run(
        [sys.executable, str(base / "hook_engine.py")],
        cwd=str(base),
        stdin=subprocess.DEVNULL,
        check=False,
        timeout=timeout,
    )
    return int(process.returncode)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repair-only",
        action="store_true",
        help="Create a safe hook artifact from the existing approved script without calling Gemini.",
    )
    args = parser.parse_args(argv)

    if not SHORT_ID:
        print("ERRO HOOK RUNTIME: SHORT_ID vazio")
        return 1

    script_path, hook_txt, _ = artifact_paths(BASE, SHORT_ID)
    if not script_path.is_file() or not read_nonempty(script_path):
        print(f"ERRO HOOK RUNTIME: roteiro ausente ou vazio: {script_path}")
        return 1

    if args.repair_only:
        try:
            hook = ensure_hook_artifact(BASE, SHORT_ID, "repair_only_missing_hook")
        except Exception as exc:
            print(f"ERRO HOOK RUNTIME: {exc}")
            return 1
        print(f"HOOK_RUNTIME=REPAIR_PASS hook={hook_txt} words={len(hook.split())}")
        return 0

    if not ENGINE.is_file():
        print(f"ERRO HOOK RUNTIME: hook_engine.py não encontrado: {ENGINE}")
        return 1

    clear_hook_artifacts(BASE, SHORT_ID)
    timeout = engine_timeout()
    print(f"HOOK_RUNTIME=ACTIVE timeout={timeout}s")

    try:
        returncode = run_engine(BASE, timeout)
    except subprocess.TimeoutExpired:
        print(f"ERRO HOOK RUNTIME: hook_engine excedeu {timeout}s")
        return 1
    except Exception as exc:
        print(f"ERRO HOOK RUNTIME: falha executando hook_engine: {exc}")
        return 1

    if returncode != 0:
        print(f"ERRO HOOK RUNTIME: hook_engine retornou código {returncode}")
        return returncode or 1

    hook = read_nonempty(hook_txt)
    if hook:
        print(f"HOOK_RUNTIME=PASS mode=engine hook={hook_txt}")
        return 0

    try:
        hook = ensure_hook_artifact(BASE, SHORT_ID, "engine_soft_failure_missing_hook")
    except Exception as exc:
        print(f"ERRO HOOK RUNTIME: fallback falhou: {exc}")
        return 1

    print(
        "HOOK_RUNTIME=PASS mode=script_fallback "
        f"hook={hook_txt} words={len(hook.split())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
