#!/usr/bin/env python3
"""Confere uma edição pronta na fila ANTES de ela ir para a prévia (e de novo antes de publicar).

Uso: python3 robo/checar_edicao.py fila/AAAA-MM-DD-edicao [--so carrossel|reels]
Sai com código 1 e lista os problemas se algo não passar. Nada aqui publica.
"""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import regras_legenda as RL   # noqa: E402
import nao_repete as NR       # noqa: E402
import foto_repete as FR      # noqa: E402
import boas_praticas as BP    # noqa: E402


def repetidas_no_post(caminho) -> list[str]:
    """24/09 (cobrança dele na prévia do Reels): a MESMA foto não pode aparecer duas vezes no mesmo post —
    nem com outro nome de arquivo (compara a imagem), nem capa repetindo cartão."""
    import json as _j
    d = _j.loads(Path(caminho).read_text(encoding="utf-8"))
    usos = []
    def walk(x):
        if isinstance(x, dict):
            for k in ("photo", "foto_cheia", "foto_alta"):
                if isinstance(x.get(k), str):
                    usos.append(x[k])
            if isinstance(x.get("photos"), list):
                usos.extend(f for f in x["photos"] if isinstance(f, str))
            for k, v in x.items():
                if k != "story_photo" and isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    vistos, erros = [], []
    for f in usos:
        q = Path(f) if Path(f).is_absolute() else RAIZ / f
        if not q.exists():
            continue
        h = FR._hash(q)
        for nome, h0 in vistos:
            if FR._dist(h, h0) <= FR.LIMIAR:
                erros.append(f"foto repetida DENTRO do post: {q.name} = {nome}")
                break
        vistos.append((q.name, h))
    return erros


def checa_carrossel(p: Path) -> list[str]:
    erros = []
    cj, pasta = p / "content.json", p / "carrossel"
    if not cj.exists():
        return ["carrossel: falta content.json"]
    d = json.loads(cj.read_text(encoding="utf-8"))
    if len(d.get("news", [])) != 9:
        erros.append(f"carrossel: {len(d.get('news', []))} notícias (o padrão é 9)")
    slides = sorted(pasta.glob("slide_*.jpg"))
    if len(slides) != 10:
        erros.append(f"carrossel: {len(slides)} slides renderizados (o padrão é 10) — rode render.py")
    e, _ = RL.checa_legenda(d.get("caption", ""), "carrossel")
    erros += [f"carrossel, legenda: {x}" for x in e]
    rep = NR.parecidas(NR.manchetes(str(cj)))
    erros += [f"carrossel: \"{a}\" repete \"{b}\" ({q})" for a, b, q, _ in rep]
    erros += [f"carrossel: foto repetida {a} = {b} ({q}, {post})" for a, b, q, post in FR.repetidas(cj)]
    erros += [f"carrossel: {e}" for e in repetidas_no_post(cj)]
    return erros


def checa_reels(p: Path) -> list[str]:
    erros = []
    mp4, leg, mj = p / "reels.mp4", p / "legenda.txt", p / "materia.json"
    if not mp4.exists() or not leg.exists():
        return ["reels: falta reels.mp4 ou legenda.txt"]
    e, _ = BP.confere_reels(str(mp4), str(leg), trava=False)
    erros += [f"reels: {x}" for x in e]
    e, _ = RL.checa_legenda(leg.read_text(encoding="utf-8"), "reels")
    erros += [f"reels, legenda: {x}" for x in e]
    if mj.exists():
        erros += [f"reels: foto repetida {a} = {b} ({q}, {post})" for a, b, q, post in FR.repetidas(mj)]
        erros += [f"reels: {e}" for e in repetidas_no_post(mj)]
        rep = NR.parecidas(NR.manchetes(str(mj)))
        erros += [f"reels: \"{a}\" repete \"{b}\" ({q})" for a, b, q, _ in rep]
        cj = p / "content.json"
        if cj.exists():   # Reels nunca repete o carrossel
            car = NR.manchetes(str(cj))
            for m in NR.manchetes(str(mj)):
                t = set(NR.tokens(m))
                for c in car:
                    comum = t & set(NR.tokens(c))
                    if len(comum) >= 3:
                        erros.append(f"reels repete o carrossel: \"{m}\" ~ \"{c}\"")
    return erros


def main():
    p = Path(sys.argv[1])
    so = sys.argv[sys.argv.index("--so") + 1] if "--so" in sys.argv else None
    erros = []
    if so in (None, "carrossel"):
        erros += checa_carrossel(p)
    if so in (None, "reels"):
        erros += checa_reels(p)
    for e in erros:
        print("PROBLEMA:", e)
    if erros:
        sys.exit(1)
    print("edição OK:", p)


if __name__ == "__main__":
    main()
