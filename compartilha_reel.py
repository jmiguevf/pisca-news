#!/usr/bin/env python3
"""Depois de publicar um Reels no Instagram, compartilha TAMBÉM no Facebook e no Story (regra do
José Miguel, 23/09/2026: "sempre que vc for publicar um reels, compartilhe tbm no facebook e no story").
Tudo pela API oficial da Meta (nada de navegador).

Uso: python3 compartilha_reel.py video.mp4 legenda.txt [--so-fb | --so-story | --so-fb-story]
     python3 compartilha_reel.py --carrossel out_xxx      # stories (Instagram + Facebook) de um carrossel
Precisa de IG_USER_ID, FB_PAGE_ID e META_PAGE_TOKEN no ambiente (.pisca_env).

- Facebook: Reels da Página pela API de Reels (video_reels: start -> upload -> finish).
- Story: o próprio vídeo se tiver até 59 s; se passar disso (limite de Story na API é 60 s), um trailer:
  os primeiros 14 s do Reels + 3 s de cartão "O Reels completo está no perfil".
"""
import os, sys, time, json, subprocess, tempfile
from pathlib import Path
import requests

V = "v23.0"
G = f"https://graph.facebook.com/{V}"
TOK = os.environ["META_PAGE_TOKEN"]
IG = os.environ["IG_USER_ID"]
PAGE = os.environ["FB_PAGE_ID"]
BASE = Path(__file__).parent


def duracao(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


# ------------------------------------------------------------------ Facebook
def facebook_reel(video, legenda):
    blob = Path(video).read_bytes()
    r = requests.post(f"{G}/{PAGE}/video_reels", data={"upload_phase": "start", "access_token": TOK}, timeout=60)
    if not r.ok:
        print("FB start ERRO:", r.text[:300]); return None
    vid = r.json()["video_id"]
    up = requests.post(f"https://rupload.facebook.com/video-upload/{V}/{vid}",
                       headers={"Authorization": f"OAuth {TOK}", "offset": "0", "file_size": str(len(blob))},
                       data=blob, timeout=600)
    print("FB upload:", up.status_code, up.text[:120])
    if not up.ok:
        return None
    fin = requests.post(f"{G}/{PAGE}/video_reels", data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": legenda, "access_token": TOK}, timeout=120)
    print("FB finish:", fin.status_code, fin.text[:200])
    if not fin.ok:
        return None
    link = ""
    for i in range(40):
        time.sleep(6)
        st = requests.get(f"{G}/{vid}", params={"fields": "status,permalink_url", "access_token": TOK}, timeout=30).json()
        s = st.get("status", {})
        fase = (s.get("publishing_phase") or {}).get("status")
        print(f"  FB [{i*6+6}s] video={s.get('video_status')} publicacao={fase}")
        link = st.get("permalink_url", "") or link
        if fase == "complete" or s.get("video_status") == "ready" and fase in (None, "complete"):
            break
        if s.get("video_status") == "error":
            print("FB ERRO no processamento:", json.dumps(s)[:300]); return None
    if link and link.startswith("/"):
        link = "https://www.facebook.com" + link
    print("FACEBOOK:", link or vid)
    return link or vid


# ------------------------------------------------------------------ Story
def cartao_final(png):
    """cartao de 1080x1920 no estilo do Pisca: 'O Reels completo está no perfil'"""
    sys.path.insert(0, str(BASE))
    import reels as R
    from playwright.sync_api import sync_playwright
    html = R.page(f"""<div class="card"><div class="safe hero" style="left:{(R.W - 712) // 2}px">
  <div class="bigmark">{R.EYE}</div>
  <div class="big">O Reels completo<br>está no perfil</div>
  <div class="line"></div>
  <div class="sub2">Toque no nome da página e assista até o fim.</div>
  <div class="h2">@pisca.news</div>
</div></div>""")
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": R.W, "height": R.H})
        pg.set_content(html, wait_until="load"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(150)
        pg.screenshot(path=str(png)); br.close()


def trailer(video, saida, corte=14.0, fim=3.0):
    tmp = Path(tempfile.mkdtemp())
    png = tmp / "fim.png"
    cartao_final(png)
    total = corte + fim
    filt = (f"[0:v]trim=0:{corte},setpts=PTS-STARTPTS,fps=30,format=yuv420p[a];"
            f"[1:v]scale=1080:1920,fps=30,format=yuv420p,trim=0:{fim},setpts=PTS-STARTPTS[b];"
            f"[a][b]concat=n=2:v=1:a=0[v];"
            f"[0:a]atrim=0:{total},asetpts=PTS-STARTPTS,afade=t=out:st={total - 1.2}:d=1.2[au]")
    tem_audio = "audio" in subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                                           "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-loop", "1", "-t", str(fim), "-i", str(png)]
    if tem_audio:
        cmd += ["-filter_complex", filt, "-map", "[v]", "-map", "[au]", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-filter_complex", filt.rsplit(";", 1)[0], "-map", "[v]"]
    cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30",
            "-movflags", "+faststart", str(saida)]
    subprocess.run(cmd, check=True)
    return saida


def codifica_story(origem, saida, teto_kbps=None):
    """23/09: o Story recusou o mp4 do Reels ("ProcessingFailedError" no upload). Reencodado assim passou:
    H.264 Main 4.0, GOP de 1 s sem B-frames, AAC 48 kHz, moov na frente e SEM edit list.
    23/09 tarde: o do Trump (53 s, 11,5 MB, 1,7 Mbps) caiu no mesmo erro duas vezes; o do prêmio que passou
    tinha 38 s e 5,2 MB (1,1 Mbps). teto_kbps limita a taxa (arquivo menor) na 2ª tentativa."""
    v = ["-crf", "21"] if not teto_kbps else ["-b:v", f"{teto_kbps}k", "-maxrate", f"{teto_kbps}k",
                                               "-bufsize", f"{teto_kbps * 2}k"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origem), "-c:v", "libx264", "-profile:v", "main",
                    "-level", "4.0", "-pix_fmt", "yuv420p", "-r", "30", "-g", "30", "-bf", "0"] + v +
                   ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k", "-movflags", "+faststart",
                    "-use_editlist", "0", str(saida)], check=True)
    return Path(saida)


def _sobe_story(arquivo):
    """cria o container de STORIES, sobe o arquivo e espera o processamento. Devolve o id ou None."""
    r = requests.post(f"{G}/{IG}/media", data={"media_type": "STORIES", "upload_type": "resumable",
                                               "access_token": TOK}, timeout=60)
    if not r.ok:
        print("Story container ERRO:", r.text[:300]); return None
    cid = r.json()["id"]
    blob = Path(arquivo).read_bytes()
    up = requests.post(f"https://rupload.facebook.com/ig-api-upload/{V}/{cid}",
                       headers={"Authorization": f"OAuth {TOK}", "offset": "0", "file_size": str(len(blob))},
                       data=blob, timeout=600)
    print(f"Story upload ({len(blob) / 1e6:.1f} MB, {duracao(arquivo):.1f}s):", up.status_code, up.text[:120])
    if not up.ok:
        return None
    for i in range(50):
        time.sleep(6)
        st = requests.get(f"{G}/{cid}", params={"fields": "status_code,status", "access_token": TOK}, timeout=30).json()
        sc = st.get("status_code")
        print(f"  Story [{i*6+6}s] {sc}")
        if sc == "FINISHED":
            return cid
        if sc == "ERROR":
            print("Story ERRO:", json.dumps(st)[:300]); return None
    return None


def instagram_story(video):
    """tenta: 1) o Reels inteiro (se couber em 59 s); 2) o mesmo com taxa limitada (arquivo menor);
    3) trailer de 14 s + cartão "O Reels completo está no perfil". Publica só a primeira que passar."""
    d = duracao(video)
    pasta = Path(tempfile.mkdtemp())
    tentativas = []
    if d <= 59.0:
        tentativas.append(("inteiro", Path(video), None))
        tentativas.append(("inteiro, taxa limitada", Path(video), 900))
    tentativas.append(("trailer", None, None))
    cid = None
    for nome, origem, teto in tentativas:
        if origem is None:
            origem = pasta / "story_trailer.mp4"
            trailer(video, origem)
            print(f"Story: trailer de {duracao(origem):.1f}s (Reels tem {d:.1f}s)")
        arquivo = codifica_story(origem, pasta / f"story_{len(str(teto))}_{nome[:3]}.mp4", teto)
        print(f"Story: tentativa '{nome}'")
        cid = _sobe_story(arquivo)
        if cid:
            break
    if not cid:
        print("Story: nenhuma tentativa passou"); return None
    pub = requests.post(f"{G}/{IG}/media_publish", data={"creation_id": cid, "access_token": TOK}, timeout=120)
    print("Story publish:", pub.status_code, pub.text[:200])
    if not pub.ok:
        return None
    sid = pub.json().get("id")
    print("STORY publicado:", sid)
    return sid


# ------------------------------------------------------------------ Stories do FACEBOOK (23/09)
# Regra dele: "dá pra fazer todas as publicações como story tbm, tanto no instagram quanto no facebook? se sim já registre".
# API de Stories de Páginas: /{page}/video_stories (start -> upload -> finish) e /{page}/photo_stories (photo_id).
def _versao_story(video):
    """o vídeo pronto para story (até 59 s; se passar, trailer de 14 s + cartão), no encode que o Story aceita"""
    pasta = Path(tempfile.mkdtemp())
    origem = Path(video)
    if duracao(video) > 59.0:
        origem = pasta / "story_trailer.mp4"
        trailer(video, origem)
    return codifica_story(origem, pasta / "story_fb.mp4")


def facebook_story_video(video):
    arq = _versao_story(video)
    r = requests.post(f"{G}/{PAGE}/video_stories", data={"upload_phase": "start", "access_token": TOK}, timeout=60)
    if not r.ok:
        print("FB story start ERRO:", r.text[:300]); return None
    j = r.json()
    vid = j["video_id"]
    url = j.get("upload_url") or f"https://rupload.facebook.com/video-upload/{V}/{vid}"
    blob = arq.read_bytes()
    up = requests.post(url, headers={"Authorization": f"OAuth {TOK}", "offset": "0", "file_size": str(len(blob))},
                       data=blob, timeout=600)
    print("FB story upload:", up.status_code, up.text[:120])
    if not up.ok:
        return None
    fin = requests.post(f"{G}/{PAGE}/video_stories", data={"upload_phase": "finish", "video_id": vid,
                                                            "access_token": TOK}, timeout=120)
    print("FB story finish:", fin.status_code, fin.text[:200])
    if not fin.ok:
        return None
    pid = fin.json().get("post_id") or vid
    print("STORY FACEBOOK publicado:", pid)
    return pid


def _foto_nao_publicada(img):
    with open(img, "rb") as f:
        r = requests.post(f"{G}/{PAGE}/photos", files={"source": (Path(img).name, f, "image/jpeg")},
                          data={"published": "false", "access_token": TOK}, timeout=120)
    r.raise_for_status()
    pid = r.json()["id"]
    info = requests.get(f"{G}/{pid}", params={"fields": "images", "access_token": TOK}, timeout=60).json()
    url = sorted(info["images"], key=lambda x: x.get("width", 0), reverse=True)[0]["source"]
    return pid, url


def facebook_story_foto(img):
    pid, _ = _foto_nao_publicada(img)
    r = requests.post(f"{G}/{PAGE}/photo_stories", data={"photo_id": pid, "access_token": TOK}, timeout=120)
    print("FB story (foto):", r.status_code, r.text[:200])
    if not r.ok:
        return None
    sid = r.json().get("post_id") or pid
    print("STORY FACEBOOK publicado:", sid)
    return sid


def instagram_story_foto(img):
    """story de IMAGEM no Instagram (a API pede URL pública: hospeda como foto não publicada da Página)"""
    _, url = _foto_nao_publicada(img)
    r = requests.post(f"{G}/{IG}/media", data={"media_type": "STORIES", "image_url": url, "access_token": TOK}, timeout=60)
    if not r.ok:
        print("Story IG (foto) container ERRO:", r.text[:300]); return None
    cid = r.json()["id"]
    for i in range(30):
        time.sleep(3)
        st = requests.get(f"{G}/{cid}", params={"fields": "status_code", "access_token": TOK}, timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            print("Story IG (foto) ERRO:", st); return None
    pub = requests.post(f"{G}/{IG}/media_publish", data={"creation_id": cid, "access_token": TOK}, timeout=120)
    print("Story IG (foto) publish:", pub.status_code, pub.text[:200])
    if not pub.ok:
        return None
    sid = pub.json().get("id")
    print("STORY publicado:", sid)
    return sid


def story_do_carrossel(capa_jpg, saida):
    """imagem 1080x1920 para story a partir da capa do carrossel (1080x1440): capa centrada sobre ela mesma
    borrada, e embaixo a chamada para o post. Tudo dentro da área segura do story (250 px em cima e embaixo)."""
    sys.path.insert(0, str(BASE))
    import reels as R
    from playwright.sync_api import sync_playwright
    uri = R.data_uri(capa_jpg)
    html = R.page(f"""<div class="card">
  <div class="bgfill"><img src="{uri}"></div>
  <img src="{uri}" style="position:absolute;left:84px;top:270px;width:912px;height:1216px;border-radius:26px;
       box-shadow:0 18px 60px rgba(0,0,0,.6);z-index:5">
  <div style="position:absolute;left:0;right:0;top:1530px;text-align:center;z-index:6">
    <div style="font-family:'Anton';font-size:58px;letter-spacing:1px;line-height:1.1">NOVO POST NO PERFIL</div>
    <div style="margin-top:14px;font-size:30px;font-weight:700;color:{R.ACCENT}">@pisca.news · arraste as notícias</div>
  </div>
</div>""")
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": R.W, "height": R.H})
        pg.set_content(html, wait_until="load"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(150)
        pg.screenshot(path=str(saida), type="jpeg", quality=92); br.close()
    return Path(saida)


def story_nativo(conteudo_json, saida):
    """Story 1080x1920 feito direto no formato vertical, SEM BORDA. 24/09: UMA foto em tela cheia — o rosto principal da
    capa (cover.story_photo, senão a 1ª foto), enquadrado pelo rosto. As 3 tiras de 360 px cortavam rosto de retrato ao
    meio. Título, data e chamada só dentro da área segura do story (250 px em cima e embaixo)."""
    import json as _json, html as _h
    sys.path.insert(0, str(BASE))
    import reels as R
    from playwright.sync_api import sync_playwright
    d = _json.loads(Path(conteudo_json).read_text(encoding="utf-8"))
    c = d["cover"]
    foto = c.get("story_photo") or (c.get("photos") or [None])[0]
    tiras = ""
    if foto:
        foto = str(foto if Path(foto).is_absolute() else BASE / foto)
        import foco, boas_praticas as BP
        pos = c.get("story_position") or foco.posicao(foto, R.W, R.H, alvo_y=0.28, padrao="50% 30%")
        a = BP.aviso_foto(foto, R.W, R.H, rotulo="story")
        if a:
            print(a)
        tiras = (f'<div style="position:absolute;inset:0;overflow:hidden"><img src="{R.data_uri(foto)}" '
                 f'style="width:100%;height:100%;object-fit:cover;object-position:{pos}"></div>')
    br = lambda t: _h.escape(t or "").replace("\n", "<br>")
    titulo = f'{br(c.get("headline_before"))} <span style="color:{R.ACCENT}">{br(c.get("headline_accent"))}</span> {br(c.get("headline_after"))}'
    html = R.page(f"""<div class="card">{tiras}
  <div style="position:absolute;inset:0;z-index:4;background:linear-gradient(to bottom,rgba(11,11,16,.62) 0px,
       rgba(11,11,16,.10) 420px,rgba(11,11,16,0) 640px,rgba(11,11,16,.78) 1030px,rgba(11,11,16,.93) 1240px,
       rgba(11,11,16,.93) 1680px,rgba(11,11,16,.70) 1920px)"></div>
  <div style="position:absolute;left:90px;right:90px;top:262px;z-index:8;display:flex;align-items:center;gap:18px">
    <div class="mark">{R.EYE}</div><div class="wordmark">PISCA</div>
    <div style="margin-left:auto;font-size:26px;font-weight:800;letter-spacing:2px;background:rgba(11,11,16,.55);
         padding:10px 20px;border-radius:40px">{_h.escape(d.get("date_label",""))}</div></div>
  <div style="position:absolute;left:90px;right:90px;bottom:262px;z-index:8">
    <div style="font-family:'Anton';font-size:104px;line-height:1.06;text-transform:uppercase">{titulo}</div>
    <div style="margin-top:22px;font-size:34px;font-weight:600;color:#D6D6DE">{_h.escape(c.get("subtitle",""))}</div>
    <div style="margin-top:44px;display:inline-block;background:{R.ACCENT};color:#0B0B10;font-family:'Anton';font-size:44px;
         letter-spacing:1px;padding:14px 30px;border-radius:16px">NOVO POST NO PERFIL</div>
    <div style="margin-top:16px;font-size:30px;font-weight:800;color:{R.ACCENT}">@pisca.news · arraste as notícias</div>
  </div>
</div>""")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": R.W, "height": R.H})
        pg.set_content(html, wait_until="load"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(150)
        fim = pg.evaluate("Math.max(...[...document.querySelectorAll('.card div')].map(e=>e.getBoundingClientRect().bottom).filter(v=>v<1920))")
        pg.screenshot(path=str(saida), type="jpeg", quality=92); b.close()
    if fim > R.H - 250:
        print(f"AVISO story: texto termina em {fim:.0f}px (limite {R.H - 250})")
    return Path(saida)


def stories_do_carrossel(pasta_out):
    """story no Instagram E no Facebook para um carrossel publicado (pasta com slide_01.jpg).
    23/09: se a pasta tem o content.json, o story sai nativo em 9:16 (tela cheia, sem moldura)."""
    cj = Path(pasta_out) / "content.json"
    if cj.exists():
        img = story_nativo(cj, Path(pasta_out) / "story.jpg")
    else:
        img = story_do_carrossel(Path(pasta_out) / "slide_01.jpg", Path(pasta_out) / "story.jpg")
    for nome, f in (("Instagram", instagram_story_foto), ("Facebook", facebook_story_foto)):
        try:
            f(img)
        except Exception as e:
            print(f"Story {nome} falhou:", e)


def main():
    if "--carrossel" in sys.argv:                  # python3 compartilha_reel.py --carrossel out_t23
        stories_do_carrossel(sys.argv[sys.argv.index("--carrossel") + 1]); return
    video, leg = sys.argv[1], Path(sys.argv[2]).read_text(encoding="utf-8").strip()
    so = [a for a in sys.argv if a.startswith("--so-")]
    if not so or "--so-fb" in so:
        facebook_reel(video, leg)
    if not so or "--so-story" in so:
        instagram_story(video)
    if not so or "--so-fb-story" in so:
        facebook_story_video(video)


if __name__ == "__main__":
    main()
