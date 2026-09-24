#!/usr/bin/env python3
"""Trava de FOTO REPETIDA (24/09/2026).

Cobrança dele no carrossel do meio-dia de 24/09: "você colocou nesse carrossel as mesmas imagens que tinha colocado
ontem à noite ... fica difícil se eu tiver que ficar controlando isso toda hora". De 12 fotos, 10 já tinham saído.

Regra: nenhuma foto (capa, cartão, fundo de Reels, story) repete o que já saiu nos últimos DIAS dias, nem com outro
nome de arquivo: a comparação é pela IMAGEM (dHash 16x16), não pelo nome. Recorte/versão da mesma foto também pega.
Só a mesma publicação pode usar a mesma foto mais de uma vez (ex.: capa e cartão do mesmo post).

Uso:
  python3 foto_repete.py checa content.json|materia.json     # lista repetidas (sai com erro se houver)
  python3 foto_repete.py registra content.json "rótulo"       # grava como usadas agora
  python3 foto_repete.py backfill                              # grava o histórico dos posts já publicados
Exceção (só com ordem dele): FOTO_REPETIDA_OK=1.
"""
import json, os, sys, glob, datetime, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent
REG = BASE / "fotos_usadas.json"
DIAS = 30
LIMIAR = 22
# prontos e ainda NÃO publicados em 24/09 (não entram no histórico)
NAO_PUBLICADOS = {"curio_lua.json", "curio_cratera.json", "curio_cerebro.json", "meta_connect.json", "elnino_mortes.json"}          # bits diferentes (de 256) para considerar a mesma imagem


def _hash(p):
    im = Image.open(p).convert("L").resize((17, 16), Image.LANCZOS)
    px = list(im.getdata())
    bits = 0
    for y in range(16):
        for x in range(16):
            bits = (bits << 1) | (px[y * 17 + x] > px[y * 17 + x + 1])
    return bits


def _dist(a, b):
    return bin(a ^ b).count("1")


def fotos(caminho):
    """todas as fotos citadas num content.json de carrossel ou json de Reels"""
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    out = []
    def walk(x):
        if isinstance(x, dict):
            for k in ("photo", "foto_cheia", "foto_alta", "story_photo"):
                if isinstance(x.get(k), str):
                    out.append(x[k])
            if isinstance(x.get("photos"), list):
                out.extend(p for p in x["photos"] if isinstance(p, str))
            for v in x.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    res = []
    for p in dict.fromkeys(out):
        q = Path(p) if Path(p).is_absolute() else BASE / p
        if q.exists():
            res.append(q)
    return res


def _carrega():
    try:
        return json.loads(REG.read_text(encoding="utf-8"))
    except Exception:
        return []


def repetidas(caminho, dias=DIAS):
    reg = _carrega()
    lim = (datetime.datetime.now() - datetime.timedelta(days=dias)).isoformat(timespec="minutes")
    reg = [r for r in reg if r["quando"] >= lim]
    achou = []
    for p in fotos(caminho):
        h = _hash(p)
        for r in reg:
            if _dist(h, int(r["hash"], 16)) <= LIMIAR:
                achou.append((p.name, r["arquivo"], r["quando"], r["post"]))
                break
    return achou


def trava(caminho):
    rep = repetidas(caminho)
    for a, b, q, post in rep:
        print(f"FOTO REPETIDA: {a} = {b} (já saiu em {q}, {post})")
    if rep and os.environ.get("FOTO_REPETIDA_OK") != "1":
        raise SystemExit(f"TRAVADO: {len(rep)} foto(s) já publicada(s) nos últimos {DIAS} dias. Troque as fotos.")


def registra(caminho, post, quando=None):
    reg = _carrega()
    quando = quando or datetime.datetime.now().isoformat(timespec="minutes")
    for p in fotos(caminho):
        reg.append({"hash": format(_hash(p), "064x"), "arquivo": p.name, "quando": quando, "post": post})
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=0), encoding="utf-8")


def backfill():
    """posts já publicados: pasta out_* com published.json ou content.json citado no ESTADO; json de Reels publicados"""
    feitos = 0
    for pj in glob.glob(str(BASE / "out_*/published.json")):
        cj = Path(pj).parent / "content.json"
        if cj.exists():
            q = datetime.datetime.fromtimestamp(os.path.getmtime(pj)).isoformat(timespec="minutes")
            registra(cj, Path(pj).parent.name, q); feitos += 1
    for cj in glob.glob(str(BASE / "content_*.json")) + glob.glob(str(BASE / "*.json")):
        if Path(cj).name in NAO_PUBLICADOS or Path(cj).name in ("publicadas.json", "fotos_usadas.json", "foco_cache.json") or cj.endswith(".ficha.json"):
            continue
        try:
            q = datetime.datetime.fromtimestamp(os.path.getmtime(cj)).isoformat(timespec="minutes")
            if fotos(cj):
                registra(cj, Path(cj).name, q); feitos += 1
        except Exception:
            pass
    print(f"backfill: {feitos} arquivos, {len(_carrega())} registros")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "checa":
        trava(sys.argv[2]); print("fotos: nenhuma repetida")
    elif cmd == "registra":
        registra(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else Path(sys.argv[2]).name)
    elif cmd == "backfill":
        backfill()
    else:
        print(__doc__)
