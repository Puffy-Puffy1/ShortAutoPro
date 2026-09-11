#!/usr/bin/env python3

import os

from vg4x_acquisition import (
    install as install_acquisition,
)

from vg4x_commit import (
    install as install_commit,
)


def install(namespace):

    if (
        os.getenv(
            "SAP_VG4X",
            "1",
        )
        ==
        "0"
    ):
        return {
            "enabled": False,
        }

    acquisition = install_acquisition(
        namespace
    )

    commit = install_commit(
        namespace
    )

    result = {
        "enabled":
            True,

        "acquisition":
            acquisition,

        "commit":
            commit,
    }

    print(
        "VG4X_BRIDGE=INSTALLED "
        f"acquisition="
        f"{acquisition.get('installed')} "
        f"commit="
        f"{commit.get('installed')}"
    )

    return result
