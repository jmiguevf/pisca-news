#!/usr/bin/env python3
"""Gera o logo do Pisca (ícone, foto de perfil, lockups horizontais) para uma cor de destaque.

Uso: ACCENT="#FFD60A" NOME="amarelo" python3 logo.py
Saída em logo/<nome>/
"""
import os, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

BASE = Path(__file__).resolve().parent
ACCENT = os.environ.get("ACCENT", "#FFD60A")
NOME = os.environ.get("NOME", "amarelo")
OUT = BASE / "logo" / NOME
OUT.mkdir(parents=True, exist_ok=True)
BG = "#0B0B10"
FONT_DIR = BASE / "node_modules" / "@fontsource"


def font_face(family, path, weight=400):
    b64 = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return (f"@font-face{{font-family:'{family}';src:url('data:font/woff2;base64,{b64}') format('woff2');"
            f"font-weight:{weight};font-style:normal;font-display:block;}}")


FONTS = "\n".join([
    font_face("Anton", FONT_DIR / "anton/files/anton-latin-400-normal.woff2"),
    font_face("Inter", FONT_DIR / "inter/files/inter-latin-500-normal.woff2", 500),
    font_face("Inter", FONT_DIR / "inter/files/inter-latin-ext-500-normal.woff2", 500),
])

# O olho no meio da piscada: pálpebra de cima mais baixa que a de baixo.
EYE_PATHS = (
    '<path d="M10 56 C 24 30, 76 30, 90 56 C 76 78, 24 78, 10 56 Z" fill="{ink}"/>'
    '<circle cx="50" cy="54.5" r="15" fill="{accent}"/>'
    '<circle cx="50" cy="54.5" r="7" fill="{ink}"/>'
)


def eye_svg(size, accent, ink, bg=None, radius=0, bleed=False):
    inner = EYE_PATHS.format(ink=ink, accent=accent)
    rect = ""
    if bg:
        if bleed:
            rect = f'<rect width="100" height="100" fill="{bg}"/>'
        else:
            rect = f'<rect width="100" height="100" rx="{radius}" fill="{bg}"/>'
    # olho ocupa ~76% do quadrado
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">{rect}'
            f'<g transform="translate(12 8.6) scale(0.76)">{inner}</g></svg>')


def page(body, w, h, bg="transparent"):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}'
            f'*{{margin:0;padding:0;box-sizing:border-box}}html,body{{width:{w}px;height:{h}px;background:{bg};overflow:hidden}}'
            f'.wrap{{width:{w}px;height:{h}px;display:flex;align-items:center;justify-content:center;gap:0}}'
            f'</style></head><body><div class="wrap">{body}</div></body></html>')


def lockup(accent, ink_text, tagline_color, bg):
    mark = eye_svg(300, accent, BG, bg=accent, radius=22)
    return page(
        f'<div style="display:flex;align-items:center;gap:70px">'
        f'{mark}'
        f'<div><div style="font-family:Anton;font-size:300px;line-height:.9;letter-spacing:12px;color:{ink_text}">PISCA</div>'
        f'<div style="font-family:Inter;font-weight:500;font-size:54px;letter-spacing:.5px;color:{tagline_color};margin-top:22px">'
        f'O que mudou no mundo enquanto você piscava.</div></div></div>', 2400, 800, bg)


def shot(pw, html, w, h, path, omit_bg=False):
    pg = pw.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    pg.set_content(html, wait_until="load")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(150)
    pg.screenshot(path=str(path), omit_background=omit_bg)
    pg.close()


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ícone (cantos arredondados, fundo transparente fora do quadrado)
        (OUT / "pisca_icone.svg").write_text(eye_svg(1024, ACCENT, BG, bg=ACCENT, radius=22), encoding="utf-8")
        shot(b, page(eye_svg(1024, ACCENT, BG, bg=ACCENT, radius=22), 1024, 1024), 1024, 1024, OUT / "pisca_icone.png", omit_bg=True)
        # foto de perfil do Instagram (sangrado, o Instagram recorta em círculo)
        shot(b, page(eye_svg(1080, ACCENT, BG, bg=ACCENT, bleed=True), 1080, 1080), 1080, 1080, OUT / "pisca_perfil_instagram.png")
        # versão invertida do ícone (olho na cor, fundo preto) para stories/marca d'água
        shot(b, page(eye_svg(1024, BG, ACCENT, bg=BG, radius=22), 1024, 1024), 1024, 1024, OUT / "pisca_icone_invertido.png", omit_bg=True)
        # lockups horizontais
        shot(b, lockup(ACCENT, "#FFFFFF", "#B9B9C3", BG), 2400, 800, OUT / "pisca_horizontal_escuro.png")
        shot(b, lockup(ACCENT, "#0B0B10", "#5C5F6A", "#FFFFFF"), 2400, 800, OUT / "pisca_horizontal_claro.png")
        b.close()
    # simulação do círculo do perfil
    im = Image.open(OUT / "pisca_perfil_instagram.png").convert("RGBA")
    mask = Image.new("L", im.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).ellipse((0, 0, im.size[0] - 1, im.size[1] - 1), fill=255)
    circ = Image.new("RGBA", im.size, (0, 0, 0, 0)); circ.paste(im, (0, 0), mask)
    circ.save(OUT / "pisca_perfil_circulo.png")
    print("OK", OUT)


if __name__ == "__main__":
    main()
