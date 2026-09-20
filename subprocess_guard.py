#!/usr/bin/env python3
"""Process helpers that terminate the full subprocess group on timeout."""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Any


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
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            out, err = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = proc.communicate()
        raise subprocess.TimeoutExpired(command, timeout, output=out, stderr=err) from exc

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
