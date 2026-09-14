#!/usr/bin/env python3

import json
import os
import re
import sys
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

CREDITS_DIR = os.path.join(BASE, "credits")
os.makedirs(CREDITS_DIR, exist_ok=True)

CREDIT_TXT = os.path.join(CREDITS_DIR, f"short_{SHORT_ID}.txt")
LEDGER_JSON = os.path.join(CREDITS_DIR, f"ledger_{SHORT_ID}.json")
ATTRIBUTION_TXT = os.path.join(CREDITS_DIR, f"attribution_{SHORT_ID}.txt")
PUBLISH_JSON = os.path.join(BASE, "roteiros", f"publish_{SHORT_ID}.json")
PUBLISH_TXT = os.path.join(BASE, "roteiros", f"publish_{SHORT_ID}.txt")


def atomic_text(path, text):
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def atomic_json(path, data):
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as exc:
        raise RuntimeError(f"falha lendo {path}: {exc}") from exc


def carregar_creditos():
    texto = read_text(CREDIT_TXT)
    if not texto.strip():
        return [], False

    blocos = re.split(r"\n(?=\s*SCENE\s+\d+)", texto.strip(), flags=re.IGNORECASE)
    saida = []

    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue

        cena = re.search(r"^\s*SCENE\s+(\d+)\s*$", bloco, flags=re.MULTILINE | re.IGNORECASE)
        autor = re.search(r"^\s*Author:\s*(.*)$", bloco, flags=re.MULTILINE | re.IGNORECASE)
        licenca = re.search(r"^\s*License:\s*(.*)$", bloco, flags=re.MULTILINE | re.IGNORECASE)
        pagina = re.search(r"^\s*Page:\s*(.*)$", bloco, flags=re.MULTILINE | re.IGNORECASE)

        if not cena or not pagina:
            raise RuntimeError("bloco de crédito Wikimedia malformado")

        numero = int(cena.group(1))
        if not 1 <= numero <= QTD_CENAS:
            raise RuntimeError(f"crédito referencia cena inválida: {numero}")

        page = pagina.group(1).strip()
        license_name = licenca.group(1).strip() if licenca else ""
        author = autor.group(1).strip() if autor else ""

        if not page.startswith("https://commons.wikimedia.org/wiki/"):
            raise RuntimeError(f"página Wikimedia inválida na cena {numero}")
        if not license_name:
            raise RuntimeError(f"licença Wikimedia ausente na cena {numero}")

        saida.append({
            "scene": numero,
            "source": "Wikimedia Commons",
            "author": author,
            "license": license_name,
            "page": page,
        })

    if not saida:
        raise RuntimeError("arquivo de créditos existe, mas nenhum crédito pôde ser lido")

    return saida, True


def deduplicar(itens):
    unicos = {}
    for item in itens:
        chave = item["page"].strip()
        if chave not in unicos:
            novo = dict(item)
            novo["scenes"] = [item["scene"]]
            unicos[chave] = novo
        elif item["scene"] not in unicos[chave]["scenes"]:
            unicos[chave]["scenes"].append(item["scene"])
    for item in unicos.values():
        item["scenes"] = sorted(item["scenes"])
    return list(unicos.values())


def precisa_atribuicao(licenca):
    l = str(licenca).strip().lower()
    if "public domain" in l or "public-domain" in l or "cc0" in l or l.startswith("pd"):
        return False
    return True


def criar_bloco(itens):
    obrigatorios = [x for x in itens if precisa_atribuicao(x.get("license", ""))]
    if not obrigatorios:
        return ""

    linhas = ["Créditos de mídia:"]
    for item in obrigatorios:
        autor = str(item.get("author", "")).strip()
        if not autor:
            raise RuntimeError(
                "ativo com licença que exige atribuição está sem autor: "
                + item.get("page", "")
            )
        licenca = item["license"]
        cenas = ", ".join(str(x) for x in item.get("scenes", []))
        linhas.append(f"• Cenas {cenas}: {autor} — {licenca}")
        linhas.append(f"  {item['page']}")
    return "\n".join(linhas)


try:
    creditos, arquivo_creditos_presente = carregar_creditos()
    unicos = deduplicar(creditos)
    bloco = criar_bloco(unicos)
except Exception as exc:
    sys.exit(f"ERRO Source Ledger: {exc}")

ledger = {
    "short_id": SHORT_ID,
    "version": "3.8",
    "credits_file_present": arquivo_creditos_presente,
    "total_scene_credits": len(creditos),
    "unique_assets": len(unicos),
    "attribution_required": bool(bloco),
    "assets": unicos,
}

try:
    atomic_json(LEDGER_JSON, ledger)
    atomic_text(ATTRIBUTION_TXT, (bloco + "\n") if bloco else "")
except Exception as exc:
    sys.exit(f"ERRO gravando ledger/atribuição: {exc}")

# Publish Pack é obrigatório neste ponto do pipeline.
try:
    with open(PUBLISH_JSON, "r", encoding="utf-8") as f:
        publish = json.load(f)
except Exception as exc:
    sys.exit(f"ERRO lendo Publish Pack JSON: {exc}")

if not isinstance(publish, dict) or not str(publish.get("chosen_title", "")).strip():
    sys.exit("ERRO: Publish Pack JSON inválido ou incompleto.")

publish["media_attribution"] = bloco
publish["source_ledger"] = LEDGER_JSON

try:
    atomic_json(PUBLISH_JSON, publish)
except Exception as exc:
    sys.exit(f"ERRO atualizando Publish Pack JSON com atribuição: {exc}")

# O TXT também é obrigatório porque é o pacote de publicação que o usuário vê.
try:
    texto_publish = read_text(PUBLISH_TXT)
except Exception as exc:
    sys.exit(f"ERRO lendo Publish Pack TXT: {exc}")

if not texto_publish.strip():
    sys.exit("ERRO: Publish Pack TXT ausente ou vazio.")

marcador = "\n\nCRÉDITOS DE MÍDIA:\n"
if marcador in texto_publish:
    texto_publish = texto_publish.split(marcador, 1)[0].rstrip()

novo_txt = texto_publish.rstrip()
if bloco:
    novo_txt += marcador + bloco
novo_txt += "\n"

try:
    atomic_text(PUBLISH_TXT, novo_txt)
except Exception as exc:
    sys.exit(f"ERRO atualizando Publish Pack TXT com atribuição: {exc}")

print()
print("================================")
print("SOURCE & ATTRIBUTION MANAGER 3.8")
print("================================")
print(f"Cenas Wikimedia: {len(creditos)}")
print(f"Arquivos únicos: {len(unicos)}")
print(f"Atribuição obrigatória: {'SIM' if bloco else 'NÃO'}")
print(f"Ledger: {LEDGER_JSON}")
print(f"Atribuição: {ATTRIBUTION_TXT}")
print()
print("SOURCE LEDGER: OK")
print()
