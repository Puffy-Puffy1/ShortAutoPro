#!/usr/bin/env python3
"""Process helpers that terminate the full subprocess group on timeout."""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Any


def _stop_group(proc: subprocess.Popen) -> tuple[Any, Any]:
    """Reap the leader and stop descendants even when the leader exits first."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        output = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        output = None
    finally:
        # communicate may return as soon as the leader exits when output is
        # inherited. A descendant ignoring TERM must still receive KILL.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    return proc.communicate() if output is None else output


def run_group(
    command: list[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    check: bool = False,
    capture_output: bool = False,
    text: bool = False,
    stdout: Any = None,
    stderr: Any = None,
) -> subprocess.CompletedProcess:
    if capture_output:
        if stdout is not None or stderr is not None:
            raise ValueError("stdout/stderr cannot be combined with capture_output")
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        text=text,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out, err = _stop_group(proc)
        raise subprocess.TimeoutExpired(command, timeout, output=out, stderr=err) from exc
    except BaseException:
        # Ctrl+C and unexpected communication errors must not orphan FFmpeg.
        _stop_group(proc)
        raise

    result = subprocess.CompletedProcess(command, proc.returncode, out, err)
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode,
            command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def check_output_group(
    command: list[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    text: bool = False,
    stderr: Any = None,
) -> str | bytes:
    result = run_group(
        command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        check=True,
        stdout=subprocess.PIPE,
        stderr=stderr,
        text=text,
    )
    return result.stdout
