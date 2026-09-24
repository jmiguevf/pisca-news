#!/usr/bin/env python3
"""Renderiza o carrossel (1080x1440) a partir de content.json.

Uso: python3 render.py [content.json] [pasta_saida]
Saída: slide_01.jpg ... slide_NN.jpg + preview.jpg (folha de contato) + caption.txt

Cada notícia pode ter "photo" (caminho local). Sem foto, cai no layout tipográfico.
"""
import json, sys, os, html, base64, mimetypes
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

BASE = Path(__file__).resolve().parent
CONTENT = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "content.json"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE / "out"
OUT.mkdir(parents=True, exist_ok=True)

FONT_DIR = BASE / "node_modules" / "@fontsource"
ACCENT = os.environ.get("ACCENT", "#FFD60A")
BG = "#0B0B10"
_r, _g, _b = int(ACCENT[1:3], 16), int(ACCENT[3:5], 16), int(ACCENT[5:7], 16)
ACCENT_RGB = f"{_r},{_g},{_b}"


def data_uri(path):
    p = Path(path)
    if not p.is_absolute():
        p = CONTENT.parent / p
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def font_face(family, path, weight=400):
    b64 = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return (f"@font-face{{font-family:'{family}';src:url('data:font/woff2;base64,{b64}') format('woff2');"
            f"font-weight:{weight};font-style:normal;font-display:block;}}")


FONTS = "\n".join(
    [font_face("Anton", FONT_DIR / "anton/files/anton-latin-400-normal.woff2"),
     font_face("Anton", FONT_DIR / "anton/files/anton-latin-ext-400-normal.woff2")]
    + [font_face("Inter", FONT_DIR / f"inter/files/inter-{sub}-{w}-normal.woff2", w)
       for sub in ("latin", "latin-ext") for w in (400, 500, 600, 700, 800)]
)

CSS = f"""
{FONTS}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1440px;overflow:hidden;background:{BG};color:#fff;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}}
.slide{{position:relative;width:1080px;height:1440px;overflow:hidden;background:{BG}}}
.accent{{color:{ACCENT}}}
/* fotos */
.photo{{position:absolute;left:0;top:0;width:1080px;height:760px;overflow:hidden;background:#15151c}}
.photo img{{width:100%;height:100%;object-fit:cover;display:block}}
.photo .bg{{position:absolute;inset:0;filter:blur(34px) brightness(.5) saturate(1.15);transform:scale(1.25)}}
.photo .fg{{position:absolute;inset:0;object-fit:contain}}
.strips{{position:absolute;left:0;top:0;width:1080px;height:940px;display:flex;gap:0;background:{BG}}}
.strips div{{flex:1;overflow:hidden;background:#15151c}}
.strips img{{width:100%;height:100%;object-fit:cover;display:block}}
.scrim{{position:absolute;left:0;top:0;width:1080px;height:260px;background:linear-gradient(180deg,rgba(0,0,0,.62) 0%,rgba(0,0,0,0) 100%)}}
.fade{{position:absolute;left:0;width:1080px;background:linear-gradient(180deg,rgba(11,11,16,0) 0%,rgba(11,11,16,.55) 45%,rgba(11,11,16,.92) 75%,{BG} 100%)}}
.glow{{position:absolute;top:-260px;right:-260px;width:820px;height:820px;border-radius:50%;background:radial-gradient(circle,rgba({ACCENT_RGB},.28) 0%,rgba({ACCENT_RGB},.09) 38%,rgba(11,11,16,0) 66%)}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);background-size:90px 90px;mask-image:linear-gradient(180deg,rgba(0,0,0,.9),rgba(0,0,0,.25) 70%,transparent)}}
/* barra superior */
.top{{position:absolute;top:56px;left:64px;right:64px;display:flex;justify-content:space-between;align-items:center}}
.logo{{display:flex;align-items:center;gap:16px}}
.mark{{width:58px;height:58px;border-radius:15px;background:{ACCENT};display:flex;align-items:center;justify-content:center;box-shadow:0 6px 24px rgba(0,0,0,.35)}}
.mark svg{{width:32px;height:32px}}
.brand{{font-family:'Anton';font-size:40px;letter-spacing:3px;line-height:1;padding-top:4px;text-shadow:0 2px 12px rgba(0,0,0,.6)}}
.date{{font-weight:700;font-size:22px;letter-spacing:1px;color:#fff;padding:12px 20px;border-radius:999px;background:rgba(11,11,16,.55);border:1.5px solid rgba(255,255,255,.28);backdrop-filter:blur(6px)}}
/* capa */
.cover-head{{position:absolute;left:64px;right:64px;top:660px;font-family:'Anton';font-size:118px;line-height:1.22;text-transform:uppercase;letter-spacing:-1px;text-shadow:0 4px 30px rgba(0,0,0,.7)}}
.cover-sub{{position:absolute;left:64px;right:64px;font-size:34px;font-weight:500;line-height:1.35;color:#D6D6DE}}
.swipe{{position:absolute;bottom:88px;left:64px;background:{ACCENT};color:{BG};font-family:'Anton';font-size:32px;letter-spacing:2px;padding:16px 30px 14px;border-radius:999px;display:flex;align-items:center;gap:14px}}
.handle{{position:absolute;bottom:100px;right:64px;font-weight:600;font-size:26px;color:rgba(255,255,255,.55)}}
.credits{{position:absolute;bottom:34px;left:64px;right:64px;font-size:16px;font-weight:500;color:rgba(255,255,255,.38);letter-spacing:.2px}}
/* notícia */
.content{{position:absolute;left:64px;right:64px;top:580px;bottom:190px;display:flex;flex-direction:column;gap:24px}}
.row{{display:flex;align-items:center;gap:22px}}
.num{{font-family:'Anton';font-size:118px;line-height:.9;color:{ACCENT};text-shadow:0 4px 24px rgba(0,0,0,.6)}}
.tag{{font-weight:700;font-size:22px;letter-spacing:3px;color:{BG};background:{ACCENT};border-radius:999px;padding:12px 20px 10px}}
.head{{font-family:'Anton';font-size:88px;line-height:1.12;text-transform:uppercase;letter-spacing:-.5px;text-shadow:0 4px 24px rgba(0,0,0,.6)}}
.body{{font-size:36px;font-weight:500;line-height:1.4;color:#DCDCE2}}
.source{{position:absolute;bottom:112px;left:64px;font-weight:600;font-size:25px;color:#8A8A96}}
.source b{{color:#D6D6DE;font-weight:700}}
.pcredit{{position:absolute;bottom:72px;left:64px;font-weight:500;font-size:18px;color:rgba(255,255,255,.4)}}
.dots{{position:absolute;bottom:118px;right:64px;display:flex;gap:10px;align-items:center}}
.dots i{{display:block;width:40px;height:8px;border-radius:4px;background:rgba(255,255,255,.18)}}
.dots i.on{{background:{ACCENT};width:64px}}
/* layout 10: capa integrada, contador e CTA */
.capa-q{{position:absolute;left:64px;right:64px;top:150px;font-family:'Anton';font-size:60px;line-height:1.12;text-transform:uppercase;letter-spacing:-.3px;text-shadow:0 4px 24px rgba(0,0,0,.8)}}
.scrim-tall{{position:absolute;left:0;top:0;width:1080px;height:460px;background:linear-gradient(180deg,rgba(0,0,0,.78) 0%,rgba(0,0,0,.55) 55%,rgba(0,0,0,0) 100%)}}
.counter{{position:absolute;bottom:106px;right:64px;font-family:'Anton';font-size:34px;letter-spacing:2px;color:rgba(255,255,255,.7)}}
.counter b{{color:{ACCENT};font-weight:400}}
.swipe-r{{position:absolute;bottom:96px;right:64px;background:{ACCENT};color:{BG};font-family:'Anton';font-size:28px;letter-spacing:2px;padding:14px 26px 12px;border-radius:999px}}
.cta-band{{position:absolute;left:0;right:0;bottom:0;height:78px;background:{ACCENT};color:{BG};display:flex;align-items:center;justify-content:center;gap:26px;font-family:'Anton';font-size:30px;letter-spacing:2px;text-transform:uppercase}}
.cta-band span{{font-family:'Inter';font-weight:700;font-size:24px;letter-spacing:.5px;text-transform:none}}
/* fechamento */
.dim{{position:absolute;inset:0;background:rgba(11,11,16,.72)}}
.close-title{{position:absolute;left:64px;right:64px;top:360px;font-family:'Anton';font-size:150px;line-height:1.10;text-transform:uppercase;text-shadow:0 4px 30px rgba(0,0,0,.7)}}
.close-l1{{position:absolute;left:64px;right:64px;top:740px;font-size:40px;font-weight:500;line-height:1.35;color:#E4E4EA}}
.close-l2{{position:absolute;left:64px;right:64px;top:890px;font-size:40px;font-weight:500;line-height:1.35;color:#E4E4EA}}
.close-q{{position:absolute;left:64px;right:64px;top:1050px;font-size:42px;font-weight:700;line-height:1.3;color:{ACCENT}}}
.close-handle{{position:absolute;bottom:88px;left:64px;background:{ACCENT};color:{BG};font-family:'Anton';font-size:40px;letter-spacing:2px;padding:20px 34px 16px;border-radius:999px}}
.close-follow{{position:absolute;bottom:104px;right:64px;font-weight:600;font-size:28px;color:rgba(255,255,255,.6)}}
"""

BOLT = (f'<svg viewBox="0 0 100 100" fill="none"><path d="M10 51.5 C 24 25.5, 76 25.5, 90 51.5 C 76 73.5, 24 73.5, 10 51.5 Z" fill="#0B0B10"/><circle cx="50" cy="50" r="15" fill="{ACCENT}"/><circle cx="50" cy="50" r="7" fill="#0B0B10"/></svg>')


def img_size(path):
    from PIL import Image as _I
    q = Path(path)
    if not q.is_absolute():
        q = CONTENT.parent / q
    with _I.open(q) as im:
        return im.size


def esc(s):
    return html.escape(s, quote=False)


def br(s):
    return esc(s).replace("\n", "<br>")


def topbar(d):
    return (f'<div class="top"><div class="logo"><div class="mark">{BOLT}</div>'
            f'<div class="brand">{esc(d["brand"])}</div></div><div class="date">{esc(d["date_label"])}</div></div>')


def frame(layers, d):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body><div class="slide">{layers}{topbar(d)}</div></body></html>')


def strips_html(photos, positions=None, height=880):
    """Cada tira usa o recorte mais seguro: retrato fica com o rosto no terço superior,
    paisagem centraliza. Nunca corta a testa nem o queixo."""
    cells = []
    for i, ph in enumerate(photos):
        w, h = img_size(ph)
        if positions and i < len(positions) and positions[i]:
            pos = positions[i]
        else:                              # 24/09: sem posição, o recorte segue o rosto
            import foco
            pos = foco.posicao(ph, 1080 // max(1, len(photos)), height, alvo_y=0.33,
                               padrao="50% 22%" if w / h < 1.0 else "50% 50%")
        cells.append(f'<div><img src="{data_uri(ph)}" style="object-position:{pos}"></div>')
    return f'<div class="strips" style="height:{height}px">{"".join(cells)}</div>'


def cover_html(d):
    c = d["cover"]
    photos = c.get("photos") or []
    layers = ""
    if photos:
        layers += strips_html(photos, c.get("photo_positions"), 800)
        layers += '<div class="fade" style="top:390px;height:470px"></div>'
        layers += '<div class="scrim"></div>'
    else:
        layers += '<div class="glow"></div><div class="grid"></div>'
    layers += f"""
<div class="cover-head" id="ch">{br(c['headline_before'])} <span class="accent">{br(c['headline_accent'])}</span> {br(c['headline_after'])}</div>
<div class="cover-sub" id="cs">{esc(c['subtitle'])}</div>
<div class="swipe">ARRASTE <span>→</span></div>
<div class="handle">{esc(d['handle'])}</div>"""
    if c.get("credits"):
        layers += f'<div class="credits">{esc(c["credits"])}</div>'
    return frame(layers, d)


def news_html(d, i, n):
    total = len(d["news"])
    layout = d.get("layout", "classico")
    ten = layout in ("10", "capa9")           # contador + CTA no último slide
    first = (i == 0) and layout == "10"       # pergunta da capa só quando não há capa separada
    last = (i == total - 1)
    dots = "".join(f'<i class="{"on" if k == i else ""}"></i>' for k in range(total))
    layers = ""
    if n.get("photo"):
        w, h = img_size(n["photo"])
        uri = data_uri(n["photo"])
        # 24/09: SEM BORDA também no carrossel ("até os carrosséis têm bordas nas imagens"): a foto SEMPRE preenche a
        # caixa de cima (1080x760). Acabou a foto inteira no meio com faixas desfocadas dos lados. Foto em pé: rosto no
        # terço de cima ("50% 20%"); foto deitada: "50% 45%"; "photo_position" no content.json ajusta.
        import foco                       # 24/09: sem posição no content.json, o recorte segue o ROSTO (nunca corta rosto)
        pos = n.get("photo_position") or foco.posicao(n["photo"], 1080, 760, alvo_y=0.40,
                                                       padrao="50% 20%" if w / h < 1.0 else "50% 45%")
        layers += f'<div class="photo"><img src="{uri}" style="object-position:{pos}"></div>'
        layers += '<div class="fade" style="top:340px;height:420px"></div>'
        layers += '<div class="scrim-tall"></div>' if (ten and first) else '<div class="scrim"></div>'
    else:
        layers += '<div class="glow"></div><div class="grid"></div>'
    if ten and first:
        c = d["cover"]
        layers += (f'<div class="capa-q">{br(c["headline_before"])} <span class="accent">{br(c["headline_accent"])}</span> '
                   f'{br(c["headline_after"]).replace("<br>", " ")}</div>')
    sstyle = ' style="bottom:150px"' if (ten and last) else ''
    layers += f"""
<div class="content" id="content">
  <div class="row"><div class="num">{i+1:02d}</div><div class="tag">{esc(n['tag'])}</div></div>
  <div class="head" id="head">{esc(n['headline'])}</div>
  <div class="body" id="body">{esc(n['body'])}</div>
</div>
<div class="source"{sstyle}>Fonte: <b>{esc(n['source'])}</b></div>"""
    if ten:
        if first:
            layers += '<div class="swipe-r">ARRASTE →</div>'
        else:
            cstyle = ' style="bottom:144px"' if last else ''
            layers += f'<div class="counter"{cstyle}><b>{i+1:02d}</b>/{total}</div>'
    else:
        layers += f'<div class="dots">{dots}</div>'
    if n.get("photo_credit"):
        pstyle = ' style="bottom:112px"' if (ten and last) else ''
        layers += f'<div class="pcredit"{pstyle}>{esc(n["photo_credit"])}</div>'
    if ten and last:
        layers += f'<div class="cta-band">{esc(d.get("cta", "Antes de piscar: salve e compartilhe"))} <span>{esc(d["handle"])}</span></div>'
    return frame(layers, d)


def closing_html(d):
    c = d["closing"]
    layers = ""
    if c.get("photos"):
        layers += strips_html(c["photos"], None, 1440) + '<div class="dim"></div>'
        layers += '<div class="fade" style="top:0;height:1440px"></div>'
    else:
        layers += '<div class="glow"></div><div class="grid"></div>'
    layers += f"""
<div class="close-title">{esc(c['title_before'])} <span class="accent">{esc(c['title_accent'])}</span></div>
<div class="close-l1">{esc(c['line1'])}</div>
<div class="close-l2">{esc(c['line2'])}</div>
<div class="close-q">{esc(c['question'])}</div>
<div class="close-handle">{esc(d['handle'])}</div>
<div class="close-follow">Siga para não perder</div>"""
    return frame(layers, d)


FIT_JS = """
() => {
  const ch = document.getElementById('ch'); const cs = document.getElementById('cs');
  if (ch && cs) {
    let size = 118;
    while (ch.getBoundingClientRect().bottom > 1160 && size > 80) { size -= 4; ch.style.fontSize = size + 'px'; }
    cs.style.top = (ch.getBoundingClientRect().bottom + 30) + 'px';
    return {cover: size, bottom: cs.getBoundingClientRect().bottom};
  }
  const box = document.getElementById('content'); const head = document.getElementById('head'); const body = document.getElementById('body');
  const q = document.querySelector('.capa-q'); if (q && box) { const b = q.getBoundingClientRect().bottom; if (b + 40 > 580) box.style.top = (b + 40) + 'px'; }
  if (document.querySelector('.cta-band') && box) { box.style.bottom = '240px'; }
  if (box && head && body) {
    let hs = 88, bs = 36, guard = 0;
    const overflow = () => box.scrollHeight > box.clientHeight + 1;
    while (overflow() && guard++ < 60) {
      if (hs > 70) { hs -= 3; head.style.fontSize = hs + 'px'; }
      else if (bs > 28) { bs -= 1; body.style.fontSize = bs + 'px'; }
      else break;
    }
    return {overflow: overflow(), hs, bs};
  }
  return {};
}
"""


def confere(d):
    """24/09 ("faça direito, tudo"): notícia repetida e foto pequena demais, avisadas ANTES de gerar."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import nao_repete as NR, boas_praticas as BP
    NR.avisa([n["headline"] for n in d.get("news", [])])
    import foto_repete as FR          # 24/09: foto que já saiu trava (cobrança dele no carrossel do meio-dia)
    FR.trava(CONTENT)
    fotos = (d.get("cover") or {}).get("photos") or []
    for k, ph in enumerate(fotos, 1):
        for caixa, nome in (((1080 // max(1, len(fotos)), 800), "capa"), ((1080 // max(1, len(fotos)), 1920), "story 9:16")):
            a = BP.aviso_foto(CONTENT.parent / ph if not Path(ph).is_absolute() else ph, *caixa, rotulo=f"{nome}, foto {k}")
            if a:
                print(a)
    for i, n in enumerate(d.get("news", []), 1):
        if not n.get("photo"):
            print(f"AVISO notícia {i}: sem foto (o carrossel fica só com texto nesse cartão)")
            continue
        p = CONTENT.parent / n["photo"] if not Path(n["photo"]).is_absolute() else Path(n["photo"])
        a = BP.aviso_foto(p, 1080, 760, rotulo=f"notícia {i}")
        if a:
            print(a)


def main():
    d = json.loads(CONTENT.read_text(encoding="utf-8"))
    layout = d.get("layout", "classico")
    confere(d)
    slides = [] if layout == "10" else [("capa", cover_html(d))]
    for i, n in enumerate(d["news"]):
        slides.append((f"noticia{i+1}", news_html(d, i, n)))
    if layout == "classico":
        slides.append(("fechamento", closing_html(d)))

    report = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1440}, device_scale_factor=1)
        for idx, (name, markup) in enumerate(slides, 1):
            page.set_content(markup, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(200)
            fit = page.evaluate(FIT_JS)
            page.wait_for_timeout(60)
            png = OUT / f"slide_{idx:02d}.png"
            page.screenshot(path=str(png), full_page=False)
            Image.open(png).convert("RGB").save(OUT / f"slide_{idx:02d}.jpg", "JPEG", quality=92, optimize=True)
            png.unlink()
            report.append((idx, name, fit))
        browser.close()

    thumbs = [Image.open(OUT / f"slide_{i:02d}.jpg") for i in range(1, len(slides) + 1)]
    tw, th = 360, 450
    cols = min(4, len(thumbs)); rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 16, rows * th + (rows + 1) * 16), "#1a1a22")
    for k, t in enumerate(thumbs):
        r, c = divmod(k, cols)
        sheet.paste(t.resize((tw, th)), (16 + c * (tw + 16), 16 + r * (th + 16)))
    sheet.save(OUT / "preview.jpg", "JPEG", quality=88)
    (OUT / "caption.txt").write_text(d["caption"], encoding="utf-8")
    (OUT / "content.json").write_text(CONTENT.read_text(encoding="utf-8"), encoding="utf-8")   # 23/09: story nativo 9:16
    for r in report:
        print(r)
    print(f"OK: {len(slides)} slides em {OUT}")


if __name__ == "__main__":
    main()
