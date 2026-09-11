#!/usr/bin/env python3

import os
import sys
import subprocess

BASE_DIR = os.path.expanduser("~/ShortAutoPro")

os.chdir(BASE_DIR)

scripts = [
    "roteiro.py",
    "audio.py",
    "midia.py",
    "video.py"
]

print()
print("========================================")
print("       SHORTAUTO - GERADOR DE SHORT")
print("========================================")
print()

for script in scripts:

    caminho = os.path.join(
        BASE_DIR,
        script
    )

    print()
    print("----------------------------------------")
    print(f"Executando: {script}")
    print("----------------------------------------")

    resultado = subprocess.run(
        [
            sys.executable,
            caminho
        ]
    )

    if resultado.returncode != 0:

        print()
        print("========================================")
        print(f"ERRO AO EXECUTAR: {script}")
        print("========================================")
        print()

        sys.exit(1)

print()
print("========================================")
print("      SHORT GERADO COM SUCESSO!")
print("========================================")
print()
print(
    f"Confira os arquivos em:\n"
    f"{BASE_DIR}/videos/"
)
print()
