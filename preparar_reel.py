#!/usr/bin/env python3
"""Publica um Reels no Instagram pela API oficial da Meta (upload retomavel).

Uso: python3 publish_reel.py video.mp4 legenda.txt [--dry-run]
Precisa de IG_USER_ID e META_PAGE_TOKEN no ambiente.
"""
import os, sys, time, json, requests
from pathlib import Path

V = "v23.0"
G = f"https://graph.facebook.com/{V}"
RUP = f"https://rupload.facebook.com/ig-api-upload/{V}"
IG = os.environ["IG_USER_ID"]
TOK = os.environ["META_PAGE_TOKEN"]

video = Path(sys.argv[1])
caption = Path(sys.argv[2]).read_text(encoding="utf-8").strip()
dry = "--dry-run" in sys.argv

size = video.stat().st_size
print(f"video: {video.name}  {size/1e6:.1f} MB")
print(f"legenda: {len(caption)} caracteres")
if dry:
    print("[dry-run] parou aqui"); sys.exit(0)

# 1) container
r = requests.post(f"{G}/{IG}/media", data={
    "media_type": "REELS", "upload_type": "resumable",
    "caption": caption, "share_to_feed": "true", "access_token": TOK}, timeout=60)
r.raise_for_status()
cid = r.json()["id"]
print("container:", cid)

# 2) sobe os bytes
blob = video.read_bytes()          # em memoria: garante Content-Length correto
up = None
for tentativa in range(1, 4):
    up = requests.post(f"{RUP}/{cid}", headers={
        "Authorization": f"OAuth {TOK}", "offset": "0",
        "file_size": str(len(blob)), "Content-Type": "application/octet-stream"},
        data=blob, timeout=600)
    print(f"upload (tentativa {tentativa}):", up.status_code, up.text[:200])
    if up.ok:
        break
    time.sleep(8)
up.raise_for_status()

# 3) espera processar
for i in range(60):
    time.sleep(6)
    st = requests.get(f"{G}/{cid}", params={
        "fields": "status_code,status", "access_token": TOK}, timeout=30).json()
    sc = st.get("status_code")
    print(f"  [{i*6+6}s] {sc}")
    if sc == "FINISHED":
        break
    if sc == "ERROR":
        print("ERRO:", json.dumps(st, ensure_ascii=False)); sys.exit(1)
else:
    print("tempo esgotado no processamento"); sys.exit(1)

# 4) publica
print("CONTAINER PRONTO:", cid)
