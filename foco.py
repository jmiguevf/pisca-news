#!/usr/bin/env python3
"""Enquadramento automático pelo ROSTO (24/09): sem borda, a foto é sempre recortada para preencher a caixa — e o
recorte não pode cortar rosto. Este módulo acha o(s) rosto(s) (OpenCV, detector de rosto frontal) e devolve o
"object-position" que põe o rosto no ponto certo da caixa. Sem rosto na foto: devolve o padrão (centro).

Uso no código: import foco; foco.posicao(foto, caixa_w, caixa_h, alvo_y=0.35, padrao="50% 45%")
Uso avulso:    python3 foco.py photos/foto.jpg 1080 760 0.4
"""
import json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CACHE = BASE / "foco_cache.json"
_cache = None


def _carrega():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE.read_text())
        except Exception:
            _cache = {}
    return _cache


def rostos(foto):
    """[(x, y, w, h)] dos rostos, em fração da imagem (0..1), do maior para o menor"""
    p = Path(foto) if Path(foto).is_absolute() else BASE / foto
    chave = f"{p}:{int(p.stat().st_mtime)}"
    c = _carrega()
    if chave in c:
        return [tuple(r) for r in c[chave]]
    import cv2
    img = cv2.imread(str(p))
    if img is None:
        return []
    H, W = img.shape[:2]
    k = 900 / max(W, H) if max(W, H) > 900 else 1.0
    cinza = cv2.cvtColor(cv2.resize(img, (int(W * k), int(H * k))) if k != 1.0 else img, cv2.COLOR_BGR2GRAY)
    cinza = cv2.equalizeHist(cinza)
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    lado = int(min(cinza.shape[:2]) * 0.07)
    achados = det.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=6, minSize=(lado, lado))
    h2, w2 = cinza.shape[:2]
    res = sorted([(x / w2, y / h2, w / w2, h / h2) for (x, y, w, h) in achados], key=lambda r: -r[2] * r[3])
    # descarta rostinhos perdidos no fundo (menos de 1/4 da área do maior)
    if res:
        a0 = res[0][2] * res[0][3]
        res = [r for r in res if r[2] * r[3] >= a0 / 4]
    c[chave] = res
    try:
        CACHE.write_text(json.dumps(c))
    except Exception:
        pass
    return res


def posicao(foto, caixa_w, caixa_h, alvo_y=0.35, padrao="50% 45%", alvo_x=0.5):
    """object-position (cover) que põe o centro do(s) rosto(s) em (alvo_x, alvo_y) da caixa, sem sair da foto"""
    try:
        from PIL import Image
        p = Path(foto) if Path(foto).is_absolute() else BASE / foto
        with Image.open(p) as im:
            w, h = im.size
        rs = rostos(p)
    except Exception:
        return padrao
    if not rs:
        return padrao
    x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs)
    x1 = max(r[0] + r[2] for r in rs); y1 = max(r[1] + r[3] for r in rs)
    fx, fy = (x0 + x1) / 2, (y0 + y1) / 2
    s = max(caixa_w / w, caixa_h / h)
    W2, H2 = w * s, h * s
    ox, oy = W2 - caixa_w, H2 - caixa_h
    px = 0.5 if ox < 1 else min(1, max(0, (fx * W2 - alvo_x * caixa_w) / ox))
    py = 0.5 if oy < 1 else min(1, max(0, (fy * H2 - alvo_y * caixa_h) / oy))
    return f"{px * 100:.0f}% {py * 100:.0f}%"


if __name__ == "__main__":
    f = sys.argv[1]
    bw, bh = int(sys.argv[2]) if len(sys.argv) > 2 else 1080, int(sys.argv[3]) if len(sys.argv) > 3 else 1920
    ay = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35
    print("rostos:", [tuple(round(v, 2) for v in r) for r in rostos(f)])
    print("posição:", posicao(f, bw, bh, ay))
