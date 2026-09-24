#!/usr/bin/env python3
import sys, re, time, requests
from pathlib import Path
UA={"User-Agent":"PiscaNews/1.0 (contato via instagram @pisca.news)"}
API="https://commons.wikimedia.org/w/api.php"

def pede(params, tentativas=6):
    """GET no Commons com espera-e-repete. A API devolve 429 quando a gente
    aperta demais — nesse caso ela manda texto puro, nao JSON, e o .json()
    estoura. Entao a gente espera (2s, 4s, 8s, 16s, 32s) e tenta de novo."""
    espera = 2
    for t in range(tentativas):
        try:
            r = requests.get(API, params=params, headers=UA, timeout=60)
            if r.status_code == 429 or "json" not in (r.headers.get("content-type") or ""):
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:80]}")
            return r.json()
        except Exception as e:
            if t == tentativas - 1:
                raise RuntimeError(f"Commons nao respondeu depois de {tentativas} tentativas: {e}")
            time.sleep(espera); espera = min(espera * 2, 32)

DEST=Path("photos"); DEST.mkdir(exist_ok=True)
def info(titulo):
    # 22/09: pedir 1700px forcava o Commons a gerar a miniatura na hora (1700 nao
    # e tamanho padrao) — era a causa dos 429 repetidos. Primeiro descobre a
    # largura original; depois pede o MAIOR tamanho padrao que nao passa dela.
    r0=pede({"action":"query","format":"json","titles":"File:"+titulo,
             "prop":"imageinfo","iiprop":"size"})
    w0=list(r0["query"]["pages"].values())[0]["imageinfo"][0]["width"]
    larg=next((x for x in (1920,1280,1024,960,800,640,500) if x<=w0), 500)
    r=pede({"action":"query","format":"json","titles":"File:"+titulo,
            "prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":larg})
    p=list(r["query"]["pages"].values())[0]; ii=p["imageinfo"][0]; em=ii.get("extmetadata",{})
    aut=re.sub("<[^>]+>","",(em.get("Artist",{}) or {}).get("value","")).strip()
    aut=re.sub(r"\s+"," ",aut)[:44]
    lic=(em.get("LicenseShortName",{}) or {}).get("value","")
    url = ii.get("thumburl")
    if not url or "upload.wikimedia.org" in url:
        # imagem menor que o thumb pedido: peca um thumb menor, porque o upload direto e bloqueado
        w2 = max(400, int(ii["width"] * 0.9))
        r2 = pede({"action":"query","format":"json","titles":"File:"+titulo,
                   "prop":"imageinfo","iiprop":"url","iiurlwidth":w2})
        url = list(r2["query"]["pages"].values())[0]["imageinfo"][0].get("thumburl")
    return url, aut, lic, ii["width"], ii["height"]
for arg in sys.argv[1:]:
    slug, titulo = arg.split("|",1)
    url,aut,lic,w,h = info(titulo)
    # 22/09: duas vezes no mesmo dia o Commons devolveu a pagina de erro 429 e o
    # script salvou esse texto como .jpg (2 KB). Agora so grava se abrir como
    # imagem de verdade; senao espera e tenta de novo.
    from io import BytesIO
    from PIL import Image as _Im
    b = None
    for tent, espera in enumerate((0, 8, 20, 40)):
        if espera: time.sleep(espera)
        r = requests.get(url, headers=UA, timeout=120)
        try:
            _Im.open(BytesIO(r.content)).verify()
            b = r.content; break
        except Exception:
            print(f'   {slug}: resposta nao e imagem (HTTP {r.status_code}, {len(r.content)} bytes) — tentando de novo')
    if b is None:
        print(f'   {slug}: FALHOU — nada gravado'); continue
    out=DEST/f"{slug}.jpg"; out.write_bytes(b)
    print(f'{slug}: {w}x{h} r={w/h:.2f} {len(b)//1024}KB')
    print(f'   credito: Foto: {aut} / {lic} (Wikimedia Commons)')
