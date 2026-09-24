#!/usr/bin/env python3
"""Versão vertical 1080x1920 de uma foto DEITADA de objeto (ex.: óculos), para usar em tela cheia no Reels.

Só para objeto que vira "pedaço sem sentido" no recorte vertical. Rosto e cena: usar a própria foto com
"posicao"/"photo_position" (fica mais bonito e é o padrão). A foto inteira fica no alto (a partir de y, padrão 300),
sobre ela mesma ampliada, desfocada e um pouco escura — sem faixa preta. O arquivo sai com final _v.jpg e a ficha do
motor marca o cartão como "composta" (permitido, mas é exceção).

Uso: python3 compor_vertical.py photos/foto.jpg [y=300]   ->  photos/foto_v.jpg
"""
import sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance

W, H = 1080, 1920


def compor(origem, y=300):
    src = Image.open(origem).convert("RGB")
    k = max(W / src.width, H / src.height)
    fundo = src.resize((round(src.width * k), round(src.height * k)), Image.LANCZOS)
    x0, y0 = (fundo.width - W) // 2, (fundo.height - H) // 2
    fundo = fundo.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(40))
    fundo = ImageEnhance.Brightness(fundo).enhance(0.75)
    frente = src.resize((W, round(src.height * W / src.width)), Image.LANCZOS)
    fundo.paste(frente, (0, y))
    destino = Path(origem).with_name(Path(origem).stem + "_v.jpg")
    fundo.save(destino, quality=92)
    if src.width < W:
        print(f"AVISO: a foto tem {src.width} px de largura; vai esticar {W / src.width:.1f}x")
    return destino


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    print(compor(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300))
