#!/usr/bin/env python3

import os
import re
import shlex
import subprocess

from pathlib import Path

from vi1500_01_common import (
    ROOT,
    policy,
)


def detect_contract(
    topic,
):
    custom = (
        os.environ.get(
            "VI1500_GENERATOR_COMMAND",
            ""
        )
        .strip()
    )


    if custom:
        command = custom.replace(
            "{topic}",
            topic
        )

        return {
            "contract":
                "USER_OVERRIDE",

            "command":
                shlex.split(
                    command
                ),

            "extra_env":
                {},
        }


    shell = (
        ROOT
        / "gerar_short.sh"
    )


    if shell.exists():
        text = shell.read_text(
            encoding="utf-8",
            errors="ignore"
        )


        if re.search(
            r"\$\{?1(?:\}|[^0-9])",
            text,
        ):
            return {
                "contract":
                    "GERAR_SHORT_POSITIONAL",

                "command": [
                    "bash",
                    str(
                        shell
                    ),
                    topic,
                ],

                "extra_env":
                    {},
            }


        if re.search(
            r"\bTEMA\b",
            text,
        ):
            return {
                "contract":
                    "GERAR_SHORT_ENV_TEMA",

                "command": [
                    "bash",
                    str(
                        shell
                    ),
                ],

                "extra_env": {
                    "TEMA":
                        topic,
                },
            }


        if re.search(
            r"\bTOPIC\b",
            text,
        ):
            return {
                "contract":
                    "GERAR_SHORT_ENV_TOPIC",

                "command": [
                    "bash",
                    str(
                        shell
                    ),
                ],

                "extra_env": {
                    "TOPIC":
                        topic,
                },
            }


    v6 = (
        ROOT
        / "v6.py"
    )


    if v6.exists():
        text = v6.read_text(
            encoding="utf-8",
            errors="ignore"
        )


        if re.search(
            r"add_argument\s*\([^)]*[\"'](?:topic|tema)[\"']",
            text,
            re.I,
        ):
            return {
                "contract":
                    "V6_POSITIONAL_TOPIC",

                "command": [
                    "python",
                    str(
                        v6
                    ),
                    topic,
                ],

                "extra_env":
                    {},
            }


    return {
        "contract":
            "UNRESOLVED",

        "command":
            None,

        "extra_env":
            {},
    }


def execute(
    topic,
    run_id,
    run_dir,
):
    config = policy()

    contract = detect_contract(
        topic
    )


    if not config.get(
        "execute_generation",
        True
    ):
        return {
            "status":
                "GENERATION_DISABLED",

            "contract":
                contract[
                    "contract"
                ],

            "returncode":
                0,
        }


    if not contract[
        "command"
    ]:
        return {
            "status":
                "GENERATOR_CONTRACT_UNRESOLVED",

            "contract":
                contract[
                    "contract"
                ],

            "returncode":
                0,
        }


    env = os.environ.copy()


    env.update({
        "VI1500_QUALIFICATION":
            "ON",

        "VI1500_RUN_ID":
            run_id,

        "SHORT_ID":
            run_id,

        "PUBLICATION_EXECUTED":
            "FALSE",

        "PUBLICATION_OFF":
            "1",

        "NO_PUBLISH":
            "1",
    })


    env.update(
        contract[
            "extra_env"
        ]
    )


    timeout = int(
        config.get(
            "generator_timeout_seconds",
            1200
        )
    )


    try:
        process = subprocess.run(
            contract[
                "command"
            ],
            cwd=str(
                ROOT
            ),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )


        (
            run_dir
            / "generator_stdout.txt"
        ).write_text(
            process.stdout,
            encoding="utf-8"
        )


        (
            run_dir
            / "generator_stderr.txt"
        ).write_text(
            process.stderr,
            encoding="utf-8"
        )


        return {
            "status":
                (
                    "GENERATOR_COMPLETED"
                    if process.returncode == 0
                    else "GENERATOR_FAILED"
                ),

            "contract":
                contract[
                    "contract"
                ],

            "command":
                contract[
                    "command"
                ],

            "returncode":
                process.returncode,

            "stdout_tail":
                process.stdout[
                    -2500:
                ],

            "stderr_tail":
                process.stderr[
                    -2500:
                ],
        }


    except subprocess.TimeoutExpired as exc:
        return {
            "status":
                "GENERATOR_TIMEOUT",

            "contract":
                contract[
                    "contract"
                ],

            "returncode":
                124,

            "stderr_tail":
                str(
                    exc
                ),
        }
