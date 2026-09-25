#!/usr/bin/env python3
"""UM comando publica em TODAS as redes (24/09/2026, pedido dele: "quando for lançar 1, lançar em todos").

  python3 publica_tudo.py carrossel out_xxx                 # Instagram + Facebook + stories, depois Threads
  python3 publica_tudo.py reels video.mp4 legenda.txt       # Instagram + collab + Facebook + stories, depois Threads,
                                                            # YouTube Shorts e TikTok
Cada rede extra só roda quando tem ACESSO (chave no .pisca_env) e REDE liberada; senão imprime "PENDENTE: motivo" e
segue — nunca derruba as outras. As travas (repetição, foto repetida, legenda, sem borda) continuam nos publicadores.

Chaves esperadas no /home/claude/.pisca_env (nunca escrever na resposta):
  THREADS_USER_ID, THREADS_TOKEN                         (Threads, app da Meta com caso de uso Threads)
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN       (YouTube Data API v3, canal do Pisca)
  TIKTOK_TOKEN                                           (TikTok Content Posting API; privado até a auditoria do app)
Rede: graph.threads.net, oauth2.googleapis.com, www.googleapis.com, open.tiktokapis.com liberados no allowlist.
"""
import os, re, sys, json, time, subprocess, requests
from pathlib import Path

BASE = Path(__file__).resolve().parent
G = "https://graph.facebook.com/v23.0"
E = os.environ.get


def rede_ok(url):
    try:
        requests.get(url, timeout=10)
        return True
    except Exception:
        return False


def pendente(rede, motivo):
    print(f"PENDENTE {rede}: {motivo}")
    return None


def ig_ultimo():
    """o post que acabou de sair no Instagram, com as URLs públicas da mídia (servem para o Threads)"""
    r = requests.get(f"{G}/{E('IG_USER_ID')}/media", params={
        "fields": "id,media_type,permalink,media_url,thumbnail_url,children{media_type,media_url}", "limit": 1,
        "access_token": E("META_PAGE_TOKEN")}, timeout=60).json()
    return r["data"][0]


# ---------------------------------------------------------------- Threads
def texto_threads(legenda, lim=500):
    """Threads aceita 500 caracteres e 1 tag: mantém os blocos da legenda que couberem, na ordem, sem cortar frase;
    tira as hashtags e fecha com a linha das fontes resumida se couber."""
    blocos = [b.strip() for b in legenda.split("\n\n") if b.strip() and not b.strip().startswith("#")]
    fontes = next((b for b in blocos if b.startswith("Fontes")), None)
    out = []
    for b in blocos:
        if b is fontes or b.startswith("📷"):
            continue
        if len("\n\n".join(out + [b])) > lim - 40:
            linhas = []
            for l in b.splitlines():                      # lista longa: entra até onde couber
                if len("\n\n".join(out + ["\n".join(linhas + [l])])) > lim - 40:
                    break
                linhas.append(l)
            if linhas:
                out.append("\n".join(linhas))
            break
        out.append(b)
    txt = "\n\n".join(out)
    if fontes and len(txt) + len(fontes) + 2 <= lim:
        txt += "\n\n" + fontes
    return txt[:lim]


def midia_publica(video):
    """Hospeda o vídeo no repositório PÚBLICO jmiguevf/pisca-midia (release "midia") e devolve a URL direta.
    O Threads não baixa o vídeo do CDN do Instagram/Facebook (24/09: status ERROR); de um link público nosso, baixa."""
    tok, repo = E("MIDIA_TOKEN"), E("MIDIA_REPO", "jmiguevf/pisca-midia")
    if not tok or not video:
        return None
    H = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/midia", headers=H, timeout=60)
    if r.status_code == 404:
        r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=H, timeout=60,
                          json={"tag_name": "midia", "name": "Mídia do Pisca", "body": "Vídeos publicados pelo Pisca."})
    rel = r.json()
    nome = time.strftime("%Y%m%d-%H%M%S-") + Path(video).name
    up = requests.post(f"https://uploads.github.com/repos/{repo}/releases/{rel['id']}/assets", params={"name": nome},
                       headers={**H, "Content-Type": "video/mp4"}, data=Path(video).read_bytes(), timeout=600)
    up.raise_for_status()
    url = up.json()["browser_download_url"]
    fim = requests.head(url, allow_redirects=True, timeout=60).url      # o link final (sem redirecionamento)
    return fim or url


def threads(legenda, ig, video=None):
    if not (E("THREADS_USER_ID") and E("THREADS_TOKEN")):
        return pendente("Threads", "falta a chave de acesso do Threads")
    if not rede_ok("https://graph.threads.net"):
        return pendente("Threads", "graph.threads.net bloqueado na rede")
    T, U, TH = E("THREADS_TOKEN"), E("THREADS_USER_ID"), "https://graph.threads.net/v1.0"
    texto = texto_threads(legenda)                      # limite do Threads: 500 caracteres
    def cria(**p):
        p["access_token"] = T
        j = requests.post(f"{TH}/{U}/threads", data=p, timeout=120).json()
        if "id" not in j:
            raise RuntimeError(j)
        return j["id"]
    if ig["media_type"] == "CAROUSEL_ALBUM":
        filhos = [cria(media_type="IMAGE", image_url=c["media_url"], is_carousel_item="true")
                  for c in ig["children"]["data"][:20]]
        for f in filhos:                                 # 24/09: cada filho precisa terminar antes do carrossel
            for _ in range(30):
                st = requests.get(f"{TH}/{f}", params={"fields": "status", "access_token": T}, timeout=60).json()
                if st.get("status") in ("FINISHED", None):
                    break
                if st.get("status") == "ERROR":
                    raise RuntimeError(st)
                time.sleep(3)
        cid = cria(media_type="CAROUSEL", children=",".join(filhos), text=texto)
    else:
        # 24/09: vídeo pela URL do Instagram/Facebook deu status ERROR no Threads (não baixa do CDN deles).
        # 1º: vídeo de verdade, hospedado no pisca-midia (público). Se falhar: capa do Reels + link do vídeo.
        try:
            url = midia_publica(video)
            if url:
                cid = cria(media_type="VIDEO", video_url=url, text=texto)
                for _ in range(50):
                    st = requests.get(f"{TH}/{cid}", params={"fields": "status,error_message", "access_token": T},
                                      timeout=60).json()
                    if st.get("status") == "FINISHED":
                        j = requests.post(f"{TH}/{U}/threads_publish", data={"creation_id": cid, "access_token": T},
                                          timeout=120).json()
                        link = requests.get(f"{TH}/{j['id']}", params={"fields": "permalink", "access_token": T},
                                            timeout=60).json()
                        print("THREADS (vídeo):", link.get("permalink", j["id"]))
                        return j["id"]
                    if st.get("status") == "ERROR":
                        print("Threads recusou o vídeo:", st.get("error_message"), "- vai capa + link")
                        break
                    time.sleep(6)
        except Exception as e:
            print("Threads vídeo falhou:", str(e)[:200], "- vai capa + link")
        link = f"\n\n🎬 Vídeo: {ig.get('permalink','')}"
        corpo = texto[:500 - len(link)]
        corpo = corpo[:corpo.rfind("\n")] if len(texto) > 500 - len(link) and "\n" in corpo else corpo
        cid = cria(media_type="IMAGE", image_url=ig.get("thumbnail_url") or ig["media_url"], text=corpo + link)
    for _ in range(40):                                  # vídeo precisa terminar de processar
        st = requests.get(f"{TH}/{cid}", params={"fields": "status", "access_token": T}, timeout=60).json()
        if st.get("status") in ("FINISHED", None):
            break
        if st.get("status") == "ERROR":
            raise RuntimeError(st)
        time.sleep(6)
    j = requests.post(f"{TH}/{U}/threads_publish", data={"creation_id": cid, "access_token": T}, timeout=120).json()
    link = requests.get(f"{TH}/{j['id']}", params={"fields": "permalink", "access_token": T}, timeout=60).json()
    print("THREADS:", link.get("permalink", j["id"]))
    return j["id"]


# ---------------------------------------------------------------- YouTube Shorts
def youtube(video, legenda):
    if not (E("YT_CLIENT_ID") and E("YT_CLIENT_SECRET") and E("YT_REFRESH_TOKEN")):
        return pendente("YouTube", "falta a autorização do canal do Pisca")
    if not rede_ok("https://www.googleapis.com"):
        return pendente("YouTube", "googleapis.com bloqueado na rede")
    tok = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": E("YT_CLIENT_ID"), "client_secret": E("YT_CLIENT_SECRET"),
        "refresh_token": E("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=60).json()["access_token"]
    linhas = [l for l in legenda.splitlines() if l.strip()]
    base = re.sub(r"[<>]", "", linhas[0]).strip() if linhas else "Pisca"
    titulo = (base[:88].rstrip() + " #Shorts")   # YouTube: até 100 caracteres, sem < >
    meta = {"snippet": {"title": titulo, "description": legenda[:4900], "categoryId": "25"},   # 25 = Notícias
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    ini = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                                 "X-Upload-Content-Type": "video/mp4"}, data=json.dumps(meta), timeout=60)
    ini.raise_for_status()
    up = requests.put(ini.headers["Location"], headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"},
                      data=Path(video).read_bytes(), timeout=600)
    up.raise_for_status()
    vid = up.json()["id"]
    print("YOUTUBE:", f"https://www.youtube.com/shorts/{vid}")
    try:   # app do Google sem auditoria: o YouTube pode travar o vídeo como privado
        st = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "status", "id": vid},
                          headers={"Authorization": f"Bearer {tok}"}, timeout=60).json()["items"][0]["status"]
        if st.get("privacyStatus") != "public":
            pendente("YouTube", f"o vídeo subiu como {st.get('privacyStatus')} (o YouTube trava apps sem auditoria); "
                                "dá para deixar público no YouTube Studio")
    except Exception:
        pass
    return vid


# ---------------------------------------------------------------- TikTok
def tiktok(video, legenda):
    if not E("TIKTOK_TOKEN"):
        return pendente("TikTok", "falta o app aprovado do TikTok")
    if not rede_ok("https://open.tiktokapis.com"):
        return pendente("TikTok", "open.tiktokapis.com bloqueado na rede")
    H = {"Authorization": f"Bearer {E('TIKTOK_TOKEN')}", "Content-Type": "application/json; charset=UTF-8"}
    info = requests.post("https://open.tiktokapis.com/v2/post/publish/creator_info/query/", headers=H, timeout=60).json()
    niveis = info.get("data", {}).get("privacy_level_options", ["SELF_ONLY"])
    nivel = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in niveis else niveis[0]   # sem auditoria: só privado
    tam = Path(video).stat().st_size
    j = requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/", headers=H, json={
        "post_info": {"title": legenda[:2200], "privacy_level": nivel},
        "source_info": {"source": "FILE_UPLOAD", "video_size": tam, "chunk_size": tam, "total_chunk_count": 1}},
        timeout=60).json()
    url = j["data"]["upload_url"]
    requests.put(url, headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{tam-1}/{tam}"},
                 data=Path(video).read_bytes(), timeout=600).raise_for_status()
    print("TIKTOK: enviado", f"({nivel})", j["data"].get("publish_id"))
    return j["data"].get("publish_id")


def extra(nome, f, *a):
    try:
        return f(*a)
    except Exception as e:
        print(f"FALHOU {nome}:", str(e)[:300])


def main():
    tipo = sys.argv[1]
    if tipo == "carrossel":
        pasta = Path(sys.argv[2])
        subprocess.run([sys.executable, str(BASE / "publish.py"), str(pasta)] + sys.argv[3:], check=True)
        legenda = (pasta / "caption.txt").read_text(encoding="utf-8")
        extra("Threads", threads, legenda, ig_ultimo())
        pendente("TikTok (carrossel)", "post de fotos no TikTok precisa de domínio verificado; por ora só vídeo")
    elif tipo == "reels":
        video, leg = sys.argv[2], sys.argv[3]
        subprocess.run([sys.executable, str(BASE / "publish_reel.py"), video, leg] + sys.argv[4:], check=True)
        legenda = Path(leg).read_text(encoding="utf-8")
        extra("Threads", threads, legenda, ig_ultimo(), video)
        extra("YouTube", youtube, video, legenda)
        extra("TikTok", tiktok, video, legenda)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
