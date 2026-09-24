#!/usr/bin/env python3
"""Busca leve no Commons (22/09): o gerador de busca com imageinfo+iiurlwidth levava
429 em rajada. Aqui: 1) busca de titulos pelo rest.php; 2) UMA chamada imageinfo
(sem iiurlwidth) com licenca/autor dos resultados. Uso: busca_leve.py "termo" [n]"""
import sys, re, time, requests
UA={"User-Agent":"PiscaNews/1.0 (https://www.instagram.com/pisca.news) python-requests/2"}
def get(u, **kw):
    for esp in (0, 20, 45, 70):
        if esp: time.sleep(esp)
        r=requests.get(u, headers=UA, timeout=60, **kw)
        if r.status_code==200 and "json" in (r.headers.get("content-type") or ""): return r.json()
        print("   (HTTP", r.status_code, "- esperando)")
    raise SystemExit("Commons nao respondeu")
termo=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 8
s=get("https://commons.wikimedia.org/w/rest.php/v1/search/page", params={"q":f"filetype:bitmap {termo}","limit":n})
tit=[p["title"] for p in s.get("pages",[]) if p["title"].startswith("File:")]
if not tit: print("nada"); raise SystemExit
time.sleep(2)
r=get("https://commons.wikimedia.org/w/api.php", params={"action":"query","format":"json","titles":"|".join(tit),
      "prop":"imageinfo","iiprop":"size|extmetadata","iiextmetadatafilter":"LicenseShortName|Artist"})
print("=== ", termo)
for p in r["query"]["pages"].values():
    ii=(p.get("imageinfo") or [{}])[0]; em=ii.get("extmetadata",{})
    lic=(em.get("LicenseShortName",{}) or {}).get("value","?")
    aut=re.sub(r"\s+"," ",re.sub("<[^>]+>","",(em.get("Artist",{}) or {}).get("value","?"))).strip()[:50]
    print(f'  [{lic}] {ii.get("width")}x{ii.get("height")} {aut}\n    {p["title"]}')
