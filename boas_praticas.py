#!/usr/bin/env python3
"""Trava de boas práticas do Instagram (pedido dele, 23/09: "faça direito, tudo").

Os motores (reels.py, reels_materia.py) gravam, ao lado do vídeo, a FICHA <video>.ficha.json: de onde veio o conteúdo,
como cada foto entrou (tela cheia / composta / desenho / FAIXA) e quanto cada foto foi esticada. O publish_reel.py
chama confere_reels() antes de publicar e PARA se achar:
  - vídeo fora do padrão: 1080x1920, 30 qps, com áudio, menos de 3 min;
  - cartão com foto em FAIXA (foto numa tira com o resto da tela preenchido = "borda"; o Instagram deixa esses Reels
    menos descobertos) — sem exceção;
  - foto esticada mais de 2x (sai borrada; "baixa resolução" também derruba a recomendação) — só com FOTO_PEQUENA_OK=1;
  - notícia parecida com uma que já saiu (nao_repete.py) — só com NOVO_FATO=1.
Esticada entre 1,5x e 2x vira AVISO. Sem ficha (vídeo feito fora dos motores) vira AVISO.

Uso avulso (checagem antes de publicar): python3 boas_praticas.py video.mp4 legenda.txt
"""
import json, os, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
W, H = 1080, 1920
ESTICA_AVISO = 1.5
ESTICA_ERRO = 2.0


def _abs(p):
    p = Path(p)
    return p if p.is_absolute() else BASE / p


def tamanho(foto):
    from PIL import Image
    with Image.open(_abs(foto)) as im:
        return im.size


def escala(foto, caixa_w=W, caixa_h=H, zoom=1.0):
    """quanto a foto é ampliada para cobrir a caixa (object-fit: cover), já contando o zoom lento"""
    w, h = tamanho(foto)
    return max(caixa_w / w, caixa_h / h) * zoom


def aviso_foto(foto, caixa_w=W, caixa_h=H, zoom=1.0, rotulo=""):
    """None se a foto aguenta a caixa; senão o texto do aviso (começa com ERRO se passar de 2x)"""
    try:
        e = escala(foto, caixa_w, caixa_h, zoom)
        w, h = tamanho(foto)
    except Exception as ex:
        return f"ERRO {rotulo}: não abriu a foto {foto} ({ex})"
    if e > ESTICA_ERRO:
        return (f"ERRO {rotulo}: foto {Path(foto).name} ({w}x{h}) esticada {e:.1f}x numa caixa {caixa_w}x{caixa_h} "
                f"— vai sair borrada; baixe maior (1920 px) ou troque")
    if e > ESTICA_AVISO:
        return f"AVISO {rotulo}: foto {Path(foto).name} ({w}x{h}) esticada {e:.1f}x — prefira uma maior"
    return None


def grava_ficha(video, motor, fonte, cartoes, extras=None):
    """cartoes: [{"cartao": "gancho", "foto": caminho|None, "modo": "cheia"|"composta"|"desenho"|"faixa"|"sem foto",
    "escala": float|None, "aviso": str|None}]"""
    ficha = {"motor": motor, "fonte": str(_abs(fonte).resolve()), "cartoes": cartoes, **(extras or {})}
    destino = Path(str(video) + ".ficha.json")
    destino.write_text(json.dumps(ficha, ensure_ascii=False, indent=1), encoding="utf-8")
    faixas = [c["cartao"] for c in cartoes if c.get("modo") == "faixa"]
    avisos = [c["aviso"] for c in cartoes if c.get("aviso")]
    print(f"ficha de boas práticas: {destino.name} — {len(cartoes)} cartões"
          + (f"; FAIXA (borda) em {faixas}" if faixas else "; nenhum com borda")
          + (f"; {len(avisos)} aviso(s) de foto" if avisos else ""))
    for a in avisos:
        print("  " + a)
    return destino


def _ffprobe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def confere_reels(video, legenda=None, trava=True):
    """devolve (erros, avisos); com trava=True sai do programa se houver erro"""
    erros, avisos = [], []
    j = _ffprobe(video)
    vs = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]
    aus = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    dur = float(j.get("format", {}).get("duration", 0) or 0)
    if not vs:
        erros.append("sem trilha de vídeo")
    else:
        v = vs[0]
        if (v.get("width"), v.get("height")) != (W, H):
            erros.append(f"vídeo {v.get('width')}x{v.get('height')}; o padrão é {W}x{H} (9:16, tela cheia)")
        num, den = (v.get("r_frame_rate") or "0/1").split("/")
        fps = float(num) / float(den or 1)
        if fps < 29.5:
            erros.append(f"{fps:.1f} quadros por segundo; o padrão é 30")
    if not aus:
        erros.append("vídeo sem som (o padrão é a trilha de suspense da pasta musicas/)")
    if dur >= 180:
        erros.append(f"{dur:.0f} s: acima de 3 min o Instagram não recomenda para público novo")
    elif dur > 90:
        avisos.append(f"{dur:.0f} s: nosso padrão é 30 a 70 s")

    ficha_p = Path(str(video) + ".ficha.json")
    fonte = None
    if not ficha_p.exists():
        avisos.append("vídeo sem ficha do motor (feito fora do reels.py/reels_materia.py): conferir os quadros na mão")
    else:
        ficha = json.loads(ficha_p.read_text(encoding="utf-8"))
        fonte = ficha.get("fonte")
        if Path(video).stat().st_mtime - ficha_p.stat().st_mtime > 5:
            avisos.append("a ficha é mais velha que o vídeo: gere o vídeo de novo pelo motor")
        for c in ficha.get("cartoes", []):
            if c.get("modo") == "faixa":
                erros.append(f"cartão {c['cartao']}: foto em FAIXA (borda) — use foto em tela cheia")
            a = c.get("aviso") or ""
            if a.startswith("ERRO"):
                if os.environ.get("FOTO_PEQUENA_OK") == "1":
                    avisos.append(a + " (liberado com FOTO_PEQUENA_OK=1)")
                else:
                    erros.append(a)
            elif a:
                avisos.append(a)
        if not ficha.get("fecho_centralizado", False):
            erros.append("cartão final não está centralizado")

    # notícia repetida: pela fonte do conteúdo (manchetes) ou, sem ela, pela legenda
    import nao_repete as NR
    textos = NR.manchetes(_abs(fonte)) if fonte and _abs(fonte).exists() else (NR.manchetes(legenda) if legenda else [])
    rep = NR.parecidas(textos)
    for nova, antiga, quando, comum in rep:
        msg = f"parece notícia que já saiu: \"{nova}\" ~ \"{antiga}\" ({quando}; em comum: {', '.join(comum)})"
        if os.environ.get("NOVO_FATO") == "1":
            avisos.append(msg + " (liberado com NOVO_FATO=1)")
        else:
            erros.append(msg)

    for a in avisos:
        print("AVISO boas práticas:", a)
    for e in erros:
        print("ERRO boas práticas:", e)
    if not erros:
        print(f"boas práticas: OK ({dur:.1f} s, {W}x{H}, som, {len(avisos)} aviso(s))")
    if erros and trava:
        raise SystemExit("publicação travada pelas boas práticas (boas_praticas.py) — corrija e gere de novo")
    return erros, avisos


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    e, _ = confere_reels(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, trava=False)
    sys.exit(1 if e else 0)
