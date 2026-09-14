#!/usr/bin/env python3

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

CREDITS_DIR = BASE / "credits"
CREDITS_DIR.mkdir(parents=True, exist_ok=True)
CREDIT_TXT = CREDITS_DIR / f"short_{SHORT_ID}.txt"
LEDGER_JSON = CREDITS_DIR / f"ledger_{SHORT_ID}.json"
ATTRIBUTION_TXT = CREDITS_DIR / f"attribution_{SHORT_ID}.txt"
PUBLISH_JSON = BASE / "roteiros" / f"publish_{SHORT_ID}.json"
PUBLISH_TXT = BASE / "roteiros" / f"publish_{SHORT_ID}.txt"
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
PROVENANCE_DIR = BASE / "manifests" / "source_provenance_live"


def atomic_text(path: Path, text: str):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def atomic_json(path: Path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
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
    cenas_vistas = set()

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
        if numero in cenas_vistas:
            raise RuntimeError(f"crédito duplicado para cena {numero}")
        cenas_vistas.add(numero)

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


def carregar_proveniencia_atual():
    """Return provenance records that point to this Short's physical media dir."""
    if not PROVENANCE_DIR.is_dir() or not MEDIA_DIR.is_dir():
        return []

    try:
        media_root = MEDIA_DIR.resolve()
    except Exception:
        media_root = MEDIA_DIR

    records = []
    for path in sorted(PROVENANCE_DIR.glob("source_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        local_path = str(data.get("local_path", "") or "").strip()
        if not local_path:
            continue
        try:
            local = Path(local_path).expanduser().resolve()
            if local.parent != media_root:
                continue
        except Exception:
            continue
        records.append(data)
    return records


def cenas_wikimedia_por_proveniencia(records):
    scenes = set()
    for item in records:
        provider = str(item.get("provider", "") or "").casefold()
        source_url = str(item.get("source_url", "") or "").casefold()
        if "wikimedia" not in provider and "commons.wikimedia.org" not in source_url:
            continue
        local_path = str(item.get("local_path", "") or "")
        match = re.search(r"scene_(\d{2})", Path(local_path).stem)
        if match:
            scenes.add(int(match.group(1)))
    return scenes


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
    value = str(licenca).strip().lower()
    return not (
        "public domain" in value
        or "public-domain" in value
        or "cc0" in value
        or value.startswith("pd")
    )


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
        cenas = ", ".join(str(x) for x in item.get("scenes", []))
        linhas.append(f"• Cenas {cenas}: {autor} — {item['license']}")
        linhas.append(f"  {item['page']}")
    return "\n".join(linhas)


def validar_cobertura_wikimedia(creditos, provenance_records):
    prov_scenes = cenas_wikimedia_por_proveniencia(provenance_records)
    credit_scenes = {int(item["scene"]) for item in creditos}
    missing = sorted(prov_scenes - credit_scenes)
    if missing:
        raise RuntimeError(
            "mídia Wikimedia sem crédito para cenas: "
            + ", ".join(str(x) for x in missing)
        )
    return sorted(prov_scenes)


def main():
    try:
        if not SHORT_ID:
            raise RuntimeError("SHORT_ID vazio")
        creditos, arquivo_creditos_presente = carregar_creditos()
        provenance_records = carregar_proveniencia_atual()
        provenance_wiki_scenes = validar_cobertura_wikimedia(
            creditos, provenance_records
        )
        unicos = deduplicar(creditos)
        bloco = criar_bloco(unicos)
    except Exception as exc:
        print(f"ERRO Source Ledger: {exc}")
        return 1

    ledger = {
        "short_id": SHORT_ID,
        "version": "3.9",
        "credits_file_present": arquivo_creditos_presente,
        "total_scene_credits": len(creditos),
        "unique_assets": len(unicos),
        "attribution_required": bool(bloco),
        "provenance_records_for_short": len(provenance_records),
        "wikimedia_scenes_from_provenance": provenance_wiki_scenes,
        "assets": unicos,
    }

    try:
        atomic_json(LEDGER_JSON, ledger)
        atomic_text(ATTRIBUTION_TXT, (bloco + "\n") if bloco else "")
    except Exception as exc:
        print(f"ERRO gravando ledger/atribuição: {exc}")
        return 1

    try:
        publish = json.loads(PUBLISH_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERRO lendo Publish Pack JSON: {exc}")
        return 1

    if not isinstance(publish, dict) or not str(publish.get("chosen_title", "")).strip():
        print("ERRO: Publish Pack JSON inválido ou incompleto.")
        return 1

    publish["media_attribution"] = bloco
    publish["source_ledger"] = str(LEDGER_JSON)

    try:
        atomic_json(PUBLISH_JSON, publish)
    except Exception as exc:
        print(f"ERRO atualizando Publish Pack JSON com atribuição: {exc}")
        return 1

    try:
        texto_publish = read_text(PUBLISH_TXT)
    except Exception as exc:
        print(f"ERRO lendo Publish Pack TXT: {exc}")
        return 1

    if not texto_publish.strip():
        print("ERRO: Publish Pack TXT ausente ou vazio.")
        return 1

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
        print(f"ERRO atualizando Publish Pack TXT com atribuição: {exc}")
        return 1

    print()
    print("================================")
    print("SOURCE & ATTRIBUTION MANAGER 3.9")
    print("================================")
    print(f"Cenas Wikimedia: {len(creditos)}")
    print(f"Arquivos únicos: {len(unicos)}")
    print(f"Proveniência desta execução: {len(provenance_records)}")
    print(f"Cenas Wikimedia confirmadas por proveniência: {len(provenance_wiki_scenes)}")
    print(f"Atribuição obrigatória: {'SIM' if bloco else 'NÃO'}")
    print(f"Ledger: {LEDGER_JSON}")
    print(f"Atribuição: {ATTRIBUTION_TXT}")
    print()
    print("SOURCE LEDGER: OK")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
