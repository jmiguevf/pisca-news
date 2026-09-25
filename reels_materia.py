#!/usr/bin/env python3
"""Reels de MATERIA UNICA do Pisca — uma historia so, contada em ~22 segundos.

Uso: python3 reels_materia.py materia.json saida.mp4

Por que existe, separado do reels.py:
  o reels.py monta uma FILA de manchetes. Os numeros da conta (21/09) mostraram
  retencao de 16% — o espectador le a primeira, entende que e lista, e sai.
  Lista nao prende. Aqui a estrutura e de historia: gancho -> fato -> numero ->
  mecanismo -> o que muda pra voce -> ressalva -> pedido.

Reaproveita do reels.py toda a maquinaria ja validada: zona segura dos dois
cortes do Instagram, foto inteira sem corte, barra de progresso, trilha e
montagem no ffmpeg. NAO duplica esse conhecimento — importa.
"""
import json, sys, os, html
from pathlib import Path

BASE = Path(__file__).resolve().parent
MATERIA = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "materia.json"
OUTMP4 = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE / "reels_materia.mp4"

# o reels.py le sys.argv na importacao (CONTENT e OUTMP4) — aponto para os meus
# antes de importar, senao ele resolve as fotos a partir da pasta errada.
sys.argv = [sys.argv[0], str(MATERIA), str(OUTMP4)]
import reels as R
from playwright.sync_api import sync_playwright

# --- duracoes -----------------------------------------------------------------
# 22/09: os 3,4s vieram do Reels de LISTA, onde o cartao tinha so uma manchete
# de ~47 caracteres. Aqui o cartao tem titulo MAIS corpo de texto — o triplo de
# letra. Medido, exigia 48 a 52 caracteres por segundo, contra 15 a 20 que e a
# leitura confortavel. Por isso 5,5s no texto e corpo limitado a ~70 caracteres.
DUR = {"gancho": 3.4, "texto": 5.5, "numero": 4.0, "fecho": 2.6}
XF_KF, XF_CARD = R.XF_KF, R.XF_CARD

CSS_EXTRA = f"""
/* o gancho nao tem indice nem fonte: e uma frase so, do tamanho da tela */
h1.gancho{{font-size:78px;line-height:1.08}}
h1.gancho.sm{{font-size:66px}}
h1.gancho.xs{{font-size:58px}}
.kicker{{font-size:23px;font-weight:800;letter-spacing:3px;color:{R.ACCENT};
  text-transform:uppercase;margin-bottom:18px}}
/* titulo menor que o do carrossel: aqui o corpo do texto tambem pesa */
h1.mat{{font-size:52px;line-height:1.1}}
h1.mat.sm{{font-size:46px}}
.corpo{{margin-top:22px;font-size:29px;font-weight:500;line-height:1.42;color:#D6D6DE;
  max-width:712px;text-shadow:0 2px 12px rgba(0,0,0,.75)}}
/* o cartao de numero: o soco visual */
.numerao{{font-family:'Anton';font-size:168px;line-height:.92;color:{R.ACCENT};
  letter-spacing:-1px;text-shadow:0 4px 28px rgba(0,0,0,.8)}}
.numerao.sm{{font-size:132px}}
.numerao.xs{{font-size:104px}}
.numlegenda{{margin-top:26px;font-size:29px;font-weight:600;line-height:1.36;color:#E4E4EC}}
/* a ressalva tem cor propria: e o cartao que diz o que NAO se sabe */
.chip.ress{{background:rgba(255,255,255,.10);color:#D8D8E2;border-color:rgba(255,255,255,.28)}}
.promessa2{{margin-top:26px;font-family:'Anton';font-size:28px;letter-spacing:1.6px;
  color:{R.ACCENT};text-transform:uppercase}}
"""
CSS_V2 = f"""
/* v2 (22/09): no tamanho real, o corpo em 29px dava letra de bula no celular e a
   foto de notebook ocupava a maior area da tela. Num Reels feito de texto, o texto
   manda: a foto vira faixa curta no topo e a letra cresce ~45%. */
.shot.curto{{top:300px;height:340px}}
.under.curto{{top:600px;height:1320px;
  background:linear-gradient(to bottom,rgba(11,11,16,.55) 0%,#0B0B10 8%)}}
.bars.curto{{top:668px}}
.body.mat2{{top:722px}}
h1.mat{{font-size:64px;line-height:1.08}}
h1.mat.sm{{font-size:56px}}
.corpo{{margin-top:26px;font-size:42px;font-weight:600;line-height:1.28;color:#F4F4F8}}
h1.gancho{{font-size:88px;line-height:1.04}}
h1.gancho.sm{{font-size:76px}}
h1.gancho.xs{{font-size:66px}}
.kicker{{font-size:26px}}
.numerao{{font-size:250px;line-height:.9}}
.numerao.sm{{font-size:170px}}
.numerao.xs{{font-size:124px}}
.numlegenda{{font-size:40px;font-weight:600;line-height:1.28;color:#F4F4F8}}
/* faixa de diagrama: no lugar da foto, quando a foto nao explica nada */
.diag{{position:absolute;left:0;top:300px;width:{R.W}px;height:340px;z-index:3;
  background:linear-gradient(to bottom,#15151C 0%,#101016 100%)}}
.diag svg{{position:absolute;inset:0}}
/* na faixa curta a foto e so atmosfera: preenche a largura (cover) em vez de
   ficar pequena no meio com laterais borradas. So vale para a faixa curta — o
   carrossel e o Reels de lista continuam com a foto inteira, sem corte. */
.shot.curto .real{{object-fit:cover}}
/* v4 (22/09): o José Miguel cobrou imagem ("so desenhos?"). Dois layouts novos:
   CHEIA = foto na tela inteira (gancho); ALTA = faixa de 560px para foto que conta. */
.fotocheia{{position:absolute;inset:0;z-index:2;overflow:hidden;background:#101016}}
.fotocheia img{{width:100%;height:100%;object-fit:cover}}
.fotocheia .grad{{position:absolute;inset:0;background:linear-gradient(to bottom,
  rgba(11,11,16,.60) 0%,rgba(11,11,16,.05) 20%,rgba(11,11,16,0) 34%,
  rgba(11,11,16,.72) 45%,rgba(11,11,16,.94) 56%,#0B0B10 68%)}}
.shot.alta{{top:300px;height:560px}}
.shot.alta .real{{object-fit:cover}}
.under.alta{{top:800px;height:1120px;
  background:linear-gradient(to bottom,rgba(11,11,16,.55) 0%,#0B0B10 9%)}}
.bars.cheia{{top:822px}}
.bars.alta{{top:878px}}
.body.cheia{{top:860px}}
.body.alta{{top:914px}}
/* 22/09: foto clara (capsulas laranja) vazava pelo fundo desfocado e deixava o texto
   sobre laranja-escuro. Abaixo da faixa da foto agora e sempre escuro. */
/* credito da foto (CC BY exige): linha pequena na base da foto, na camada parada */
.credfoto{{font-size:18px;font-weight:600;color:rgba(255,255,255,.74);
  text-shadow:0 1px 6px rgba(0,0,0,.95);z-index:9;white-space:nowrap}}
.credfoto.cheia{{top:784px}}
.credfoto.alta{{top:832px}}
.credfoto.curto{{top:610px}}
.sub2{{font-size:38px;line-height:1.3;color:#E8E8EE}}
/* 22/09 noite: a data no canto some sobre foto clara (gorro colorido do golpe #2) */
.when{{text-shadow:0 1px 8px rgba(0,0,0,.95),0 0 2px rgba(0,0,0,.8)}}
"""
CSS_V5 = f"""
/* v5 (23/09): o José Miguel mandou print do perfil — "muito espaço vazio embaixo nos reels". O texto acabava em
   y~1256 e 35% da tela ficava preta. Agora o bloco de texto é ancorado EMBAIXO (termina em R.TEXTO_FIM=1520, deixando
   os 400 px de baixo para a interface) e a faixa da foto/desenho cresce até encostar nele (medido em _mede_topos). */
.safe.body.v5{{top:auto !important;bottom:{R.H - R.TEXTO_FIM}px}}
.v5bars{{display:flex;gap:6px;margin-bottom:24px}}
.v5bars i{{flex:1;height:5px;border-radius:3px;background:rgba(255,255,255,.28)}}
.v5bars i.on{{background:{R.ACCENT}}}
.v5cred{{font-size:18px;font-weight:600;color:rgba(255,255,255,.74);text-shadow:0 1px 6px rgba(0,0,0,.95);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:12px}}
.shot.v5{{top:300px}}
.shot.v5 .real{{object-fit:cover}}
.under.v5{{height:auto;bottom:0}}
.diag.v5{{top:300px}}
.diag.v5 svg{{inset:auto;left:0;top:50%;transform-origin:50% 50%}}
"""
R.CSS = R.CSS + CSS_EXTRA + CSS_V2 + CSS_V5


def esc(s):
    return html.escape(s or "")


def _tam(txt, cortes):
    """escolhe a classe de tamanho pelo comprimento do texto"""
    n = len(txt)
    for limite, cls in cortes:
        if n <= limite:
            return cls
    return cortes[-1][1]


DIAGRAMAS = {
    # Mac com o app -> (localizacao) -> iPhone. Desenho proprio, formas genericas,
    # sem logo de ninguem. Fica abaixo da linha da marca (y > 100 na faixa).
    "mac_iphone": f"""<svg viewBox="0 0 1080 340" width="1080" height="340">
  <rect x="176" y="112" width="232" height="140" rx="14" fill="none" stroke="#fff" stroke-width="8"/>
  <path d="M146 268 H438 L414 292 H170 Z" fill="none" stroke="#fff" stroke-width="8" stroke-linejoin="round"/>
  <circle cx="292" cy="182" r="30" fill="{R.ACCENT}"/>
  <circle cx="292" cy="182" r="12" fill="#101016"/>
  <line x1="470" y1="200" x2="712" y2="200" stroke="{R.ACCENT}" stroke-width="10" stroke-linecap="round"/>
  <path d="M690 172 L726 200 L690 228" fill="none" stroke="{R.ACCENT}" stroke-width="10"
        stroke-linecap="round" stroke-linejoin="round"/>
  <text x="592" y="166" fill="{R.ACCENT}" font-family="Inter" font-weight="800" font-size="31"
        text-anchor="middle" letter-spacing="1">localização</text>
  <rect x="770" y="100" width="128" height="222" rx="24" fill="none" stroke="#fff" stroke-width="8"/>
  <circle cx="834" cy="194" r="28" fill="{R.ACCENT}"/>
  <path d="M813 208 L834 246 L855 208 Z" fill="{R.ACCENT}"/>
  <circle cx="834" cy="194" r="11" fill="#101016"/>
</svg>""",
}



def _medico(cx, cy, esc=1.0, cor="#fff", fundo="#101016"):
    """Silhueta generica de medico (cabeca, jaleco, gola em V, estetoscopio)."""
    return (f'<g transform="translate({cx},{cy}) scale({esc})">'
            f'<circle cx="0" cy="-40" r="23" fill="{cor}"/>'
            f'<path d="M-46 42 Q-46 -8 0 -8 Q46 -8 46 42 Z" fill="{cor}"/>'
            f'<path d="M-11 -8 L0 15 L11 -8" fill="none" stroke="{fundo}" stroke-width="5"/>'
            f'<path d="M-24 0 Q-32 28 -10 31" fill="none" stroke="{fundo}" stroke-width="4.5"/>'
            f'<circle cx="-8" cy="32" r="5.5" fill="{fundo}"/></g>')


def _celular(x, y, w=140, h=226):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="none" stroke="#fff" stroke-width="8"/>'


def _seta(x1, x2, y, cor):
    return (f'<line x1="{x1}" y1="{y}" x2="{x2 - 8}" y2="{y}" stroke="{cor}" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M{x2 - 26} {y - 26} L{x2} {y} L{x2 - 26} {y + 26}" fill="none" stroke="{cor}" '
            f'stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')


def _grade(n, cols, x0, x1, y0, y1, cor):
    """n bonequinhos em grade — para o numero ter tamanho visivel."""
    linhas = -(-n // cols)
    dx = (x1 - x0) / cols
    dy = (y1 - y0) / linhas
    out = []
    for k in range(n):
        c, l = k % cols, k // cols
        cx, cy = x0 + dx * (c + .5), y0 + dy * (l + .5)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy - 7:.1f}" r="7.5" fill="{cor}"/>'
                   f'<path d="M{cx - 13:.1f} {cy + 14:.1f} Q{cx - 13:.1f} {cy + 1:.1f} {cx:.1f} {cy + 1:.1f} '
                   f'Q{cx + 13:.1f} {cy + 1:.1f} {cx + 13:.1f} {cy + 14:.1f} Z" fill="{cor}"/>')
    return "".join(out)


def _svg(corpo):
    return f'<svg viewBox="0 0 1080 340" width="1080" height="340">{corpo}</svg>'


A = R.ACCENT
# REGRA (22/09): com zoom de 7% a partir do centro, tudo que esta no desenho precisa
# ficar entre x=150 e x=930 — senao o zoom empurra para fora do corte lateral do
# player (108px de cada lado). O "nao achou" saiu cortado ("nao acho") por isso.
DIAGRAMAS.update({
    # gancho: um "medico" dentro do celular, com o selo IA
    "medico_video": _svg(
        _celular(470, 100) + _medico(540, 222, 1.0)
        + f'<path d="M500 128 L500 156 L524 142 Z" fill="{A}"/>'
        + f'<rect x="588" y="104" width="96" height="54" rx="14" fill="{A}"/>'
        + f'<text x="636" y="143" text-anchor="middle" font-family="Inter" font-weight="800" '
          f'font-size="34" fill="#101016">IA</text>'),
    # como funciona: IA -> "medico" no celular -> conselho falso
    "ia_medico": _svg(
        f'<rect x="150" y="136" width="130" height="130" rx="20" fill="none" stroke="#fff" stroke-width="8"/>'
        + "".join(f'<line x1="{x}" y1="120" x2="{x}" y2="136" stroke="#fff" stroke-width="7"/>'
                  f'<line x1="{x}" y1="266" x2="{x}" y2="282" stroke="#fff" stroke-width="7"/>' for x in (184, 215, 246))
        + f'<text x="215" y="220" text-anchor="middle" font-family="Inter" font-weight="800" font-size="50" fill="{A}">IA</text>'
        + _seta(300, 400, 201, A)
        + _celular(422, 96, 136, 222) + _medico(490, 214, 0.92)
        + _seta(580, 680, 201, A)
        + f'<path d="M708 128 H888 Q908 128 908 148 V240 Q908 260 888 260 H772 L744 292 L750 260 H728 '
          f'Q708 260 708 240 V148 Q708 128 728 128 Z" fill="none" stroke="#fff" stroke-width="8" stroke-linejoin="round"/>'
        + f'<text x="808" y="228" text-anchor="middle" font-family="Anton" font-size="92" fill="{A}">!</text>'),
    # o numero: 97 bonequinhos
    "grade_97": _svg(_grade(97, 20, 150, 930, 104, 326, A)),
    # proteger 1: busca pelo nome ou CRM -> existe / nao achou
    "busca_crm": _svg(
        f'<rect x="150" y="152" width="470" height="100" rx="50" fill="none" stroke="#fff" stroke-width="7"/>'
        + f'<circle cx="206" cy="196" r="21" fill="none" stroke="{A}" stroke-width="7"/>'
        + f'<line x1="221" y1="211" x2="238" y2="228" stroke="{A}" stroke-width="8" stroke-linecap="round"/>'
        + f'<text x="258" y="212" font-family="Inter" font-weight="600" font-size="29" fill="#D6D6DE">nome ou CRM do médico</text>'
        + f'<circle cx="690" cy="150" r="26" fill="{A}"/>'
        + f'<path d="M677 150 L687 161 L705 140" fill="none" stroke="#101016" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        + f'<text x="730" y="161" font-family="Inter" font-weight="800" font-size="31" fill="#fff">existe</text>'
        + f'<circle cx="690" cy="254" r="26" fill="#fff"/>'
        + f'<path d="M679 243 L701 265 M701 243 L679 265" stroke="#101016" stroke-width="7" stroke-linecap="round"/>'
        + f'<text x="730" y="265" font-family="Inter" font-weight="800" font-size="31" fill="#fff">não achou</text>'),
    # proteger 2: remedio de video (X) -> seu medico (V)
    "remedio_video": _svg(
        f'<rect x="160" y="112" width="310" height="190" rx="20" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<path d="M214 178 L214 236 L262 207 Z" fill="#fff"/>'
        + f'<g transform="translate(372 207) rotate(-32)"><rect x="-58" y="-24" width="116" height="48" rx="24" fill="#fff"/>'
          f'<rect x="0" y="-24" width="58" height="48" rx="0" fill="{A}"/><rect x="34" y="-24" width="24" height="48" rx="24" fill="{A}"/></g>'
        + f'<circle cx="468" cy="114" r="30" fill="#fff"/>'
        + f'<path d="M456 102 L480 126 M480 102 L456 126" stroke="#101016" stroke-width="7" stroke-linecap="round"/>'
        + _seta(520, 640, 207, A)
        + _medico(790, 222, 1.25)
        + f'<circle cx="880" cy="124" r="30" fill="{A}"/>'
        + f'<path d="M865 124 L876 136 L896 112" fill="none" stroke="#101016" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'),
})


# ---- golpe da vez #2 (voz clonada) ----------------------------------------
_ONDA = (26, 64, 104, 58, 124, 80, 38, 92, 48)   # mesma forma dos dois lados: a IA copia


def _onda(x0, cy, cor, passo=20, larg=11):
    return "".join(f'<rect x="{x0 + k * passo - larg / 2:.1f}" y="{cy - h / 2:.1f}" width="{larg}" height="{h}" '
                   f'rx="{larg / 2:.1f}" fill="{cor}"/>' for k, h in enumerate(_ONDA))


def _rotulo(x, y, txt, cor="#D6D6DE", tam=29):
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Inter" font-weight="800" '
            f'font-size="{tam}" fill="{cor}">{txt}</text>')


def _chip_ia(x, y, lado=130):
    cx = x + lado / 2
    pinos = "".join(f'<line x1="{px}" y1="{y - 16}" x2="{px}" y2="{y}" stroke="#fff" stroke-width="7"/>'
                    f'<line x1="{px}" y1="{y + lado}" x2="{px}" y2="{y + lado + 16}" stroke="#fff" stroke-width="7"/>'
                    for px in (cx - 31, cx, cx + 31))
    return (f'<rect x="{x}" y="{y}" width="{lado}" height="{lado}" rx="20" fill="none" stroke="#fff" stroke-width="8"/>'
            + pinos + f'<text x="{cx}" y="{y + 84}" text-anchor="middle" font-family="Inter" font-weight="800" '
            f'font-size="50" fill="{A}">IA</text>')


def _fone(cx, cy, cor="#fff", ang=0, esc=1.0):
    """monofone generico (telefone), desenhado com traco grosso"""
    return (f'<g transform="translate({cx},{cy}) rotate({ang}) scale({esc})">'
            f'<path d="M-26 -14 Q-30 -30 -18 -32 L-8 -33 Q-2 -33 -1 -26 L0 -16 Q0 -10 -6 -8 L-10 -6 '
            f'Q-6 6 6 10 L8 6 Q10 0 16 0 L26 1 Q33 2 33 8 L32 18 Q30 30 14 26 Q-20 16 -26 -14 Z" fill="{cor}"/></g>')


def _grade_pequena(n, cols, x0, x1, y0, y1, cor, s=0.72):
    """como _grade, mas com o bonequinho menor (para numeros de centenas)"""
    linhas = -(-n // cols)
    dx, dy = (x1 - x0) / cols, (y1 - y0) / linhas
    out = []
    for k in range(n):
        c, l = k % cols, k // cols
        cx, cy = x0 + dx * (c + .5), y0 + dy * (l + .5)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy - 7 * s:.1f}" r="{7.5 * s:.2f}" fill="{cor}"/>'
                   f'<path d="M{cx - 13 * s:.1f} {cy + 14 * s:.1f} Q{cx - 13 * s:.1f} {cy + 1 * s:.1f} {cx:.1f} {cy + 1 * s:.1f} '
                   f'Q{cx + 13 * s:.1f} {cy + 1 * s:.1f} {cx + 13 * s:.1f} {cy + 14 * s:.1f} Z" fill="{cor}"/>')
    return "".join(out)


DIAGRAMAS.update({
    # como funciona: voz real -> IA -> copia (mesma onda, na cor de destaque)
    "voz_copia": _svg(
        _onda(170, 190, "#fff") + _rotulo(250, 318, "voz real")
        + _seta(360, 452, 190, A)
        + _chip_ia(475, 125)
        + _seta(628, 720, 190, A)
        + _onda(750, 190, A) + _rotulo(830, 318, "cópia", A)),
    # o numero: 258 bonequinhos (registros de estelionato por hora, FBSP)
    "grade_258": _svg(_grade_pequena(258, 30, 150, 930, 104, 330, A)),
    # palavra-senha: o celular pergunta, a familia responde
    "palavra_senha": _svg(
        _celular(170, 100, 128, 214)
        + _onda(196, 206, "#fff", passo=10, larg=6)
        + f'<path d="M330 118 H590 Q610 118 610 138 V196 Q610 216 590 216 H370 L346 244 L352 216 H350 '
          f'Q330 216 330 196 V138 Q330 118 350 118 Z" fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round"/>'
        + _rotulo(470, 180, "qual é a palavra?", "#fff", 29)
        + f'<rect x="640" y="196" width="280" height="96" rx="48" fill="{A}"/>'
        + f'<circle cx="690" cy="244" r="17" fill="none" stroke="#101016" stroke-width="7"/>'
        + f'<line x1="706" y1="244" x2="752" y2="244" stroke="#101016" stroke-width="7" stroke-linecap="round"/>'
        + f'<line x1="738" y1="244" x2="738" y2="260" stroke="#101016" stroke-width="7" stroke-linecap="round"/>'
        + f'<text x="768" y="256" font-family="Inter" font-weight="800" font-size="31" fill="#101016">secreta</text>'),
    # desligue -> ligue voce para o numero salvo
    "desliga_liga": _svg(
        _celular(180, 100, 128, 214) + _rotulo(244, 170, "?", "#fff", 60)
        + f'<circle cx="244" cy="258" r="30" fill="#E5484D"/>' + _fone(244, 258, "#fff", 135, 0.62)
        + _seta(360, 452, 207, A)
        + _celular(500, 100, 128, 214)
        + f'<circle cx="564" cy="160" r="26" fill="#fff"/>'
        + f'<path d="M536 214 Q536 188 564 188 Q592 188 592 214 Z" fill="#fff"/>'
        + f'<circle cx="564" cy="262" r="30" fill="#2EB67D"/>' + _fone(564, 262, "#fff", 0, 0.62)
        + _rotulo(790, 190, "ligue você", "#fff", 34)
        + _rotulo(790, 236, "para o número", "#D6D6DE", 29)
        + _rotulo(790, 274, "já salvo", "#D6D6DE", 29)),
    # caiu? contestar no app -> bloqueio do que ainda estiver na conta
    "med_bloqueio": _svg(
        _celular(170, 100, 128, 214)
        + f'<rect x="186" y="236" width="96" height="44" rx="22" fill="{A}"/>'
        + f'<text x="234" y="266" text-anchor="middle" font-family="Inter" font-weight="800" font-size="22" fill="#101016">MED</text>'
        + f'<text x="234" y="176" text-anchor="middle" font-family="Inter" font-weight="800" font-size="46" fill="#fff">Pix</text>'
        + _seta(340, 432, 207, A)
        + f'<rect x="470" y="170" width="120" height="98" rx="14" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<path d="M494 170 V142 Q494 110 530 110 Q566 110 566 142 V170" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<circle cx="530" cy="212" r="11" fill="{A}"/><rect x="525" y="216" width="10" height="26" rx="4" fill="{A}"/>'
        + _rotulo(775, 190, "o banco bloqueia", "#fff", 31)
        + _rotulo(775, 232, "o que ainda", "#fff", 31)
        + _rotulo(775, 274, "encontrar", "#fff", 31)),
})

# ---- golpe da vez #3 (falso advogado / juiz feito com IA) -------------------
def _pessoa(cx, cy, esc=1.0, cor="#fff", gravata=None, fundo="#101016"):
    """pessoa generica (cabeca e ombros); com gravata = advogado"""
    g = (f'<g transform="translate({cx},{cy}) scale({esc})">'
         f'<circle cx="0" cy="-40" r="23" fill="{cor}"/>'
         f'<path d="M-46 42 Q-46 -8 0 -8 Q46 -8 46 42 Z" fill="{cor}"/>')
    if gravata:
        g += (f'<path d="M-10 -8 L0 3 L10 -8 Z" fill="{fundo}"/>'
              f'<path d="M0 1 L-7 9 L0 38 L7 9 Z" fill="{gravata}"/>')
    return g + '</g>'


def _juiz(cx, cy, esc=1.0):
    """silhueta de juiz: toga larga, gola em V e as pregas"""
    return (f'<g transform="translate({cx},{cy}) scale({esc})">'
            f'<circle cx="0" cy="-40" r="23" fill="#fff"/>'
            f'<path d="M-54 42 Q-54 -8 0 -8 Q54 -8 54 42 Z" fill="#fff"/>'
            f'<path d="M-15 -8 L0 20 L15 -8" fill="none" stroke="#101016" stroke-width="6"/>'
            f'<line x1="-27" y1="8" x2="-31" y2="42" stroke="#101016" stroke-width="4"/>'
            f'<line x1="27" y1="8" x2="31" y2="42" stroke="#101016" stroke-width="4"/></g>')


DIAGRAMAS.update({
    # como funciona: dados reais do processo -> "advogado" no WhatsApp -> Pix da "taxa"
    "falso_adv": _svg(
        f'<path d="M160 104 H258 L290 136 V300 H160 Z" fill="none" stroke="#fff" stroke-width="8" stroke-linejoin="round"/>'
        + f'<path d="M258 104 V136 H290" fill="none" stroke="#fff" stroke-width="8" stroke-linejoin="round"/>'
        + "".join(f'<line x1="186" y1="{y}" x2="{x2}" y2="{y}" stroke="{c}" stroke-width="7" stroke-linecap="round"/>'
                  for y, x2, c in ((170, 262, "#fff"), (202, 262, A), (234, 262, "#fff"), (266, 230, "#fff")))
        + _seta(312, 392, 202, A)
        + _celular(418, 96, 136, 222) + _pessoa(486, 214, 0.92, gravata=A)
        + _seta(578, 658, 202, A)
        + f'<rect x="684" y="142" width="226" height="120" rx="22" fill="none" stroke="#fff" stroke-width="8"/>'
        + _rotulo(797, 206, "Pix", "#fff", 50)
        + _rotulo(797, 246, "taxa", A, 28)),
    # agora com IA: audiencia falsa por video, com juiz feito com IA, pedindo Pix
    "juiz_ia": _svg(
        f'<rect x="196" y="98" width="388" height="190" rx="14" fill="#1C1C26" stroke="#fff" stroke-width="8"/>'
        + f'<path d="M164 302 H616 L594 322 H186 Z" fill="none" stroke="#fff" stroke-width="8" stroke-linejoin="round"/>'
        + _juiz(390, 212, 0.95)
        + f'<rect x="488" y="112" width="80" height="48" rx="12" fill="{A}"/>'
        + f'<text x="528" y="148" text-anchor="middle" font-family="Inter" font-weight="800" font-size="32" fill="#101016">IA</text>'
        + _seta(640, 720, 196, A)
        + f'<rect x="746" y="146" width="164" height="100" rx="22" fill="none" stroke="#fff" stroke-width="8"/>'
        + _rotulo(828, 212, "Pix", "#fff", 46)
        + _rotulo(828, 292, "urgente", A, 30)),
    # o numero: registros na OAB-PR, 2025 (ano todo) x 2026 (ate 21/09)
    "barras_oab": _svg(
        _rotulo(206, 152, "2025", "#D6D6DE", 32)
        + f'<rect x="262" y="112" width="{round(2103 / 3600 * 520)}" height="56" rx="12" fill="#D6D6DE"/>'
        + f'<text x="{262 + round(2103 / 3600 * 520) + 18}" y="152" font-family="Inter" font-weight="800" font-size="32" fill="#fff">2.103</text>'
        + _rotulo(206, 262, "2026", A, 32)
        + f'<rect x="262" y="222" width="520" height="56" rx="12" fill="{A}"/>'
        + f'<text x="800" y="262" font-family="Inter" font-weight="800" font-size="32" fill="{A}">3.600</text>'),
    # proteger: ligue para o seu advogado + confira o processo no site do tribunal
    "confirma": _svg(
        _celular(170, 100, 128, 214) + _pessoa(234, 194, 0.78, gravata=A)
        + f'<circle cx="234" cy="274" r="26" fill="#2EB67D"/>' + _fone(234, 274, "#fff", 0, 0.55)
        + _rotulo(348, 222, "+", A, 64)
        + f'<rect x="400" y="110" width="510" height="196" rx="16" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<line x1="404" y1="150" x2="906" y2="150" stroke="#fff" stroke-width="6"/>'
        + "".join(f'<circle cx="{x}" cy="130" r="7" fill="#fff"/>' for x in (428, 452, 476))
        + f'<rect x="430" y="178" width="316" height="56" rx="28" fill="none" stroke="#D6D6DE" stroke-width="5"/>'
        + f'<circle cx="462" cy="204" r="13" fill="none" stroke="{A}" stroke-width="5"/>'
        + f'<line x1="471" y1="213" x2="482" y2="224" stroke="{A}" stroke-width="6" stroke-linecap="round"/>'
        + f'<text x="494" y="216" font-family="Inter" font-weight="600" font-size="27" fill="#D6D6DE">seu processo</text>'
        + f'<circle cx="826" cy="206" r="32" fill="{A}"/>'
        + f'<path d="M810 206 L822 219 L843 193" fill="none" stroke="#101016" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        + _rotulo(655, 282, "site do tribunal", "#D6D6DE", 26)),
})


# ---- golpe da vez #4 (falso premio com apresentador feito com IA) ----------
DIAGRAMAS.update({
    # como funciona: "apresentador" (IA) na videochamada -> "voce ganhou" -> contas esvaziadas
    "premio_video": _svg(
        _celular(160, 96, 136, 222) + _pessoa(228, 214, 0.86)
        + f'<rect x="232" y="112" width="54" height="34" rx="9" fill="{A}"/>'
        + f'<text x="259" y="137" text-anchor="middle" font-family="Inter" font-weight="800" font-size="22" fill="#101016">IA</text>'
        + f'<path d="M332 112 H588 Q606 112 606 130 V206 Q606 224 588 224 H356 L322 250 L334 224 Q316 224 316 206 V130 Q316 112 332 112 Z" '
          f'fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round"/>'
        + _rotulo(461, 160, "você ganhou", "#fff", 29)
        + _rotulo(461, 204, "R$ 100 mil!", A, 36)
        + _seta(628, 708, 190, A)
        + f'<path d="M740 150 L825 112 L910 150 Z" fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round"/>'
        + "".join(f'<rect x="{x}" y="160" width="14" height="72" rx="3" fill="#fff"/>' for x in (758, 794, 830, 866))
        + f'<rect x="740" y="238" width="170" height="14" rx="4" fill="#fff"/>'
        + f'<path d="M825 266 V304 M809 290 L825 306 L841 290" fill="none" stroke="#E5484D" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'),
    # proteger: premio que voce nao esperava (X) + senha/codigo por telefone (X)
    "premio_nao": _svg(
        f'<rect x="176" y="168" width="170" height="120" rx="10" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<rect x="164" y="136" width="194" height="40" rx="8" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<line x1="261" y1="136" x2="261" y2="288" stroke="{A}" stroke-width="12"/>'
        + f'<path d="M261 136 Q226 96 214 118 Q206 138 261 136 Q316 138 308 118 Q296 96 261 136" fill="none" stroke="{A}" stroke-width="8"/>'
        + f'<circle cx="352" cy="146" r="28" fill="#E5484D"/>'
        + f'<path d="M341 135 L363 157 M363 135 L341 157" stroke="#fff" stroke-width="7" stroke-linecap="round"/>'
        + _rotulo(261, 326, "prêmio surpresa", "#D6D6DE", 26)
        + _celular(560, 96, 136, 222)
        + f'<rect x="578" y="160" width="100" height="40" rx="10" fill="none" stroke="#D6D6DE" stroke-width="5"/>'
        + _rotulo(628, 190, "• • • •", "#fff", 26)
        + f'<rect x="578" y="214" width="100" height="40" rx="10" fill="none" stroke="#D6D6DE" stroke-width="5"/>'
        + _rotulo(628, 243, "123 456", "#fff", 22)
        + f'<circle cx="700" cy="112" r="28" fill="#E5484D"/>'
        + f'<path d="M689 101 L711 123 M711 101 L689 123" stroke="#fff" stroke-width="7" stroke-linecap="round"/>'
        + _rotulo(820, 196, "senha", "#fff", 30) + _rotulo(820, 236, "e código", "#fff", 30)),
    # desligue -> ligue voce no canal oficial
    "desliga_oficial": _svg(
        _celular(180, 100, 128, 214) + _rotulo(244, 170, "?", "#fff", 60)
        + f'<circle cx="244" cy="258" r="30" fill="#E5484D"/>' + _fone(244, 258, "#fff", 135, 0.62)
        + _seta(360, 452, 207, A)
        + _celular(500, 100, 128, 214)
        + f'<path d="M564 136 L604 150 V184 Q604 214 564 230 Q524 214 524 184 V150 Z" fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round"/>'
        + f'<path d="M548 182 L560 195 L582 170" fill="none" stroke="{A}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        + f'<circle cx="564" cy="270" r="26" fill="#2EB67D"/>' + _fone(564, 270, "#fff", 0, 0.55)
        + _rotulo(790, 190, "ligue você", "#fff", 34)
        + _rotulo(790, 236, "no canal", "#D6D6DE", 29)
        + _rotulo(790, 274, "oficial", "#D6D6DE", 29)),
})


def _banco(cx, cy, esc=1.0, cor="#fff"):
    """predio de banco generico (fronte com colunas), sem marca"""
    return (f'<g transform="translate({cx},{cy}) scale({esc})">'
            f'<path d="M-62 -26 L0 -58 L62 -26 Z" fill="none" stroke="{cor}" stroke-width="7" stroke-linejoin="round"/>'
            + "".join(f'<rect x="{x}" y="-18" width="11" height="52" rx="3" fill="{cor}"/>' for x in (-47, -20, 9, 36))
            + f'<rect x="-62" y="38" width="124" height="11" rx="3" fill="{cor}"/></g>')


DIAGRAMAS.update({
    # o caso: tres contas esvaziadas (R$ 30 mil + R$ 11 mil + R$ 1 mil = R$ 42 mil, Jornal da Regiao)
    "tres_contas": _svg(
        "".join(_banco(cx, 196, 1.0) + _rotulo(cx, 300, v, A, 34)
                + f'<path d="M{cx + 84} 150 V214 M{cx + 70} 200 L{cx + 84} 216 L{cx + 98} 200" fill="none" stroke="#E5484D" '
                  f'stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
                for cx, v in ((236, "R$ 30 mil"), (512, "R$ 11 mil"), (788, "R$ 1 mil")))),
})


# ---- Reels "risco de 3a guerra mundial" (23/09) ------------------------------
def _missil(cx, base, esc=1.0, cor="#fff"):
    """missil/ogiva generico em pe (corpo, bico e aletas)"""
    return (f'<g transform="translate({cx},{base}) scale({esc})">'
            f'<path d="M-11 0 V-78 Q-11 -104 0 -118 Q11 -104 11 -78 V0 Z" fill="{cor}"/>'
            f'<path d="M-11 -24 L-24 0 H-11 Z M11 -24 L24 0 H11 Z" fill="{cor}"/></g>')


def _drone(cx, cy, esc=1.0, cor="#fff"):
    """quadricoptero generico visto de cima"""
    g = f'<g transform="translate({cx},{cy}) scale({esc})">'
    g += f'<rect x="-24" y="-24" width="48" height="48" rx="12" fill="{cor}"/>'
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        g += (f'<line x1="{dx * 18}" y1="{dy * 18}" x2="{dx * 52}" y2="{dy * 52}" stroke="{cor}" stroke-width="9" stroke-linecap="round"/>'
              f'<circle cx="{dx * 58}" cy="{dy * 58}" r="24" fill="none" stroke="{cor}" stroke-width="7"/>')
    return g + '</g>'


def _relogio(cx, cy, r):
    marcas = "".join(
        f'<line x1="{cx + (r - 14) * __import__("math").sin(a * 0.5236):.1f}" y1="{cy - (r - 14) * __import__("math").cos(a * 0.5236):.1f}" '
        f'x2="{cx + (r - 2) * __import__("math").sin(a * 0.5236):.1f}" y2="{cy - (r - 2) * __import__("math").cos(a * 0.5236):.1f}" '
        f'stroke="#fff" stroke-width="{7 if a % 3 == 0 else 4}" stroke-linecap="round"/>' for a in range(12))
    import math
    ang_min = math.radians(-8.5)    # 85 s antes da meia-noite (ponteiro de minutos)
    ang_hr = math.radians(-0.7)
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#fff" stroke-width="8"/>' + marcas
            + f'<path d="M{cx} {cy} L{cx} {cy - r + 10} A{r - 10} {r - 10} 0 0 0 {cx + (r - 10) * math.sin(ang_min):.1f} {cy - (r - 10) * math.cos(ang_min):.1f} Z" fill="#E5484D" opacity=".85"/>'
            + f'<line x1="{cx}" y1="{cy}" x2="{cx + (r - 26) * math.sin(ang_min):.1f}" y2="{cy - (r - 26) * math.cos(ang_min):.1f}" stroke="{A}" stroke-width="9" stroke-linecap="round"/>'
            + f'<line x1="{cx}" y1="{cy}" x2="{cx + (r - 50) * math.sin(ang_hr):.1f}" y2="{cy - (r - 50) * math.cos(ang_hr):.1f}" stroke="#fff" stroke-width="11" stroke-linecap="round"/>'
            + f'<circle cx="{cx}" cy="{cy}" r="10" fill="{A}"/>')


def _chip_foco(x, y, txt, w=360):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="84" rx="42" fill="none" stroke="#fff" stroke-width="6"/>'
            f'<circle cx="{x + 44}" cy="{y + 42}" r="14" fill="#E5484D"/>'
            f'<text x="{x + 72}" y="{y + 53}" font-family="Inter" font-weight="800" font-size="30" fill="#fff">{txt}</text>')


DIAGRAMAS.update({
    # relogio do juizo final: 85 s para a meia-noite (Bulletin of the Atomic Scientists, jan/2026)
    "relogio_fim": _svg(
        _relogio(330, 212, 112)
        + f'<text x="500" y="200" font-family="Anton" font-size="78" fill="{A}">85 segundos</text>'
        + f'<text x="502" y="250" font-family="Inter" font-weight="800" font-size="32" fill="#fff">para a meia-noite</text>'
        + f'<text x="502" y="292" font-family="Inter" font-weight="600" font-size="27" fill="#D6D6DE">o mais perto da história</text>'),
    # os focos (cada um envolve ao menos um pais com arma nuclear)
    "focos": _svg(
        _chip_foco(160, 112, "Rússia x Ucrânia") + _chip_foco(560, 112, "EUA x Irã")
        + _chip_foco(160, 222, "China x Taiwan") + _chip_foco(560, 222, "Coreia do Norte")),
    # 9 paises com armas nucleares (SIPRI 2026)
    "nove_paises": _svg(
        "".join(_missil(190 + k * 87.5, 262, 0.95, A if k < 9 else "#fff") for k in range(9))
        + _rotulo(540, 318, "9 países têm armas nucleares", "#fff", 30)),
    # IA na guerra: drone com IA -> alvo -> maquina nao decide
    "ia_guerra": _svg(
        _drone(290, 206, 1.0)
        + f'<rect x="332" y="112" width="80" height="48" rx="12" fill="{A}"/>'
        + f'<text x="372" y="148" text-anchor="middle" font-family="Inter" font-weight="800" font-size="32" fill="#101016">IA</text>'
        + _seta(430, 520, 206, A)
        + f'<circle cx="636" cy="206" r="86" fill="none" stroke="#fff" stroke-width="7"/>'
        + f'<circle cx="636" cy="206" r="46" fill="none" stroke="#fff" stroke-width="6"/>'
        + f'<line x1="636" y1="104" x2="636" y2="308" stroke="#fff" stroke-width="5"/>'
        + f'<line x1="534" y1="206" x2="738" y2="206" stroke="#fff" stroke-width="5"/>'
        + f'<circle cx="820" cy="134" r="40" fill="#E5484D"/>'
        + f'<path d="M804 118 L836 150 M836 118 L804 150" stroke="#fff" stroke-width="9" stroke-linecap="round"/>'
        + _rotulo(820, 216, "máquina", "#fff", 28) + _rotulo(820, 252, "não decide", "#fff", 28)),
    # efeito no Brasil: petroleo -> diesel
    "petroleo_diesel": _svg(
        f'<rect x="196" y="116" width="150" height="176" rx="24" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<line x1="196" y1="164" x2="346" y2="164" stroke="#fff" stroke-width="6"/>'
        + f'<line x1="196" y1="244" x2="346" y2="244" stroke="#fff" stroke-width="6"/>'
        + _rotulo(271, 216, "US$ 99", A, 34)
        + _rotulo(271, 330, "petróleo", "#D6D6DE", 26)
        + _seta(380, 470, 204, A)
        + f'<rect x="506" y="112" width="130" height="190" rx="14" fill="none" stroke="#fff" stroke-width="8"/>'
        + f'<rect x="526" y="134" width="90" height="56" rx="8" fill="none" stroke="#fff" stroke-width="5"/>'
        + f'<path d="M636 150 H660 Q674 150 674 166 V246 Q674 262 688 262 Q702 262 702 246 V178 L682 158" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        + _rotulo(571, 172, "R$", A, 26)
        + _rotulo(818, 196, "R$ 7,13", A, 50)
        + _rotulo(818, 238, "o litro do diesel", "#fff", 25)
        + _rotulo(571, 330, "diesel", "#D6D6DE", 26)),
    # o que fazer: video de guerra -> IA? -> confira antes de repassar
    "video_falso": _svg(
        _celular(170, 96, 136, 222)
        + f'<rect x="184" y="150" width="108" height="92" rx="10" fill="#1C1C26" stroke="#fff" stroke-width="4"/>'
        + f'<path d="M226 176 L226 216 L256 196 Z" fill="#fff"/>'
        + f'<rect x="250" y="112" width="64" height="40" rx="10" fill="#E5484D"/>'
        + f'<text x="282" y="141" text-anchor="middle" font-family="Inter" font-weight="800" font-size="24" fill="#fff">IA?</text>'
        + _seta(346, 436, 207, A)
        + f'<circle cx="530" cy="190" r="56" fill="none" stroke="#fff" stroke-width="9"/>'
        + f'<line x1="570" y1="230" x2="616" y2="276" stroke="#fff" stroke-width="14" stroke-linecap="round"/>'
        + _rotulo(530, 206, "fonte?", A, 30)
        + _rotulo(800, 190, "confira antes", "#fff", 33)
        + _rotulo(800, 236, "de repassar", "#fff", 33)),
})


DIAGRAMAS.update({
    # +60 guerras envolvendo ao menos um Estado (Turk, ONU, 07/09/2026): 60 marcas
    "grade_60": _svg("".join(
        f'<circle cx="{175 + (k % 15) * 52:.0f}" cy="{132 + (k // 15) * 52:.0f}" r="15" fill="#E5484D"/>'
        for k in range(60))),
})


# ---- Reels "corrida pela AGI" (23/09) ----------------------------------------
def _arco(cx, cy, r, a1, a2, cor, larg):
    """arco de a1 a a2 graus (0 = direita, 90 = topo), no sentido horario da tela"""
    import math
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
    x2, y2 = cx + r * math.cos(math.radians(a2)), cy - r * math.sin(math.radians(a2))
    return (f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{cor}" '
            f'stroke-width="{larg}" stroke-linecap="butt"/>')


def _medidor(cx, cy, r, ang):
    """medidor de 4 faixas (baixo, medio, alto, critico) com o ponteiro em ang graus"""
    import math
    cores = ("#4A4A56", "#7A7A88", A, "#E5484D")
    faixas = "".join(_arco(cx, cy, r, 180 - 45 * k - 1.5, 180 - 45 * (k + 1) + 1.5, c, 38) for k, c in enumerate(cores))
    px, py = cx + (r - 34) * math.cos(math.radians(ang)), cy - (r - 34) * math.sin(math.radians(ang))
    return (faixas + f'<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" stroke="#fff" stroke-width="11" stroke-linecap="round"/>'
            + f'<circle cx="{cx}" cy="{cy}" r="17" fill="#fff"/>')


def _lupa(cx, cy, r=52, cor="#fff"):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{cor}" stroke-width="9"/>'
            f'<line x1="{cx + r * .71:.0f}" y1="{cy + r * .71:.0f}" x2="{cx + r * 1.5:.0f}" y2="{cy + r * 1.5:.0f}" '
            f'stroke="{cor}" stroke-width="14" stroke-linecap="round"/>')


DIAGRAMAS.update({
    # GPT-6 Astra: 1o modelo da OpenAI no nivel "Critical" de ciberseguranca (Preparedness Framework, 03/09/2026)
    "medidor_critico": _svg(
        _medidor(344, 292, 158, 22)
        + f'<text x="556" y="206" font-family="Anton" font-size="84" fill="#E5484D">CRÍTICO</text>'
        + f'<text x="558" y="254" font-family="Inter" font-weight="800" font-size="31" fill="#fff">em cibersegurança</text>'
        + f'<text x="558" y="294" font-family="Inter" font-weight="600" font-size="26" fill="#D6D6DE">o 1º da OpenAI nesse nível</text>'),
    # 10% = 1 chance em 10 (AI Impacts, set/2026)
    "um_em_dez": _svg(
        "".join(_pessoa(205 + k * 74.4, 206, 0.78, "#E5484D" if k == 9 else "#fff") for k in range(10))
        + _rotulo(540, 312, "1 chance em 10", "#D6D6DE", 30)),
    # modelos distinguem teste de uso real (International AI Safety Report 2026)
    "teste_real": _svg(
        _chip_ia(210, 118, 124)
        + f'<circle cx="344" cy="112" r="27" fill="#2EB67D"/>'
        + f'<path d="M331 112 L341 123 L358 101" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        + _rotulo(272, 316, "em teste", "#D6D6DE", 29)
        + f'<line x1="496" y1="184" x2="584" y2="184" stroke="{A}" stroke-width="13" stroke-linecap="round"/>'
        + f'<line x1="496" y1="224" x2="584" y2="224" stroke="{A}" stroke-width="13" stroke-linecap="round"/>'
        + f'<line x1="566" y1="146" x2="514" y2="262" stroke="{A}" stroke-width="13" stroke-linecap="round"/>'
        + _chip_ia(746, 118, 124)
        + f'<circle cx="880" cy="112" r="27" fill="#E5484D"/>'
        + _rotulo(880, 124, "?", "#fff", 36)
        + _rotulo(808, 316, "no uso real", "#D6D6DE", 29)),
    # o que fazer: aprenda a usar IA + confira video e voz
    "usar_conferir": _svg(
        _pessoa(252, 214, 1.0)
        + f'<rect x="294" y="110" width="74" height="44" rx="12" fill="{A}"/>'
        + f'<text x="331" y="143" text-anchor="middle" font-family="Inter" font-weight="800" font-size="28" fill="#101016">IA</text>'
        + _rotulo(268, 318, "aprenda a usar", "#fff", 28)
        + _rotulo(468, 232, "+", A, 64)
        + f'<rect x="560" y="116" width="170" height="112" rx="14" fill="none" stroke="#fff" stroke-width="7"/>'
        + f'<path d="M628 146 L628 198 L668 172 Z" fill="#fff"/>'
        + _lupa(742, 214, 50, A)
        + _rotulo(700, 318, "confira antes", "#fff", 28)),
    # AGI: uma IA para qualquer trabalho intelectual (codigo, saude, direito, texto)
    "agi_tudo": _svg(
        _chip_ia(478, 112, 124)
        + "".join(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#6A6A78" stroke-width="5" stroke-dasharray="10 9"/>'
                  for x1, y1, x2, y2 in ((296, 138, 470, 150), (296, 262, 470, 214), (610, 150, 784, 138), (610, 214, 784, 262)))
        + f'<rect x="176" y="98" width="120" height="80" rx="16" fill="none" stroke="#fff" stroke-width="7"/>'
        + _rotulo(236, 152, "&lt;/&gt;", "#fff", 38)
        + f'<rect x="176" y="222" width="120" height="80" rx="16" fill="none" stroke="#fff" stroke-width="7"/>'
        + f'<rect x="224" y="238" width="24" height="48" rx="4" fill="#E5484D"/><rect x="212" y="250" width="48" height="24" rx="4" fill="#E5484D"/>'
        + f'<rect x="784" y="98" width="120" height="80" rx="16" fill="none" stroke="#fff" stroke-width="7"/>'
        + f'<line x1="844" y1="110" x2="844" y2="164" stroke="#fff" stroke-width="6" stroke-linecap="round"/>'
        + f'<line x1="812" y1="120" x2="876" y2="120" stroke="#fff" stroke-width="6" stroke-linecap="round"/>'
        + f'<path d="M800 146 Q812 160 824 146 M864 146 Q876 160 888 146" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round"/>'
        + f'<line x1="812" y1="120" x2="800" y2="146" stroke="#fff" stroke-width="4"/><line x1="812" y1="120" x2="824" y2="146" stroke="#fff" stroke-width="4"/>'
        + f'<line x1="876" y1="120" x2="864" y2="146" stroke="#fff" stroke-width="4"/><line x1="876" y1="120" x2="888" y2="146" stroke="#fff" stroke-width="4"/>'
        + f'<rect x="784" y="222" width="120" height="80" rx="16" fill="none" stroke="#fff" stroke-width="7"/>'
        + "".join(f'<line x1="806" y1="{y}" x2="{x2}" y2="{y}" stroke="{c}" stroke-width="7" stroke-linecap="round"/>'
                  for y, x2, c in ((246, 882, "#fff"), (262, 882, A), (278, 850, "#fff")))
        + _rotulo(540, 322, "qualquer trabalho intelectual", "#D6D6DE", 29)),
    # a corrida: 5 modelos em 20 dias (datas dos anuncios oficiais, set/2026)
    "corrida_20dias": _svg(
        f'<line x1="186" y1="104" x2="186" y2="302" stroke="#4A4A56" stroke-width="5" stroke-linecap="round"/>'
        + "".join(
            f'<circle cx="186" cy="{y - 9}" r="{11 if dest else 8}" fill="{A if dest else "#fff"}"/>'
            f'<text x="212" y="{y}" font-family="Anton" font-size="29" fill="{A}">{d}</text>'
            f'<text x="306" y="{y}" font-family="Inter" font-weight="800" font-size="27" fill="{A if dest else "#fff"}">{m}</text>'
            f'<text x="572" y="{y}" font-family="Inter" font-weight="600" font-size="23" fill="#9A9AA8">{c}</text>'
            for y, d, m, c, dest in ((126, "02/09", "Gemini 3.8", "Google", False),
                                     (172, "03/09", "GPT-6 Astra", "OpenAI", True),
                                     (218, "10/09", "DeepSeek V4.1", "China", False),
                                     (264, "21/09", "Grok 4.7", "xAI", False),
                                     (310, "22/09", "Claude Opus 5.5", "Anthropic", False)))),
    # checagem Trump/ONU: municao que leva 3 a 4 anos para repor (CSIS via PolitiFact)
    "municao_anos": _svg(
        "".join(_missil(196 + k * 58, 300, 0.9, "#fff") for k in range(5))
        + f'<path d="M520 112 H608 M520 300 H608 M530 112 Q530 190 564 206 Q530 222 530 300 M598 112 Q598 190 564 206 Q598 222 598 300" '
          f'fill="none" stroke="{A}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        + f'<path d="M548 262 L580 262 L564 236 Z" fill="{A}"/>'
        + f'<text x="636" y="206" font-family="Anton" font-size="62" fill="{A}">3 a 4 anos</text>'
        + _rotulo(752, 256, "para repor mísseis", "#fff", 28)
        + _rotulo(752, 294, "e interceptadores", "#fff", 28)),
    # checagem: "era da superinteligencia" — a IA de hoje e irregular (PolitiFact)
    "superinteligencia": _svg(
        f'<line x1="176" y1="138" x2="900" y2="138" stroke="{A}" stroke-width="6" stroke-dasharray="14 10"/>'
        + f'<text x="900" y="124" text-anchor="end" font-family="Inter" font-weight="800" font-size="26" fill="{A}">superinteligência</text>'
        + f'<polyline points="{" ".join(f"{176 + i * 45},{y}" for i, y in enumerate((282, 196, 266, 170, 276, 222, 300, 186, 256, 208, 290, 178, 270, 230, 296, 198, 262)))}" '
          f'fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/>'
        + _rotulo(540, 326, "a IA de hoje: ótima em algumas tarefas, fraca em outras", "#D6D6DE", 25)),
    # checagem: EUA a frente da China em IA, mas por poucos meses
    "eua_china_meses": _svg(
        _rotulo(214, 164, "EUA", "#fff", 34)
        + f'<rect x="276" y="130" width="600" height="46" rx="12" fill="{A}"/>'
        + _rotulo(214, 262, "China", "#fff", 34)
        + f'<rect x="276" y="228" width="520" height="46" rx="12" fill="#E5484D"/>'
        + f'<line x1="806" y1="252" x2="866" y2="252" stroke="#fff" stroke-width="5" stroke-dasharray="6 6"/>'
        + _rotulo(790, 322, "alguns meses", "#fff", 28)),
    # o que fazer: frase de politico -> checagem antes de repassar
    "checar_frase": _svg(
        f'<path d="M176 118 H436 Q456 118 456 138 V222 Q456 242 436 242 H236 L204 272 L212 242 H196 Q176 242 176 222 V138 Q176 118 196 118 Z" '
          f'fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round"/>'
        + "".join(f'<circle cx="{x}" cy="180" r="13" fill="#fff"/>' for x in (272, 316, 360))
        + _seta(484, 574, 186, A)
        + _lupa(660, 176, 52, A)
        + f'<circle cx="826" cy="140" r="30" fill="#2EB67D"/>'
        + f'<path d="M811 140 L822 152 L842 128" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        + f'<circle cx="826" cy="232" r="30" fill="#E5484D"/>'
        + f'<path d="M815 221 L837 243 M837 221 L815 243" stroke="#fff" stroke-width="7" stroke-linecap="round"/>'
        + _rotulo(660, 318, "procure a checagem", "#fff", 28)),
    # Brasil: jovens nas ocupacoes mais expostas a IA (FGV Ibre, set/2026)
    "jovens_ia": _svg(
        "".join(_pessoa(x, 212, 0.86) for x in (196, 282, 368))
        + f'<text x="486" y="196" font-family="Anton" font-size="78" fill="#E5484D">−5%</text>'
        + _rotulo(560, 244, "de chance", "#fff", 27) + _rotulo(560, 280, "de emprego", "#fff", 27)
        + f'<text x="716" y="196" font-family="Anton" font-size="78" fill="#E5484D">−7%</text>'
        + _rotulo(786, 244, "de renda", "#fff", 27)),
})


def foto_curta(path):
    """Faixa curta (340px): fundo borrado + foto inteira, sem corte."""
    uri = R.data_uri(path)
    return (f'<div class="bgfill"><img src="{uri}"></div>'
            f'<div class="shot curto"><img class="fill" src="{uri}">'
            f'<img class="real" src="{uri}">'
            f'<div class="top-scrim"></div><div class="bot-scrim"></div></div>'
            f'<div class="under curto"></div>')


def _moldura(bloco, idx, total, when, st, dentro):
    if bloco.get("diagrama") in DIAGRAMAS:
        foto = f'<div class="diag">{DIAGRAMAS[bloco["diagrama"]]}</div>'
    elif bloco.get("photo"):
        foto = foto_curta(bloco["photo"])
    else:
        foto = ""
    bars = "".join(f'<i class="{"on" if i <= idx else ""}"></i>' for i in range(1, total + 1))
    return R.page(f"""<div class="card">
  {foto}
  <div class="safe top"><div class="mark">{R.EYE}</div><div class="wordmark">PISCA</div>
    <div class="when">{esc(when)}</div></div>
  <div class="safe bars curto">{bars}</div>
  <div class="safe body mat2 st{st}">{dentro}</div>
</div>""")


def card_gancho(g, tag, idx, total, when, st, promessa=""):
    linha = esc(g["linha"]).upper()
    cls = _tam(linha, [(40, ""), (58, "sm"), (999, "xs")])
    prom = f'<div class="promessa2">{esc(promessa)}</div>' if promessa else ""
    dentro = (f'<div class="meta"><div class="chip">{esc(tag)}</div></div>'
              f'<h1 class="gancho {cls}">{linha}</h1>{prom}')
    return _moldura(g, idx, total, when, st, dentro)


def card_texto(b, idx, total, when, st):
    tit = esc(b["titulo"]).upper()
    cls = _tam(tit, [(34, ""), (999, "sm")])
    chip = f'<div class="chip{" ress" if b.get("ressalva") else ""}">{esc(b.get("chip", ""))}</div>' if b.get("chip") else ""
    kick = f'<div class="kicker">{esc(b["kicker"])}</div>' if b.get("kicker") else ""
    dentro = (f'{kick}{f"<div class=meta>{chip}</div>" if chip else ""}'
              f'<h1 class="mat {cls}">{tit}</h1>'
              f'<div class="corpo">{esc(b["texto"])}</div>')
    return _moldura(b, idx, total, when, st, dentro)


def card_numero(b, idx, total, when, st):
    val = esc(b["valor"]).upper()
    cls = _tam(val, [(9, ""), (14, "sm"), (999, "xs")])
    dentro = (f'<div class="kicker">{esc(b.get("kicker", "o número"))}</div>'
              f'<div class="numerao {cls}">{val}</div>'
              f'<div class="numlegenda">{esc(b["legenda"])}</div>')
    return _moldura(b, idx, total, when, st, dentro)


def card_fecho(f, handle, foto=None):
    linhas = esc(f.get("linha", "")).replace("\n", "<br>")
    fundo = f'<div class="bgfill"><img src="{R.data_uri(foto)}"></div>' if foto else ""
    return R.page(f'''<div class="card">{fundo}
  <div class="safe hero" style="left:{(R.W - 712) // 2}px">
    <div class="bigmark">{R.EYE}</div>
    <div class="big">{linhas}</div>
    <div class="line"></div>
    <div class="sub2">{esc(f.get("cta", ""))}</div>
    <div class="h2">{esc(handle)}</div>
  </div>
</div>''')


LIM_Y = R.BAR_Y   # onde comeca a barra de progresso: nenhum texto pode passar daqui


def _checa_estouro(pw, htmls):
    """Mede o bloco de texto de cada cartao. O conferir_video.py NAO pega isso:
    ele olha as faixas que o Instagram corta (topo e rodape), nao o limite da
    barra de progresso. Ja aconteceu de a legenda do numero invadir a barra."""
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": R.W, "height": R.H})
    ruins = []
    for i, doc in enumerate(htmls, 1):
        pg.set_content(doc, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(90)
        # mede o estado ASSENTADO: os quadros st0/st1 entram deslizando 74px
        # mais abaixo e duram 0,22s a 14% de opacidade — medir esses da alarme
        # falso. O que o espectador le e o texto parado.
        b = pg.evaluate("()=>{const e=document.querySelector('.body');"
                        "if(!e) return 0;"
                        "e.classList.remove('st0','st1'); e.classList.add('st2');"
                        "return e.getBoundingClientRect().bottom}")
        if b > LIM_Y:
            ruins.append((i, round(b)))
    br.close()
    if ruins:
        print(f"  ATENCAO: {len(ruins)} cartao(oes) com texto passando de {LIM_Y}px:")
        for i, b in ruins:
            print(f"    cartao {i}: fundo em {b}px (+{b-LIM_Y})")
        print("  Encurte o texto ou baixe o corpo da fonte antes de publicar.")
    else:
        print(f"  texto dentro do limite de {LIM_Y}px em todos os cartoes")


# ============================================================================
# v3 (22/09) — DUAS CAMADAS
# Olhando o quadro zero do Reels publicado: o texto entrava apagado (0,00s) e com
# IMAGEM DUPLA (0,15s) — o fade entre dois estados em posicoes diferentes gerava
# dupla exposicao na entrada de TODO cartao. E o zoom no quadro inteiro nunca pode
# ser usado porque empurra o texto para fora da area segura.
# Solucao: cada cartao vira duas imagens. FUNDO (foto/diagrama) recebe um zoom
# lento de verdade; FRENTE (marca, barras, texto) vem transparente e fica parada
# por cima. O texto entra pronto, sem fade — o quadro zero ja e legivel.
# ============================================================================
ZOOM_FOTO = float(os.environ.get("ZOOM_FOTO", "0.07"))
# Entre cartoes: CORTE SECO (1 quadro). O fade de 0,16s entre dois cartoes cheios
# de texto mostrava os dois textos sobrepostos — a mesma imagem dupla. O movimento
# agora vem do zoom da foto; o corte da o ritmo.
XF_CORTE = 0.034
PONTO_Y = 470          # centro da faixa curta (300..640): o zoom abre a partir dali
CSS_TRANSP = "html,body{background:transparent !important}.card.transp{background:transparent !important}"


def _layout(bloco):
    if bloco.get("foto_cheia"):
        return "cheia"
    if bloco.get("foto_alta"):
        return "alta"
    return "curto"


FOLGA = 44            # espaço entre o fim da faixa (foto/desenho) e o começo do texto


def _faixa_fim(topo):
    """onde a faixa de foto/desenho termina, dado o topo do bloco de texto"""
    return int(max(700, min(1240, topo - FOLGA)))


def _fundo(bloco, topo):
    base = _faixa_fim(topo)
    if bloco.get("foto_cheia"):
        uri = R.data_uri(bloco["foto_cheia"])
        pos = bloco.get("posicao")
        if not pos:                        # 24/09: sem posição, o recorte segue o rosto
            import foco
            pos = foco.posicao(bloco["foto_cheia"], R.W, R.H, alvo_y=0.25, padrao="50% 50%")
        t = int(topo)
        g = (f"linear-gradient(to bottom,rgba(11,11,16,.60) 0px,rgba(11,11,16,.05) 380px,"
             f"rgba(11,11,16,0) {max(420, t - 470)}px,rgba(11,11,16,.72) {t - 170}px,rgba(11,11,16,.92) {t + 10}px,"
             f"rgba(11,11,16,.90) 1545px,rgba(11,11,16,.62) 1720px,rgba(11,11,16,.50) 1920px)")
        # 23/09: ele pediu a foto "em cima e embaixo" — depois do fim do texto (1520) a foto volta a aparecer
        return R.page(f'<div class="card"><div class="fotocheia"><img src="{uri}" style="object-position:{pos}">'
                      f'<div class="grad" style="background:{g}"></div></div></div>')
    under = (f'<div class="under v5" style="top:{base - 70}px;background:linear-gradient(to bottom,'
             f'rgba(11,11,16,.55) 0px,#0B0B10 90px,#0B0B10 {max(100, 1570 - (base - 70))}px,rgba(11,11,16,.84) 100%)"></div>')
    if bloco.get("diagrama") in DIAGRAMAS:
        altura = base - 300
        k = min(1.25, max(1.0, (altura - 60) / 340))
        svg = DIAGRAMAS[bloco["diagrama"]].replace(
            "<svg ", f'<svg style="transform:translateY(-50%) scale({k:.3f})" ', 1)
        return R.page(f'<div class="card"><div class="diag v5" style="height:{altura}px">{svg}</div>{under}</div>')
    foto = bloco.get("foto_alta") or bloco.get("photo")
    if foto:
        uri = R.data_uri(foto)
        return R.page(f'<div class="card"><div class="bgfill"><img src="{uri}"></div>'
                      f'<div class="shot v5" style="height:{base - 300}px"><img class="fill" src="{uri}">'
                      f'<img class="real" src="{uri}"><div class="top-scrim"></div><div class="bot-scrim"></div></div>'
                      f'{under}</div>')
    return R.page('<div class="card"></div>')


def _ponto_zoom(bloco, topo):
    """centro do zoom lento do fundo: o rosto no gancho (zoom_y) ou o meio da faixa"""
    if bloco.get("foto_cheia"):
        return float(bloco.get("zoom_y", 700))
    return (300 + _faixa_fim(topo)) / 2


def _mede_topos(pw, frentes):
    """topo (y) do bloco de texto de cada frente, com o texto ancorado embaixo. Avisa se o texto for tão alto
    que esmague a faixa da foto (faixa com menos de ~400 px)."""
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": R.W, "height": R.H})
    topos = []
    for doc in frentes:
        pg.set_content(doc, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(90)
        r = pg.evaluate("()=>{const e=document.querySelector('.body');const b=e.getBoundingClientRect();"
                        "return [b.top,b.bottom]}")
        topos.append(r[0])
        if r[1] > R.TEXTO_FIM + 2:
            print(f"  ATENCAO: texto passa de {R.TEXTO_FIM}px (fundo em {round(r[1])})")
    br.close()
    apertados = [round(t) for t in topos if t < 744]
    if apertados:
        print(f"  ATENCAO: {len(apertados)} cartão(ões) com texto alto demais (topo em {apertados}): a faixa da foto fica"
              " com menos de 400 px. Encurte o texto.")
    else:
        print(f"  texto de {min(round(t) for t in topos)} a {R.TEXTO_FIM}px; faixa de foto com 400 px ou mais em todos")
    return topos


def _frente(idx, total, when, dentro, lay="curto", credito=""):
    bars = "".join(f'<i class="{"on" if i <= idx else ""}"></i>' for i in range(1, total + 1))
    cred = f'<div class="v5cred">{esc(credito)}</div>' if credito else ""
    doc = R.page(f"""<div class="card transp">
  <div class="safe top"><div class="mark">{R.EYE}</div><div class="wordmark">PISCA</div>
    <div class="when">{esc(when)}</div></div>
  <div class="safe body v5 st2">{cred}<div class="v5bars">{bars}</div>{dentro}</div>
</div>""")
    return doc.replace("</style>", CSS_TRANSP + "</style>", 1)


def _dentro_gancho(g, tag, promessa):
    linha = esc(g["linha"]).upper()
    cls = g.get("classe") or _tam(linha, [(40, ""), (58, "sm"), (999, "xs")])
    prom = f'<div class="promessa2">{esc(promessa)}</div>' if promessa else ""
    return (f'<div class="meta"><div class="chip">{esc(tag)}</div></div>'
            f'<h1 class="gancho {cls}">{linha}</h1>{prom}')


def _dentro_texto(b):
    tit = esc(b["titulo"]).upper()
    cls = _tam(tit, [(34, ""), (999, "sm")])
    chip = (f'<div class="meta"><div class="chip{" ress" if b.get("ressalva") else ""}">'
            f'{esc(b.get("chip", ""))}</div></div>') if b.get("chip") else ""
    kick = f'<div class="kicker">{esc(b["kicker"])}</div>' if b.get("kicker") else ""
    return f'{kick}{chip}<h1 class="mat {cls}">{tit}</h1><div class="corpo">{esc(b["texto"])}</div>'


def _dentro_numero(b, valor=None):
    val = esc(valor if valor is not None else b["valor"]).upper()
    cls = b.get("classe") or _tam(esc(b["valor"]).upper(), [(9, ""), (14, "sm"), (999, "xs")])  # tamanho fixo na contagem
    return (f'<div class="kicker">{esc(b.get("kicker", "o número"))}</div>'
            f'<div class="numerao {cls}">{val}</div>'
            f'<div class="numlegenda">{esc(b["legenda"])}</div>')


def _contagem(valor, passos=5):
    """'+50' -> ['+10','+20','+30','+40','+50']. So conta inteiro simples;
    '1,8 MILHAO' e parecidos nao contam (devolve [])."""
    import re
    # 22/09 noite: "3.600" tambem conta (720, 1.440, ... 3.600), com o ponto de milhar
    m2 = re.fullmatch(r"(\D*)(\d{1,3}(?:\.\d{3})+)(\D*)", valor.strip())
    if m2:
        pre, num, suf = m2.group(1), int(m2.group(2).replace(".", "")), m2.group(3)
        fmt = lambda x: f"{x:,}".replace(",", ".")
        return [f"{pre}{fmt(round(num * k / passos))}{suf}" for k in range(1, passos + 1)]
    m = re.fullmatch(r"(\D*)(\d+)(\D*)", valor.strip())
    if not m:
        return []
    pre, num, suf = m.group(1), int(m.group(2)), m.group(3)
    if num < passos:
        return []
    return [f"{pre}{round(num * k / passos)}{suf}" for k in range(1, passos + 1)]


def _foto_camadas(pw, pares, pasta):
    """pares = lista de (html_fundo, html_frente|None). Devolve [(png_fundo, png_frente|None)]."""
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": R.W, "height": R.H}, device_scale_factor=R.SCALE)
    out = []
    for i, (fundo, frente) in enumerate(pares, 1):
        pf = pasta / f"c{i:02d}_fundo.png"
        pg.set_content(fundo, wait_until="load"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(150)
        pg.screenshot(path=str(pf))
        pt = None
        if frente:
            pt = pasta / f"c{i:02d}_frente.png"
            pg.set_content(frente, wait_until="load"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(150)
            pg.screenshot(path=str(pt), omit_background=True)
        out.append((pf, pt))
        print(f"  camada {i} ok")
    br.close()
    return out


def montar_video(pecas, out):
    """pecas: dicts com fundo, frente (ou None), d (s), xf (fade p/ a proxima), z0, z1.
    Fundo: 1 quadro -> zoompan gera exatamente d*30 quadros (zoom real, suave).
    Frente: transparente, parada, sobreposta."""
    import subprocess
    W, H = R.W, R.H
    ins, filt, k = [], [], 0
    for i, p in enumerate(pecas):
        fr = max(2, int(round(p["d"] * 30)))
        ins += ["-i", str(p["fundo"])]; ib = k; k += 1
        # amplia 2x antes do zoompan: ele recorta em pixel inteiro, e com o quadro
        # maior o degrau cai para ~1/3 de pixel na saida (medido: sem isso a faixa
        # tremia em picos regulares a cada 5-7 quadros)
        filt.append(f"[{ib}:v]scale=iw*2:ih*2:flags=lanczos,"
                    f"zoompan=z='{p['z0']:.4f}+({p['z1'] - p['z0']:.4f})*on/{fr}':d={fr}"
                    f":x='iw/2-(iw/zoom/2)':y='ih*{p.get('py', PONTO_Y) / H:.5f}*(1-1/zoom)'"
                    f":s={W}x{H}:fps=30,setsar=1,format=yuv420p[bg{i}]")
        if p.get("frente"):
            ins += ["-loop", "1", "-framerate", "30", "-t", f"{p['d']:.3f}", "-i", str(p["frente"])]
            it = k; k += 1
            filt.append(f"[{it}:v]scale={W}:{H},format=rgba[fg{i}]")
            filt.append(f"[bg{i}][fg{i}]overlay=0:0:shortest=1:format=auto,format=yuv420p,"
                        f"settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
        else:
            filt.append(f"[bg{i}]settb=AVTB,setpts=PTS-STARTPTS[v{i}]")

    # Emenda direta (concat): corte de verdade, ZERO quadros misturados. O xfade
    # nao tem corte seco — a duracao minima e 1 quadro, e esse quadro sai com os
    # dois cartoes sobrepostos (visto na troca ressalva -> fecho).
    n = len(pecas)
    filt.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]")
    cur = "vc"
    total = sum(max(2, int(round(p["d"] * 30))) for p in pecas) / 30.0

    i_trilha, i_barra = k, k + 1
    filt.append(f"[{i_barra}:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                f"a='if(lte(X,{R.BAR_W}*T/{total:.3f}),255,0)'[bar]")
    t_fecho = total - max(2, int(round(pecas[-1]["d"] * 30))) / 30.0   # a barra some no cartão final (centralizado)
    filt.append(f"[{cur}][bar]overlay=x={R.BAR_X}:y={R.BAR_Y}:format=auto:enable='lt(t,{t_fecho:.3f})'[vp]")
    filt.append(f"[{i_trilha}:a]atrim=0:{total:.3f},asetpts=N/SR/TB,"
                f"afade=t=in:st=0:d={getattr(R, 'FADE_IN', 0.4)},afade=t=out:st={max(0, total - 1.2):.3f}:d=1.2[a]")
    cmd = (["ffmpeg", "-y"] + ins
           + ["-stream_loop", "-1", "-i", str(R.TRILHA),
              "-f", "lavfi", "-i", f"color=c=0x{R.ACCENT.lstrip('#')}:s={R.BAR_W}x{R.BAR_H}:d={total:.3f}:r=30",
              "-filter_complex", ";".join(filt), "-map", "[vp]", "-map", "[a]",
              "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-level", "4.1",
              "-pix_fmt", "yuv420p", "-r", "30", "-g", "60", "-movflags", "+faststart",
              "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-t", f"{total:.3f}", str(out)])
    print(f"  ffmpeg: montando {total:.1f}s")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    return total


def main():
    d = json.loads(MATERIA.read_text(encoding="utf-8"))
    when, tag, blocos = d.get("date_label", ""), d.get("tag", ""), d["blocos"]
    # 23/09: "todo reels sai sempre conforme as boas práticas" — foto em tela cheia em todo cartão com foto
    for nome, b in [("gancho", d.get("gancho", {}))] + [(f"bloco {i}", b) for i, b in enumerate(blocos, 1)]:
        if (b.get("foto_alta") or b.get("photo")) and not b.get("foto_cheia"):
            print(f"AVISO boas práticas: {nome} sem foto em tela cheia (use foto_cheia; foto deitada de objeto: compor vertical)")
    total = 1 + len(blocos)
    # 24/09 ("faça direito, tudo"): ficha para a trava do publicador + regra de não repetir já na produção
    import nao_repete as NR, boas_praticas as BP
    NR.avisa(NR.manchetes(MATERIA))
    import foto_repete as FR          # 24/09: foto que já saiu trava
    FR.trava(MATERIA)
    cartoes = []
    for nome, b in [("gancho", d.get("gancho", {}))] + [(f"bloco {i}", b) for i, b in enumerate(blocos, 1)]:
        foto = b.get("foto_cheia")
        if foto:
            p_ = Path(foto) if Path(foto).is_absolute() else BASE / foto
            cartoes.append({"cartao": nome, "foto": foto, "modo": "composta" if p_.stem.endswith("_v") else "cheia",
                            "escala": round(BP.escala(p_, R.W, R.H, 1.0 + ZOOM_FOTO), 2),
                            "aviso": BP.aviso_foto(p_, R.W, R.H, 1.0 + ZOOM_FOTO, nome)})
        elif b.get("diagrama"):
            cartoes.append({"cartao": nome, "foto": None, "modo": "desenho", "escala": None, "aviso": None})
        elif b.get("foto_alta") or b.get("photo"):
            cartoes.append({"cartao": nome, "foto": b.get("foto_alta") or b.get("photo"), "modo": "faixa", "escala": None,
                            "aviso": None})
        else:
            cartoes.append({"cartao": nome, "foto": None, "modo": "sem foto", "escala": None,
                            "aviso": f"AVISO {nome}: cartão só com texto (Reels \"mostly text\" é menos descoberto)"})

    # 23/09: padrao IMPACTO — trilha gerada sob medida, com pancada em cada corte (trilha_impacto.py).
    # O José Miguel pediu "músicas mais impactantes"; a biblioteca do Instagram só existe no app.
    # TRILHA_NOME=PULSO|CORRIDA|NOTURNO|TENSAO (ou TRILHA=arquivo) volta para as trilhas fixas.
    # 24/09 (ele): "música diferente e dramática no reels" -> padrão DRAMA (tensão: drone, cordas, coração, pancadas
    # nos cortes; trilha_tensao.py). IMPACTO continua disponível com "trilha": "IMPACTO" no json.
    escolha = (os.environ.get("TRILHA_NOME") or d.get("trilha") or ("" if os.environ.get("TRILHA") else "IMPACTO")).upper()
    impacto = escolha in ("IMPACTO", "DRAMA")
    if impacto:
        print(f"trilha: {escolha} (batida nos cortes; gerada depois de montar o plano)")
    else:
        nome = R._escolhe_trilha(when)
        R.TRILHA = Path(os.environ.get("TRILHA", str(BASE / f"Pisca_trilha_{nome}.mp3")))
        if not R.TRILHA.exists():
            import subprocess
            subprocess.run([sys.executable, str(BASE / "trilha.py"), str(R.TRILHA), "40", nome], check=True)
        print(f"trilha: {nome}")

    dur_de = lambda b, tipo: float(b.get("dur", DUR.get(tipo, 5.5)))
    d_gancho = dur_de(d["gancho"], "gancho")
    seg = d_gancho + sum(dur_de(b, b.get("tipo", "texto")) for b in blocos) + DUR["fecho"]
    promessa = d.get("gancho", {}).get("promessa") or f"a história em {int(round(seg))} segundos"
    print(f"Reels materia v3: 1 gancho + {len(blocos)} blocos  ~{seg:.1f}s")

    # cada item: (html_fundo, html_frente, duracao, xf, z0, z1)
    plano = [(d["gancho"], _frente(1, total, when, _dentro_gancho(d["gancho"], tag, promessa), _layout(d["gancho"]), d["gancho"].get("credito", "")),
              d_gancho, XF_CORTE, 1.0, 1.0 + ZOOM_FOTO)]
    inicios = [(0, "gancho")]          # (indice no plano, tipo) de cada cartao — para a trilha IMPACTO
    for i, b in enumerate(blocos, 2):
        inicios.append((len(plano), b.get("tipo", "texto")))
        fundo = b                       # o HTML do fundo sai depois de medir o texto (v5)
        if b.get("tipo") == "numero":
            passos = _contagem(b["valor"])
            if passos:
                t_passo = 0.09
                for v in passos[:-1]:
                    plano.append((fundo, _frente(i, total, when, _dentro_numero(b, v), _layout(b), b.get("credito", "")), t_passo, 0.034, 1.0, 1.0))
                resto = dur_de(b, "numero") - t_passo * (len(passos) - 1)
                plano.append((fundo, _frente(i, total, when, _dentro_numero(b), _layout(b), b.get("credito", "")), resto, XF_CORTE, 1.0, 1.0 + ZOOM_FOTO))
            else:
                plano.append((fundo, _frente(i, total, when, _dentro_numero(b), _layout(b), b.get("credito", "")), dur_de(b, "numero"), XF_CORTE, 1.0, 1.0 + ZOOM_FOTO))
        else:
            plano.append((fundo, _frente(i, total, when, _dentro_texto(b), _layout(b), b.get("credito", "")), dur_de(b, "texto"), XF_CORTE, 1.0, 1.0 + ZOOM_FOTO))
    inicios.append((len(plano), "fecho"))
    g = d["gancho"]
    foto_g = g.get("foto_cheia") or g.get("foto_alta") or g.get("photo")
    plano.append((card_fecho(d.get("fecho", {}), d.get("handle", "@pisca.news"), foto_g), None, DUR["fecho"], 0.0, 1.0, 1.0))  # fecho e so texto: sem zoom (letra treme)

    pasta = R.FRAMES
    with sync_playwright() as pw:
        # v5: mede onde o texto de cada cartão começa (ancorado embaixo) e só então monta o fundo
        topos = _mede_topos(pw, [f for _, f, *_ in plano if f])
        it = iter(topos)
        tops = [next(it) if f else None for _, f, *_ in plano]
        fundos = [_fundo(a, t) if f else a for (a, f, *_), t in zip(plano, tops)]
        pngs = _foto_camadas(pw, [(fu, f) for fu, (_, f, *_) in zip(fundos, plano)], pasta)

    pys = [_ponto_zoom(a, t) if f else PONTO_Y for (a, f, *_), t in zip(plano, tops)]
    pecas = [dict(fundo=pf, frente=pt, d=p[2], xf=p[3], z0=p[4], z1=p[5], py=py)
             for (pf, pt), p, py in zip(pngs, plano, pys)]
    if impacto:
        # tempos dos cortes medidos em QUADROS, igual ao montar_video (cada peça = max(2, round(d*30)) quadros)
        quadros = [max(2, int(round(p[2] * 30))) for p in plano]
        t_de = lambda k: sum(quadros[:k]) / 30.0
        total = sum(quadros) / 30.0
        cortes = [round(t_de(k), 3) for k, _ in inicios]
        grandes = [0.0] + [round(t_de(k), 3) for k, tipo in inicios if tipo in ("numero", "fecho")]
        final = round(t_de(inicios[-1][0]), 3)
        import trilha_impacto as TI
        wav = OUTMP4.with_suffix(".impacto.wav")
        if escolha == "DRAMA":
            import trilha_tensao as TT
            TI.grava(TT.arranjo(total, cortes, grandes, final), str(wav))
        else:
            TI.grava(TI.arranjo(total, cortes, grandes, final), str(wav))
        R.TRILHA = wav
        R.FADE_IN = 0.01                  # a pancada do gancho tem que soar no quadro zero
        print(f"trilha {escolha}: {total:.1f}s, cortes {cortes}, grandes {grandes}")
    dur = montar_video(pecas, OUTMP4)
    print(f"OK {OUTMP4}  {dur:.1f}s  {OUTMP4.stat().st_size / 1e6:.1f} MB")
    BP.grava_ficha(OUTMP4, "reels_materia.py", MATERIA, cartoes,
                   {"fecho_centralizado": True, "trilha": escolha if impacto else str(R.TRILHA), "duracao": round(dur, 2)})


if __name__ == "__main__":
    main()
