#!/usr/bin/env python3
"""Busca no Wikimedia Commons e mostra candidatos com licenca e autor."""
import sys, json, time, re, requests
UA = {"User-Agent": "PiscaNews/1.0 (contato via instagram @pisca.news)"}
API = "https://commons.wikimedia.org/w/api.php"

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


def busca(termo, n=6):
    r = pede({
        "action":"query","format":"json","generator":"search",
        "gsrsearch": f'filetype:bitmap {termo}', "gsrnamespace":6, "gsrlimit":n,
        "prop":"imageinfo","iiprop":"url|extmetadata|size",
        "iiurlwidth": 1400})
    out=[]
    for p in (r.get("query",{}).get("pages") or {}).values():
        ii=p["imageinfo"][0]; em=ii.get("extmetadata",{})
        lic=(em.get("LicenseShortName",{}) or {}).get("value","?")
        aut=(em.get("Artist",{}) or {}).get("value","?")
        aut=re.sub("<[^>]+>","",aut).strip()[:60]
        out.append({"title":p["title"],"url":ii.get("thumburl") or ii["url"],
                    "w":ii.get("width"),"h":ii.get("height"),"lic":lic,"aut":aut})
    return out

for termo in sys.argv[1:]:
    print("=== ", termo)
    for c in busca(termo):
        print(f'  [{c["lic"]}] {c["w"]}x{c["h"]} {c["aut"]}\n    {c["title"]}\n    {c["url"]}')
