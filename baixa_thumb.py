#!/usr/bin/env python3
"""Baixa miniatura padrao direto do servidor de thumbs (sem API).
Uso: baixa_thumb.py slug "Titulo do arquivo.jpg" largura"""
import sys, hashlib, time, requests, urllib.parse
from io import BytesIO
from PIL import Image
UA={"User-Agent":"PiscaNews/1.0 (https://www.instagram.com/pisca.news) python-requests/2"}
slug,tit,w=sys.argv[1],sys.argv[2],int(sys.argv[3])
nome=tit.replace(" ","_"); h=hashlib.md5(nome.encode()).hexdigest()
q=urllib.parse.quote(nome)
u=f"https://thumb.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{w}px-{q}"
for esp in (0,6,15,30):
    if esp: time.sleep(esp)
    r=requests.get(u,headers=UA,timeout=90)
    try:
        Image.open(BytesIO(r.content)).verify()
        open(f"photos/{slug}.jpg","wb").write(r.content)
        im=Image.open(f"photos/{slug}.jpg"); print(slug, im.size, len(r.content)//1024,"KB"); break
    except Exception:
        print(f"  {slug}: HTTP {r.status_code} ({len(r.content)} bytes)")
else: print(f"  {slug}: FALHOU")
