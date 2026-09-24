#!/usr/bin/env python3
"""Mostra os cartoes do Reels COMO O INSTAGRAM EXIBE, nos DOIS lugares, para conferir
antes de publicar.

Uso: python3 conferir.py [pasta_dos_cartoes] [saida.jpg]

O Reels de 1080x1920 aparece de dois jeitos, com cortes diferentes:
  PLAYER (tela cheia): preenche a altura e corta ~108px de cada lado; a interface do
    Instagram cobre o topo (ate y=192) e o rodape (a partir de y=1296).
  FEED: mostra a largura toda, mas corta y<248 em cima e y>1286 embaixo.
Zona que sobrevive aos dois: x 118..830, y 300..1280. Nenhum texto pode sair dali.
Em vermelho: area perdida ou coberta. Nenhuma letra pode cair no vermelho.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("reels_frames")
DST = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC / "conferencia.jpg"
LARG = 360


def carta(p):
    im = Image.open(p).convert("RGB")
    if im.size != (1080, 1920):        # os cartoes saem em 1620x2880 (supersample 1.5x)
        im = im.resize((1080, 1920), Image.LANCZOS)
    return im


def vista_player(im, w=LARG):
    """tela cheia: corta as laterais, interface cobre topo e rodape"""
    v = im.crop((108, 0, 972, 1920))
    h = int(w * 1920 / 864)
    v = v.resize((w, h), Image.LANCZOS)
    ov = Image.new("RGBA", v.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    k = h / 1920
    d.rectangle([0, 0, w, int(192 * k)], fill=(255, 0, 0, 78))
    d.rectangle([0, int(1296 * k), w, h], fill=(255, 0, 0, 78))
    d.rectangle([int((852 - 108) * w / 864), int(430 * k), w, int(1296 * k)], fill=(255, 0, 0, 78))
    return Image.alpha_composite(v.convert("RGBA"), ov).convert("RGB")


def vista_feed(im, w=LARG):
    """feed: largura toda, corta em cima e embaixo"""
    v = im.crop((0, 248, 1080, 1286))
    h = int(w * (1286 - 248) / 1080)
    return v.resize((w, h), Image.LANCZOS)


def main():
    cards = sorted(SRC.glob("card_*.png"))
    if not cards:
        print("nenhum cartao em", SRC); sys.exit(1)
    pares = []
    for c in cards:
        im = carta(c)
        pares.append((vista_player(im), vista_feed(im)))
    pw, ph = pares[0][0].size
    fw, fh = pares[0][1].size
    col = max(pw, fw)
    alt = ph + 14 + fh
    n = len(pares); cols = min(5, n); linhas = (n + cols - 1) // cols
    sh = Image.new("RGB", (col * cols + (cols + 1) * 12, alt * linhas + (linhas + 1) * 16 + 30), (24, 24, 30))
    d = ImageDraw.Draw(sh)
    try:
        f = ImageFont.load_default(16)
    except Exception:
        f = ImageFont.load_default()
    d.text((14, 8), "linha de cima = PLAYER tela cheia (vermelho = interface)   |   "
                    "linha de baixo = FEED (ja cortado em cima e embaixo)", fill=(200, 200, 210), font=f)
    for i, (vp, vf) in enumerate(pares):
        x = 12 + (i % cols) * (col + 12)
        y = 30 + 16 + (i // cols) * (alt + 16)
        sh.paste(vp, (x, y)); sh.paste(vf, (x, y + ph + 14))
    sh.save(DST, quality=93)
    print(f"OK {DST}  ({n} cartoes, duas vistas cada)")


if __name__ == "__main__":
    main()
