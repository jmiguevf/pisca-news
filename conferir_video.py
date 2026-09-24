#!/usr/bin/env python3
"""Confere o Reels JA PRONTO, nao os cartoes antes do video.

Foi escrito depois de descobrir que o zoom do quadro inteiro empurrava a manchete
para fora da zona segura: o conferir.py olhava o PNG do cartao, onde o texto ainda
estava no lugar, e o defeito so aparecia no mp4. Este aqui amostra quadros do
proprio arquivo publicado.

Uso: python3 conferir_video.py reels.mp4 [folha.jpg]
Sai com codigo 1 se achar tinta nas faixas que o Instagram cobre.
"""
import subprocess, sys, tempfile, os
from pathlib import Path
from PIL import Image, ImageDraw

MP4 = Path(sys.argv[1] if len(sys.argv) > 1 else "reels.mp4")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "conferencia_video.jpg")
N = int(os.environ.get("AMOSTRAS", "14"))

# O Reels aparece em dois lugares, com cortes diferentes.
VISTAS = {
    "player": dict(x0=108, y0=192, x1=972, y1=1296),
    "feed":   dict(x0=0,   y0=248, x1=1080, y1=1286),
}
LIMIAR = 150      # a partir daqui o pixel conta como "tinta" (texto ou marca)
TOLERA = 60       # quantos pixels claros a gente aceita por faixa (compressao, halo)


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def quadro(p, t, dest):
    subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(p),
                    "-frames:v", "1", str(dest), "-y"], check=True)


def tinta(im, caixa):
    """quantos pixels claros existem dentro da caixa (x0,y0,x1,y1)"""
    reg = im.crop(caixa).convert("L")
    h = reg.histogram()
    return sum(h[LIMIAR:])


def main():
    if not MP4.exists():
        sys.exit(f"nao achei {MP4}")
    D = dur(MP4)
    ts = [D * (i + 0.5) / N for i in range(N)]
    tmp = Path(tempfile.mkdtemp())
    problemas = []
    tiras = {k: [] for k in VISTAS}

    for i, t in enumerate(ts):
        f = tmp / f"q{i:02d}.png"
        quadro(MP4, t, f)
        im = Image.open(f).convert("RGB")
        W, H = im.size
        # faixas que somem em pelo menos uma das vistas
        # A FOTO sangra ate a borda de proposito — so o TEXTO tem que respeitar
        # a zona segura. Entao nas bordas laterais a gente olha apenas a faixa
        # onde vive texto sobre fundo escuro (abaixo da foto, que termina em 900).
        TXT0, TXT1 = 905, 1300
        faixas = {
            "topo (feed corta y<248)":  (0, 0, W, 248),
            "base (feed corta y>1286)": (0, 1286, W, H),
            "esquerda (player corta x<108)": (0, TXT0, 108, TXT1),
            "direita (player corta x>972)":  (972, TXT0, W, TXT1),
        }
        for nome, cx in faixas.items():
            n = tinta(im, cx)
            if n > TOLERA:
                problemas.append(f"  t={t:5.2f}s  {nome}: {n} pixels claros")
        for vista, c in VISTAS.items():
            rec = im.crop((c["x0"], c["y0"], c["x1"], c["y1"]))
            r = 300 / rec.width
            rec = rec.resize((300, int(rec.height * r)), Image.LANCZOS)
            d = ImageDraw.Draw(rec)
            d.text((6, 4), f"{t:.1f}s", fill=(255, 214, 10))
            tiras[vista].append(rec)

    # folha de contato: uma linha por vista
    linhas = []
    for vista, ims in tiras.items():
        h = max(i.height for i in ims)
        row = Image.new("RGB", (300 * len(ims), h), (18, 18, 22))
        for i, im in enumerate(ims):
            row.paste(im, (300 * i, 0))
        linhas.append((vista, row))
    alt = sum(r.height for _, r in linhas) + 26 * len(linhas)
    folha = Image.new("RGB", (max(r.width for _, r in linhas), alt), (18, 18, 22))
    d = ImageDraw.Draw(folha)
    y = 0
    for vista, row in linhas:
        d.text((8, y + 6), f"como o Instagram exibe — {vista}", fill=(255, 255, 255))
        y += 26
        folha.paste(row, (0, y))
        y += row.height
    folha.save(OUT, quality=88)

    print(f"OK {OUT}  ({N} amostras de {D:.1f}s, duas vistas)")
    if problemas:
        print("\nTINTA EM FAIXA QUE O INSTAGRAM COBRE:")
        print("\n".join(problemas))
        print("\nNAO PUBLIQUE. Encurte a manchete, ou o layout saiu da zona segura.")
        sys.exit(1)
    print("Nenhuma tinta nas faixas cortadas — enquadramento limpo nas duas vistas.")


if __name__ == "__main__":
    main()
