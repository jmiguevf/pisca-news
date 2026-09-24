#!/usr/bin/env python3
"""Monta fotos compostas para o Reels de materia (faixa ALTA = 1080x560).
Usa o Chromium do motor (mesmas fontes Anton/Inter). Uso:
    compor.py spec.json
spec: {"saida": "photos/x.jpg", "tipo": "grade"|"duelo", "tiles": [{"foto","crop":[x0,y0,x1,y1],"rotulo"}]}
Tudo que importa fica entre x=150 e x=930 (zoom de 7% + corte lateral do player)."""
import json, sys, base64, io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
import reels as R

W, H = 1080, 560


def _uri(path, crop=None, maxw=1100):
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(tuple(crop))
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def html_grade(tiles):
    # 2x2 entre x=150 e x=930
    pos = [(150, 8), (546, 8), (150, 246), (546, 246)]   # 23/09: a base da faixa (y>480) fica sob o degrade do texto
    out = []
    for (x, y), t in zip(pos, tiles):
        out.append(f'<div class="t" style="left:{x}px;top:{y}px;width:384px;height:230px">'
                   f'<img src="{_uri(t["foto"], t.get("crop"))}" style="object-position:{t.get("pos", "50% 40%")}">'
                   f'<div class="g"></div><div class="pill">{t["rotulo"]}</div></div>')
    return "".join(out)


def html_duelo(tiles):
    out = []
    for (x, t) in zip((150, 546), tiles):
        out.append(f'<div class="t" style="left:{x}px;top:8px;width:384px;height:470px">'
                   f'<img src="{_uri(t["foto"], t.get("crop"))}" style="object-position:{t.get("pos", "50% 50%")}">'
                   f'<div class="g2"></div><div class="big">{t["rotulo"]}</div></div>')
    out.append(f'<div class="x"><svg viewBox="0 0 100 100" width="46" height="46">'
               f'<path d="M24 24 L76 76 M76 24 L24 76" stroke="#101016" stroke-width="15" stroke-linecap="round"/></svg></div>')
    return "".join(out)


CSS = f"""{R.FONTS}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;background:#0c0c12;overflow:hidden}}
.t{{position:absolute;overflow:hidden;border-radius:18px;background:#1c1c26}}
.t img{{width:100%;height:100%;object-fit:cover;display:block}}
.g{{position:absolute;left:0;right:0;bottom:0;height:46%;background:linear-gradient(to bottom,rgba(12,12,18,0),rgba(12,12,18,.88))}}
.g2{{position:absolute;left:0;right:0;bottom:0;height:40%;background:linear-gradient(to bottom,rgba(12,12,18,0),rgba(12,12,18,.92))}}
.pill{{position:absolute;left:16px;bottom:14px;font-family:'Inter';font-weight:800;font-size:25px;color:#fff;
  letter-spacing:-.2px;text-shadow:0 1px 6px rgba(0,0,0,.9)}}
.pill b{{color:{R.ACCENT};font-weight:800}}
.big{{position:absolute;left:0;right:0;bottom:22px;text-align:center;font-family:'Anton';font-size:92px;
  color:#fff;letter-spacing:1px;text-shadow:0 2px 14px rgba(0,0,0,.9)}}
.x{{position:absolute;left:{540 - 44}px;top:{243 - 44}px;width:88px;height:88px;border-radius:50%;
  background:{R.ACCENT};display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 8px #0c0c12}}
"""


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    corpo = html_grade(spec["tiles"]) if spec["tipo"] == "grade" else html_duelo(spec["tiles"])
    doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{corpo}</body></html>'
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": W, "height": H})
        pg.set_content(doc, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(150)
        png = pg.screenshot(type="png")
        br.close()
    Image.open(io.BytesIO(png)).convert("RGB").save(spec["saida"], "JPEG", quality=94)
    print("ok", spec["saida"])


if __name__ == "__main__":
    main()
