#!/usr/bin/env python3
"""Gera o Reels vertical (1080x1920) do Pisca a partir de content.json + trilha.

Uso: python3 reels.py [content.json] [saida.mp4]
Renderiza cada cartao em 1620x2880 (supersample 1.5x) e monta com ffmpeg:
zoom lento + crossfade + trilha embutida. Saida: H.264/AAC, 9:16.
"""
import json, sys, os, html, base64, mimetypes, subprocess, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

BASE = Path(__file__).resolve().parent
CONTENT = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "content.json"
OUTMP4 = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE / "reels.mp4"
FRAMES = BASE / "reels_frames"
import shutil as _sh
if FRAMES.exists(): _sh.rmtree(FRAMES)
FRAMES.mkdir(parents=True, exist_ok=True)

# --- trilha: tres faixas, uma diferente a cada Reels -------------------------
# O Jose Miguel pediu que dois Reels seguidos nunca saiam com a mesma musica.
# A escolha nao guarda estado nenhum (o container das tarefas agendadas nasce
# limpo todo dia): sai da data + qual edicao e. Como a conta anda de 1 em 1,
# dois Reels seguidos caem sempre em faixas diferentes, inclusive virando o dia.
# Da para forcar com TRILHA_NOME=CORRIDA.
TRILHAS = ["PULSO", "CORRIDA", "NOTURNO"]
TRILHA = None   # definida em main(), depois de ler o date_label

def _escolhe_trilha(rotulo=""):
    forcada = os.environ.get("TRILHA_NOME", "").upper()
    if forcada in TRILHAS:
        return forcada
    import datetime
    # hora de Brasilia (UTC-3), para o Reels das 21h nao pular de dia
    hoje = (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()
    r = (rotulo or os.environ.get("EDICAO", "")).upper()
    ed = 0 if ("MEIO-DIA" in r or "MEIODIA" in r or "MANHA" in r or "MANHÃ" in r) else 1
    return TRILHAS[(hoje.toordinal() * 2 + ed) % len(TRILHAS)]
MAX_CARDS = int(os.environ.get("MAX_CARDS", "8"))
DUR_CARD = float(os.environ.get("DUR_CARD", "3.4"))   # 21/09: 2.4 pedia 21 char/s, acima do que da pra ler
DUR_INTRO = 0.0   # v2: sem capa institucional
DUR_OUTRO = 2.0
XF = 0.25                      # crossfade
W, H = 1080, 1920
SCALE = 1.5

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


def img_size(path):
    p = Path(path)
    if not p.is_absolute():
        p = CONTENT.parent / p
    with Image.open(p) as im:
        return im.size


def font_face(family, path, weight=400):
    b64 = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return (f"@font-face{{font-family:'{family}';src:url('data:font/woff2;base64,{b64}') format('woff2');"
            f"font-weight:{weight};font-style:normal;font-display:block;}}")


FONTS = "\n".join(
    [font_face("Anton", FONT_DIR / "anton/files/anton-latin-400-normal.woff2"),
     font_face("Anton", FONT_DIR / "anton/files/anton-latin-ext-400-normal.woff2")]
    + [font_face("Inter", FONT_DIR / f"inter/files/inter-{sub}-{w}-normal.woff2", w)
       for sub in ("latin", "latin-ext") for w in (500, 600, 700, 800)]
)

EYE = (f'<svg viewBox="0 0 100 100" fill="none">'
       f'<path d="M10 51.5 C 24 25.5, 76 25.5, 90 51.5 C 76 73.5, 24 73.5, 10 51.5 Z" fill="{BG}"/>'
       f'<circle cx="50" cy="50" r="15" fill="{ACCENT}"/>'
       f'<circle cx="50" cy="50" r="7" fill="{BG}"/></svg>')

CSS = f"""
{FONTS}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{BG};color:#fff;
  font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}}
.card{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{BG}}}
.accent{{color:{ACCENT}}}

/* O Reels aparece em dois lugares, com cortes DIFERENTES:
   - player de tela cheia: corta 108px de cada lado; interface cobre y<192 e y>1296
   - feed: mostra a largura toda, mas corta y<248 e y>1286
   A zona que sobrevive aos dois: x 118..830, y 300..1280. Tudo que e texto vive ali. */
.safe{{position:absolute;left:118px;width:712px;z-index:8}}

/* fundo da tela inteira, borrado (o corte nao importa, esta fora de foco) */
.bgfill{{position:absolute;inset:0;overflow:hidden;background:#101016}}
.bgfill img{{width:100%;height:100%;object-fit:cover;
  filter:blur(52px) brightness(.34) saturate(1.2);transform:scale(1.4)}}

/* faixa da foto: largura TOTAL, sem moldura flutuando */
.shot{{position:absolute;left:0;top:300px;width:{W}px;height:600px;overflow:hidden;z-index:3}}
.shot .fill{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  filter:blur(30px) brightness(.66) saturate(1.3);transform:scale(1.35)}}
.shot .real{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}}
.shot .top-scrim{{position:absolute;left:0;top:0;width:100%;height:190px;
  background:linear-gradient(to bottom,rgba(11,11,16,.88) 0%,rgba(11,11,16,.35) 58%,rgba(11,11,16,0) 100%)}}
.shot .bot-scrim{{position:absolute;left:0;bottom:0;width:100%;height:150px;
  background:linear-gradient(to top,rgba(11,11,16,.92) 0%,rgba(11,11,16,0) 100%)}}
.under{{position:absolute;left:0;top:880px;width:{W}px;height:180px;z-index:4;
  background:linear-gradient(to bottom,rgba(11,11,16,.55) 0%,{BG} 62%)}}

/* marca, por cima da faixa */
.top{{top:330px;display:flex;align-items:center;gap:16px;z-index:9}}
.mark{{width:50px;height:50px;border-radius:14px;background:{ACCENT};
  display:flex;align-items:center;justify-content:center;flex:none}}
.mark svg{{width:37px;height:37px}}
.wordmark{{font-family:'Anton';font-size:36px;letter-spacing:3px;line-height:1;
  text-shadow:0 2px 12px rgba(0,0,0,.8)}}
.when{{margin-left:auto;font-size:21px;font-weight:700;letter-spacing:2px;color:#CFCFD8;
  text-shadow:0 2px 10px rgba(0,0,0,.8)}}
.bars{{top:852px;display:flex;gap:6px;z-index:9}}
.bars i{{flex:1;height:5px;border-radius:3px;background:rgba(255,255,255,.28)}}
.bars i.on{{background:{ACCENT}}}

/* texto */
.body{{top:940px}}
.meta{{display:flex;align-items:center;gap:17px;margin-bottom:20px}}
.num{{font-family:'Anton';font-size:58px;line-height:.8;color:{ACCENT}}}
.chip{{font-size:22px;font-weight:800;letter-spacing:2.4px;padding:9px 18px;border-radius:9px;
  background:rgba({ACCENT_RGB},.18);color:{ACCENT};border:2px solid rgba({ACCENT_RGB},.45)}}
h1{{font-family:'Anton';font-weight:400;font-size:66px;line-height:1.12;letter-spacing:.3px;
  text-transform:uppercase;max-width:712px;overflow-wrap:break-word;
  text-shadow:0 3px 16px rgba(0,0,0,.7)}}
h1.sm{{font-size:58px}}
h1.xs{{font-size:51px}}
.src{{margin-top:20px;font-size:23px;font-weight:700;color:#A6A6B2;max-width:712px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.src span{{font-weight:500;color:#6C6C78;font-size:18px}}

/* abertura e fechamento: tambem dentro da zona dos dois cortes */
.hero{{top:320px;height:960px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;text-align:center;z-index:9}}
.bigmark{{width:162px;height:162px;border-radius:40px;background:{ACCENT};display:flex;
  align-items:center;justify-content:center;margin-bottom:38px}}
.bigmark svg{{width:119px;height:119px}}
.name{{font-family:'Anton';font-size:104px;letter-spacing:8px;line-height:1}}
.q{{font-family:'Anton';font-size:64px;line-height:1.12;text-transform:uppercase;margin-top:32px}}
.sub{{margin-top:24px;font-size:29px;font-weight:600;color:#C2C2CC}}
.date{{margin-top:16px;font-size:22px;font-weight:800;letter-spacing:2.5px;color:{ACCENT}}}
.collage{{position:absolute;inset:0;display:flex;gap:6px;opacity:.5;filter:blur(3px) saturate(1.1)}}
.collage div{{flex:1;overflow:hidden}}
.collage img{{width:100%;height:100%;object-fit:cover}}
.veil{{position:absolute;inset:0;z-index:2;
  background:radial-gradient(ellipse 72% 42% at 50% 41%,rgba(11,11,16,.5) 0%,rgba(11,11,16,.97) 74%)}}
.big{{font-family:'Anton';font-size:84px;line-height:1.12;text-transform:uppercase}}
.line{{width:160px;height:8px;background:{ACCENT};border-radius:5px;margin:34px auto}}
.sub2{{font-size:30px;font-weight:600;color:#C2C2CC;line-height:1.42}}

/* v2: o bloco de texto entra deslizando. Tres estados congelados; o ffmpeg
   faz a passagem entre eles — movimento de verdade sem custo de render. */
.body.st0{{transform:translateY(74px);opacity:.14}}
.body.st1{{transform:translateY(30px);opacity:.70}}
.body.st2{{transform:translateY(0);opacity:1}}
/* v2: a promessa, so no primeiro cartao — o motivo de ficar ate o fim */
.promessa{{margin-top:22px;font-family:'Anton';font-size:30px;letter-spacing:1.6px;
  color:{ACCENT};text-transform:uppercase}}
.h2{{margin-top:40px;font-family:'Anton';font-size:54px;letter-spacing:2px;color:{ACCENT}}}
/* v5 (23/09) — sem faixa vazia embaixo: foto de 300 a 1120, texto de baixo para cima até 1520 */
.shot{{height:820px}}
.under{{top:1040px;height:880px;
  background:linear-gradient(to bottom,rgba(11,11,16,.55) 0px,rgba(11,11,16,.92) 110px,rgba(11,11,16,.90) 505px,
  rgba(11,11,16,.62) 680px,rgba(11,11,16,.50) 100%)}}
/* 23/09 tela cheia: foto em pé ocupa tudo; o degradê escurece só atrás do texto */
.bgfill img{{filter:blur(46px) brightness(.58) saturate(1.2)}}
.bgfill.cheia img{{filter:none;transform:none}}
.under.cheia{{top:0;height:1920px;background:linear-gradient(to bottom,rgba(11,11,16,.55) 0px,rgba(11,11,16,.05) 380px,
  rgba(11,11,16,0) 700px,rgba(11,11,16,.72) 1010px,rgba(11,11,16,.92) 1190px,rgba(11,11,16,.90) 1545px,
  rgba(11,11,16,.62) 1720px,rgba(11,11,16,.50) 1920px)}}
.body{{top:auto;bottom:{1920 - 1520}px}}
.bars5{{display:flex;gap:6px;margin-bottom:24px}}
.bars5 i{{flex:1;height:5px;border-radius:3px;background:rgba(255,255,255,.28)}}
.bars5 i.on{{background:{ACCENT}}}
.hero{{top:300px;height:1220px}}
"""


MAX_PERDA = 0.18   # so preenche a caixa se o corte comer menos que isto


def esc(s):
    return html.escape(s or "")


def whole_photo(path, pos=None):
    """24/09 — TELA CHEIA SEMPRE ("em cima e embaixo", SEM BORDA — o Instagram deixa menos descobertos os Reels
    "with borders around them"). Foto em pé: rosto no terço de cima ("50% 30%"). Foto deitada: recorte vertical no
    ponto de "photo_position" (padrão: centro) — conferir na folha de contato. Objeto deitado que não sobrevive ao
    recorte: compor antes a versão vertical (compor_vertical.py) e usar o arquivo *_v.jpg."""
    uri = data_uri(path)
    try:
        w, h = img_size(path)
    except Exception:
        w, h = 1, 1
    padrao = "50% 30%" if w / h <= 0.82 else "50% 45%"
    if not pos:                            # 24/09: o recorte segue o rosto (acima do texto)
        import foco
        pos = foco.posicao(Path(path) if Path(path).is_absolute() else CONTENT.parent / path, W, H, alvo_y=0.28,
                           padrao=padrao)
    return (f'<div class="bgfill cheia"><img src="{uri}" style="object-position:{pos}"></div>'
            f'<div class="under cheia"></div>')


def ficha_cartoes(news):
    """como cada foto entra no vídeo, para a trava de boas práticas (boas_praticas.py)"""
    import boas_praticas as BP
    cart = []
    for i, n in enumerate(news, 1):
        foto = n.get("photo")
        p = Path(foto) if Path(foto).is_absolute() else CONTENT.parent / foto
        w, h = img_size(foto)
        modo = "composta" if p.stem.endswith("_v") else "cheia"
        aviso = BP.aviso_foto(p, W, H, 1.012, f"notícia {i}")
        import foco
        if not aviso and w / h > 0.82 and not n.get("photo_position") and modo == "cheia" and not foco.rostos(p):
            aviso = (f"AVISO notícia {i}: foto deitada ({w}x{h}) sem photo_position — conferir o recorte na folha "
                     f"(rosto/objeto inteiro na tela?)")
        cart.append({"cartao": f"notícia {i}", "foto": str(foto), "modo": modo,
                     "escala": round(BP.escala(p, W, H, 1.012), 2), "aviso": aviso})
    return cart


def page(inner):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body>{inner}</body></html>')


def card_news(n, idx, total, when, st=2, promessa=""):
    """st = estado de entrada do bloco de texto (0, 1 ou 2). promessa so no cartao 1."""
    hl = esc(n["headline"]).upper()
    cls = "" if len(hl) <= 38 else ("sm" if len(hl) <= 54 else "xs")
    bars = "".join(f'<i class="{"on" if i <= idx else ""}"></i>' for i in range(1, total + 1))
    prom = f'<div class="promessa">{esc(promessa)}</div>' if promessa else ""
    return page(f"""<div class="card">
  {whole_photo(n["photo"], n.get("photo_position")) if n.get("photo") else ""}
  <div class="safe top"><div class="mark">{EYE}</div><div class="wordmark">PISCA</div>
    <div class="when">{esc(when)}</div></div>
  <div class="safe body st{st}">
    <div class="bars5">{bars}</div>
    <div class="meta"><div class="num">{idx:02d}</div><div class="chip">{esc(n["tag"])}</div></div>
    <h1 class="{cls}">{hl}</h1>
    <div class="src">Fonte: {esc(n["source"])}<span>&nbsp;&nbsp;·&nbsp;&nbsp;{esc(n.get("photo_credit",""))}</span></div>
    {prom}
  </div>
</div>""")


def card_intro(c, cover, when, n_news):
    ph = cover.get("photos", [])[:3]
    col = "".join(f'<div><img src="{data_uri(p)}"></div>' for p in ph)
    q = (cover.get("headline_before", "") + " " + cover.get("headline_accent", "")
         + " " + cover.get("headline_after", "")).replace("\n", " ").strip()
    return page(f'''<div class="card">
  <div class="collage">{col}</div><div class="veil"></div>
  <div class="safe hero">
    <div class="bigmark">{EYE}</div>
    <div class="name">PISCA</div>
    <div class="q">{esc(q)}</div>
    <div class="sub">{n_news} notícias em {int(round(n_news*DUR_CARD + DUR_INTRO + DUR_OUTRO))} segundos.</div>
    <div class="date">{esc(when)}</div>
  </div>
</div>''')


def card_outro(cta):
    # o cartao final usa o cta do content.json. Antes vinha uma frase fixa
    # ("salve para ler depois e mande para quem precisa ficar por dentro"),
    # que e exatamente a formula generica proibida na regra da legenda.
    import html as _html
    txt = (cta or "Mandou pra alguem? E assim que cresce.").strip()
    meio = len(txt) // 2
    corte = txt.rfind(" ", 0, meio + 8)
    if corte < 8:
        corte = txt.find(" ", meio)
    if corte and corte > 0:
        linhas = _html.escape(txt[:corte]) + "<br>" + _html.escape(txt[corte + 1:])
    else:
        linhas = _html.escape(txt)
    return page(f'''<div class="card">
  <div class="safe hero" style="left:{(W - 712) // 2}px">
    <div class="bigmark">{EYE}</div>
    <div class="big">Antes de<br><span class="accent">piscar:</span></div>
    <div class="line"></div>
    <div class="sub2">{linhas}</div>
    <div class="h2">@pisca.news</div>
  </div>
</div>''')


def shoot(pw, htmls):
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
    paths = []
    for i, doc in enumerate(htmls, 1):
        pg.set_content(doc, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(200)
        p = FRAMES / f"card_{i:02d}.png"
        pg.screenshot(path=str(p))
        paths.append(p)
        print("  cartao", i, "ok")
    b.close()
    return paths


# ZOOM do quadro inteiro = 0, e isso e proposital.
# O zoompan amplia a partir do centro, entao ele empurra o TEXTO para fora:
# a 1.055 (valor da v1) a manchete saia de x=118 para x=95 e entrava debaixo da
# interface do player; o rodape passava de y=1280 para 1298 e sumia no feed.
# O conferidor nunca pegou isso porque olha o cartao ANTES do zoom.
# O movimento da v2 vem do texto que entra, da barra de progresso e do corte seco.
ZOOM = 0.0
XF_KF = 0.10       # passagem entre os estados do mesmo cartao
XF_CARD = 0.16     # passagem entre cartoes (v2: corte mais seco)
# v5 (23/09): o José Miguel viu "muito espaço vazio embaixo" (o texto acabava em 1256 e 35% da
# tela ficava vazia). Agora o texto encosta em TEXTO_FIM=1520 (medida oficial: 350px livres
# embaixo) e a barra de progresso vem logo abaixo.
TEXTO_FIM = 1520
BAR_X, BAR_Y, BAR_W, BAR_H = 118, 1534, 712, 8   # barra de progresso


def _zp(i, d, z0, z1):
    """zoompan de um pedaco, indo de z0 a z1."""
    fr = max(2, int(round(d * 30)))
    return (f"[{i}:v]zoompan=z='{z0:.4f}+({z1 - z0:.4f})*on/{fr}':d={fr}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,"
            f"setsar=1,format=yuv420p[v{i}]")


def build_video(pecas, out):
    """pecas = lista de (png, duracao, xfade_para_a_proxima, z0, z1).
    Monta a cadeia e desenha por cima uma barra de progresso que anda o video inteiro."""
    ins, filt = [], []
    for i, (png, d, _xf, z0, z1) in enumerate(pecas):
        ins += ["-loop", "1", "-t", f"{d:.3f}", "-i", str(png)]
        filt.append(_zp(i, d, z0, z1))

    acc = pecas[0][1]
    cur = "v0"
    for i in range(1, len(pecas)):
        xf = pecas[i - 1][2]
        off = acc - xf
        nxt = f"x{i}"
        filt.append(f"[{cur}][v{i}]xfade=transition=fade:duration={xf}:offset={off:.3f}[{nxt}]")
        acc = acc + pecas[i][1] - xf
        cur = nxt
    total = acc

    # Barra de progresso: anda o video inteiro, dentro da zona segura dos dois cortes.
    # O drawbox NAO serve aqui — ele calcula a largura uma vez so e a barra sai cheia.
    # Entao a barra e uma faixa solida cujo ALFA e recortado por quadro pelo geq.
    ibar = len(pecas) + 1
    filt.append(f"[{ibar}:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                f"a='if(lte(X,{BAR_W}*T/{total:.3f}),255,0)'[bar]")
    t_fecho = total - pecas[-1][1]          # 24/09: a barra some no cartão final (centralizado), como na matéria
    filt.append(f"[{cur}][bar]overlay=x={BAR_X}:y={BAR_Y}:format=auto:enable='lt(t,{t_fecho:.3f})'[vp]")

    filt.append(f"[{len(pecas)}:a]atrim=0:{total:.3f},asetpts=N/SR/TB,"
                f"afade=t=in:st=0:d={globals().get('FADE_IN', 0.4)},afade=t=out:st={max(0, total - 1.2):.3f}:d=1.2[a]")
    cmd = (["ffmpeg", "-y"] + ins
           + ["-stream_loop", "-1", "-i", str(TRILHA),
              "-f", "lavfi", "-i",
              f"color=c=0x{ACCENT.lstrip('#')}:s={BAR_W}x{BAR_H}:d={total:.3f}:r=30",
              "-filter_complex", ";".join(filt),
              "-map", "[vp]", "-map", "[a]",
              "-c:v", "libx264", "-preset", "medium", "-crf", "19",
              "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
              "-r", "30", "-g", "60", "-movflags", "+faststart",
              "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
              "-t", f"{total:.3f}", str(out)])
    print("  ffmpeg: montando", f"{total:.1f}s")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    return total


def main():
    global TRILHA
    d = json.loads(CONTENT.read_text(encoding="utf-8"))
    news = [n for n in d["news"] if n.get("photo")][:MAX_CARDS]
    when = d.get("date_label", "")
    n = len(news)
    sem_foto = [x["headline"] for x in d["news"] if not x.get("photo")]
    if sem_foto:
        print(f"AVISO boas práticas: {len(sem_foto)} notícia(s) sem foto ficam FORA do Reels: {sem_foto}")
    import nao_repete as NR                 # 24/09: regra de não repetir, conferida já na produção
    NR.avisa([x["headline"] for x in news])
    import foto_repete as FR                # 24/09: foto que já saiu trava
    FR.trava(CONTENT)
    cartoes = ficha_cartoes(news)

    # 23/09: padrao IMPACTO (trilha_impacto.py) — pancada em cada troca de notícia, feita sob medida.
    # TRILHA_NOME=PULSO|CORRIDA|NOTURNO (ou TRILHA=arquivo) volta para as trilhas fixas.
    escolha = (os.environ.get("TRILHA_NOME") or ("" if os.environ.get("TRILHA") else "IMPACTO")).upper()
    impacto = escolha == "IMPACTO"
    if not impacto:
        nome = _escolhe_trilha(when)
        TRILHA = Path(os.environ.get("TRILHA", str(BASE / f"Pisca_trilha_{nome}.mp3")))
        if not TRILHA.exists():
            subprocess.run([sys.executable, str(BASE / "trilha.py"), str(TRILHA), "40", nome], check=True)
        print(f"trilha: {nome}")
    else:
        print("trilha: IMPACTO (batida em cada notícia)")
    print(f"Reels v2: {n} noticias")

    # v2: SEM capa institucional. Abre na noticia mais forte, e a promessa
    # de ficar ate o fim viaja junto com ela, em vez de atrasar o comeco.
    total_est = n * DUR_CARD + DUR_OUTRO
    promessa = f"+ {n - 1} notícias em {int(round(total_est - DUR_CARD))} segundos" if n > 1 else ""

    htmls, meta = [], []
    for i, nw in enumerate(news, 1):
        pr = promessa if i == 1 else ""
        for st in (0, 1, 2):
            htmls.append(card_news(nw, i, n, when, st=st, promessa=pr))
            meta.append(("kf", i, st))
    htmls.append(card_outro(d.get("cta", "")))
    meta.append(("outro", 0, 0))

    with sync_playwright() as pw:
        paths = shoot(pw, htmls)

    # monta as pecas: 3 estados por cartao + o fechamento
    pecas = []
    k = 0
    for i in range(1, n + 1):
        ult = (i == n)
        dA, dB = 0.22, 0.20
        dC = DUR_CARD                      # contribui DUR_CARD - 0.22 na linha do tempo
        z_fim = 1.0 + ZOOM
        pecas.append((paths[k],     dA, XF_KF,   1.0,    1.006))
        pecas.append((paths[k + 1], dB, XF_KF,   1.006,  1.012))
        pecas.append((paths[k + 2], dC, XF_CARD, 1.012,  z_fim))
        k += 3
    pecas.append((paths[k], DUR_OUTRO, 0.0, 1.0, 1.03))

    if impacto:
        # inicio de cada peça na linha do tempo do xfade: t[i] = t[i-1] + d[i-1] - xf[i-1]
        ini = [0.0]
        for (_p, d_, xf_, _a, _b) in pecas[:-1]:
            ini.append(ini[-1] + d_ - xf_)
        total_t = ini[-1] + pecas[-1][1]
        cortes = [round(ini[3 * (i - 1)], 3) for i in range(1, n + 1)] + [round(ini[-1], 3)]
        import trilha_impacto as TI
        wav = OUTMP4.with_suffix(".impacto.wav")
        TI.grava(TI.arranjo(total_t, cortes, [0.0, round(ini[-1], 3)], round(ini[-1], 3)), str(wav))
        TRILHA = wav
        globals()["FADE_IN"] = 0.01
        print(f"trilha IMPACTO: {total_t:.1f}s, cortes {cortes}")
    total = build_video(pecas, OUTMP4)
    mb = OUTMP4.stat().st_size / 1e6
    print(f"OK {OUTMP4}  {total:.1f}s  {mb:.1f} MB")
    import boas_praticas as BP
    BP.grava_ficha(OUTMP4, "reels.py", CONTENT, cartoes,
                   {"fecho_centralizado": True, "trilha": "IMPACTO" if impacto else str(TRILHA), "duracao": round(total, 2)})


if __name__ == "__main__":
    main()
