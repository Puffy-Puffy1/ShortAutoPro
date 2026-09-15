#!/usr/bin/env python3

from pathlib import Path


VERSION = "6.69"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


def _size(path):

    try:
        return path.stat().st_size

    except Exception:
        return 0


def audit():

    logdir = (
        BASE
        / "logs"
        / "producao"
    )


    files = []


    if logdir.exists():

        for path in logdir.glob(
            "*.json"
        ):

            files.append(
                {
                    "name": path.name,
                    "bytes": _size(path),
                }
            )


    files.sort(
        key=lambda x:
            x["bytes"],
        reverse=True
    )


    total = sum(
        x["bytes"]
        for x in files
    )


    warnings = []


    if total > 25 * 1024 * 1024:

        warnings.append(
            "production_json_logs_large"
        )


    return {
        "version": VERSION,
        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),
        "json_report_count":
            len(files),
        "json_total_bytes":
            total,
        "largest_reports":
            files[:10],
        "warnings": warnings,

        # This stage NEVER deletes automatically.
        "files_deleted": 0,

        "recommended_policy": {
            "keep_latest_master_reports": True,
            "keep_final_manifest": True,
            "keep_final_video": True,
            "remove_temp_only_after_success":
                True,
        },
    }


def self_test():

    result = audit()

    assert result["files_deleted"] == 0

    print("VI6.69 STORAGE GUARD=PASS")


if __name__ == "__main__":
    self_test()
