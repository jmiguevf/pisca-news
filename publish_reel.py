#!/usr/bin/env python3
"""Publica um Reels no Instagram pela API oficial da Meta (upload retomavel).

Uso: python3 publish_reel.py video.mp4 legenda.txt [--dry-run]
Precisa de IG_USER_ID e META_PAGE_TOKEN no ambiente.
"""
import os, sys, time, json, requests
from pathlib import Path

# 23/09: Reels de teste (trial_params) e colaborador (collaborators) pela API oficial.
#   TRIAL=MANUAL ou TRIAL=SS_PERFORMANCE -> vai primeiro para quem NAO segue a pagina;
#     SS_PERFORMANCE libera sozinho para os seguidores se for bem; MANUAL, so pelo app.
#   COLLAB=usuario1,usuario2 -> convite de collab (a pessoa aceita no app; ate 3).
#   trial_params esta documentado na v25.0: com TRIAL, a versao sobe para v25.0.
TRIAL = os.environ.get("TRIAL", "").strip().upper()
COLLAB = [u.strip().lstrip("@") for u in os.environ.get("COLLAB", "").split(",") if u.strip()]
V = os.environ.get("GRAPH_V") or ("v25.0" if TRIAL else "v23.0")
G = f"https://graph.facebook.com/{V}"
RUP = f"https://rupload.facebook.com/ig-api-upload/{V}"
IG = os.environ["IG_USER_ID"]
TOK = os.environ["META_PAGE_TOKEN"]

video = Path(sys.argv[1])
caption = Path(sys.argv[2]).read_text(encoding="utf-8").strip()
sys.path.insert(0, str(Path(__file__).parent))
import regras_legenda
regras_legenda.aplica(caption, "reels")
# boas praticas: Reels com mais de 3 min nao vai para publico novo
import subprocess as _sp
_dur = float(_sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", sys.argv[1]],
                     capture_output=True, text=True).stdout.strip() or 0)
if _dur >= 180:
    sys.exit(f"Reels com {_dur:.0f}s: acima de 3 min o Instagram nao recomenda para publico novo")
# 24/09 ("faça direito, tudo"): trava de boas práticas — 1080x1920/30 qps/som, sem BORDA (ficha do motor), foto sem
# esticar demais, fecho centralizado e notícia que não repete (boas_praticas.py + nao_repete.py)
import boas_praticas as BP
BP.confere_reels(str(video), sys.argv[2])
try:                                        # 24/09: foto que já saiu trava (pelo json da ficha)
    import foto_repete as FR
    _f0 = json.loads(Path(str(video) + ".ficha.json").read_text(encoding="utf-8")).get("fonte")
    if _f0 and Path(_f0).exists():
        FR.trava(_f0)
except SystemExit:
    raise
except Exception as e:
    print("checagem de foto repetida falhou:", e)
dry = "--dry-run" in sys.argv

size = video.stat().st_size
print(f"video: {video.name}  {size/1e6:.1f} MB")
print(f"legenda: {len(caption)} caracteres")
if dry:
    print("[dry-run] parou aqui"); sys.exit(0)

# 1) container
# 22/09: o script nunca definia a capa, e o Instagram usava o quadro zero — que em
# todos os Reels ate hoje era o texto entrando, apagado e com imagem dupla. Agora a
# capa e escolhida (THUMB_MS, padrao 1200 ms: o gancho ja assentado).
import os as _os
THUMB_MS = int(_os.environ.get("THUMB_MS", "1200"))
print(f"capa: quadro em {THUMB_MS} ms")
dados = {"media_type": "REELS", "upload_type": "resumable",
         "caption": caption, "share_to_feed": "true", "thumb_offset": str(THUMB_MS),
         "access_token": TOK}
if TRIAL:
    if TRIAL not in ("MANUAL", "SS_PERFORMANCE"):
        sys.exit(f"TRIAL invalido: {TRIAL} (use MANUAL ou SS_PERFORMANCE)")
    dados["trial_params"] = json.dumps({"graduation_strategy": TRIAL})
    print(f"Reels de TESTE: graduation_strategy={TRIAL} (API {V})")
if COLLAB:
    dados["collaborators"] = json.dumps(COLLAB[:3])
    print("convite de collab para:", ", ".join(COLLAB[:3]))
r = requests.post(f"{G}/{IG}/media", data=dados, timeout=60)
if not r.ok:
    print("ERRO no container:", r.text[:400])
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
pub = requests.post(f"{G}/{IG}/media_publish", data={
    "creation_id": cid, "access_token": TOK}, timeout=120)
pub.raise_for_status()
mid = pub.json()["id"]

link = requests.get(f"{G}/{mid}", params={
    "fields": "permalink", "access_token": TOK}, timeout=30).json().get("permalink", "")
print("PUBLICADO:", link or mid)
try:                                        # 24/09: entra no histórico de não repetir
    import nao_repete as NR
    _ficha = Path(str(video) + ".ficha.json")
    _fonte = json.loads(_ficha.read_text(encoding="utf-8")).get("fonte") if _ficha.exists() else None
    _fp = (Path(__file__).resolve().parent / _fonte) if _fonte and not Path(_fonte).is_absolute() else (Path(_fonte) if _fonte else None)
    NR.registra(NR.manchetes(_fp) if _fp and _fp.exists() else NR.manchetes(sys.argv[2]), NR._hora_brt())
    if _fp and _fp.exists():
        import foto_repete as FR            # 24/09: fotos do Reels entram no histórico
        FR.registra(_fp, Path(str(video)).name)
except Exception as e:
    print("histórico de não repetir falhou:", e)

# 23/09: "sempre que vc for publicar um reels, compartilhe tbm no facebook e no story"
# (COMPARTILHAR=0 desliga; Reels de teste nao se compartilha, porque e para quem nao segue)
if os.environ.get("COMPARTILHAR", "1") != "0" and not TRIAL:
    import compartilha_reel as C
    try:
        C.facebook_reel(str(video), caption)
    except Exception as e:
        print("Facebook falhou:", e)
    try:
        C.instagram_story(str(video))
    except Exception as e:
        print("Story falhou:", e)
    try:                                   # 23/09: story também no Facebook
        C.facebook_story_video(str(video))
    except Exception as e:
        print("Story do Facebook falhou:", e)
