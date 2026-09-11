#!/usr/bin/env python3


def normalized_label(
    *,
    generic,
    strategy,
    existing=None,
):
    if generic:

        return (
            "IMAGEM ILUSTRATIVA"
        )

    if existing:

        return existing

    if strategy == "ARCHIVAL_INSET":

        return (
            "ARQUIVO DO CASO"
        )

    if strategy == "DOCUMENT_PAGE_PREVIEW":

        return (
            "DOCUMENTO DO CASO"
        )

    return None


def main():
    tests = [
        (
            "GENERIC_LABEL",
            normalized_label(
                generic=True,
                strategy="IMAGE_COVER",
            ),
            "IMAGEM ILUSTRATIVA",
        ),

        (
            "ARCHIVAL_LABEL",
            normalized_label(
                generic=False,
                strategy="ARCHIVAL_INSET",
            ),
            "ARQUIVO DO CASO",
        ),

        (
            "DOCUMENT_LABEL",
            normalized_label(
                generic=False,
                strategy="DOCUMENT_PAGE_PREVIEW",
            ),
            "DOCUMENTO DO CASO",
        ),

        (
            "CONTEXT_LABEL_PRESERVED",
            normalized_label(
                generic=False,
                strategy="IMAGE_INSET",
                existing="IMAGEM DE CONTEXTO",
            ),
            "IMAGEM DE CONTEXTO",
        ),
    ]

    failed = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1400 REGRESSION"
    )
    print(
        "=============================================="
    )

    for name, actual, expected in tests:

        ok = (
            actual == expected
        )

        print(
            name,
            "=",
            (
                "PASS"
                if ok
                else "FAIL"
            ),
            "| expected=",
            expected,
            "| actual=",
            actual
        )

        if not ok:

            failed.append(
                name
            )

    print(
        "FAILED:",
        failed
    )

    if failed:
        raise SystemExit(1)

    print(
        "VI1400_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
