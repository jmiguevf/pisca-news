#!/usr/bin/env python3
"""Publica um carrossel no Instagram pela Graph API (Instagram API with Facebook Login).

Uso:
  python3 publish.py out/                # publica slide_*.jpg de out/ com out/caption.txt
  python3 publish.py out/ --dry-run      # faz tudo (hospeda, cria containers) menos o media_publish
  python3 publish.py out/ --caption "texto"

Variáveis de ambiente obrigatórias: IG_USER_ID, FB_PAGE_ID, META_PAGE_TOKEN
Opcionais: GRAPH_VERSION (padrão v23.0), GITHUB_TOKEN + GITHUB_REPO (hospedagem alternativa, ex. "usuario/repo")

Hospedagem das imagens: a API do Instagram exige URL pública (JPEG). Estratégia:
  1) foto não publicada na Página do Facebook (mesmo token) -> URL do CDN da Meta
  2) fallback: commit no GitHub (raw.githubusercontent.com)
As fotos temporárias da Página são apagadas ao final.
"""
import os, sys, json, time, base64, argparse
from pathlib import Path
import requests

GRAPH = "https://graph.facebook.com/" + os.environ.get("GRAPH_VERSION", "v23.0")
IG_USER_ID = os.environ.get("IG_USER_ID")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
TOKEN = os.environ.get("META_PAGE_TOKEN")
GH_TOKEN = os.environ.get("GITHUB_TOKEN")
GH_REPO = os.environ.get("GITHUB_REPO")


def die(msg):
    print("ERRO:", msg, file=sys.stderr)
    sys.exit(1)


def api(method, path, **kw):
    kw.setdefault("timeout", 120)
    r = requests.request(method, f"{GRAPH}/{path}", **kw)
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text}
    if r.status_code >= 400 or "error" in j:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {json.dumps(j, ensure_ascii=False)[:600]}")
    return j


# ---------- hospedagem ----------
def host_on_facebook(path):
    with open(path, "rb") as f:
        j = api("POST", f"{FB_PAGE_ID}/photos",
                files={"source": (Path(path).name, f, "image/jpeg")},
                data={"published": "false", "access_token": TOKEN})
    photo_id = j["id"]
    info = api("GET", photo_id, params={"fields": "images", "access_token": TOKEN})
    images = sorted(info["images"], key=lambda x: x.get("width", 0), reverse=True)
    return images[0]["source"], photo_id


def host_on_github(path, run_id):
    if not (GH_TOKEN and GH_REPO):
        raise RuntimeError("GITHUB_TOKEN/GITHUB_REPO não configurados")
    name = f"posts/{run_id}/{Path(path).name}"
    content = base64.b64encode(Path(path).read_bytes()).decode()
    r = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{name}",
                     headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"},
                     json={"message": f"post {run_id}", "content": content}, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f"GitHub {r.status_code}: {r.text[:300]}")
    branch = r.json()["content"]["url"].split("ref=")[-1] if "ref=" in r.json()["content"]["url"] else "main"
    return f"https://raw.githubusercontent.com/{GH_REPO}/{branch}/{name}", None


def host(path, run_id):
    try:
        return host_on_facebook(path)
    except Exception as e:
        print(f"  hospedagem na Página falhou ({e}); tentando GitHub...")
        return host_on_github(path, run_id)


# ---------- Facebook (regra dele, 23/09: "precisa publicar tudo no face junto, tanto os reels quanto carrosel") ----------
def post_facebook(photo_ids, caption):
    """Post de várias fotos na Página, na mesma ordem do carrossel, reaproveitando as fotos não publicadas
    que já subiram para hospedar o Instagram. Devolve o link do post."""
    data = {"message": caption, "access_token": TOKEN}
    for i, pid in enumerate(photo_ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    j = api("POST", f"{FB_PAGE_ID}/feed", data=data)
    link = f"https://www.facebook.com/{j['id']}"
    try:
        link = api("GET", j["id"], params={"fields": "permalink_url", "access_token": TOKEN}).get("permalink_url") or link
    except Exception:
        pass
    print("FACEBOOK:", link)
    return link


# ---------- containers ----------
def wait_ready(container_id, label, tries=40):
    for _ in range(tries):
        j = api("GET", container_id, params={"fields": "status_code,status", "access_token": TOKEN})
        code = j.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {label} falhou: {j}")
        time.sleep(3)
    raise RuntimeError(f"container {label} não ficou pronto a tempo")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--caption")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--so-facebook", action="store_true", help="só publica no Facebook (carrossel que já saiu no Instagram)")
    a = ap.parse_args()

    for k, v in (("IG_USER_ID", IG_USER_ID), ("FB_PAGE_ID", FB_PAGE_ID), ("META_PAGE_TOKEN", TOKEN)):
        if not v:
            die(f"variável {k} não definida")

    folder = Path(a.folder)
    slides = sorted(folder.glob("slide_*.jpg"))
    if not 2 <= len(slides) <= 10:
        die(f"carrossel precisa de 2 a 10 imagens; encontrei {len(slides)}")
    caption = a.caption if a.caption is not None else (folder / "caption.txt").read_text(encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).parent))
    import regras_legenda
    regras_legenda.aplica(caption, "carrossel")
    # 24/09: regra de não repetir notícia (só passa com NOVO_FATO=1) — manchetes do content.json da pasta
    import nao_repete as NR
    manchetes = NR.manchetes(folder)
    if not a.so_facebook:
        NR.trava(manchetes)
        import foto_repete as FR      # 24/09: foto que já saiu trava
        if (folder / "content.json").exists():
            FR.trava(folder / "content.json")
    if len(caption) > 2200:
        die("legenda acima de 2200 caracteres")

    run_id = time.strftime("%Y%m%d-%H%M%S")
    temp_photos = []
    try:
        # sanidade do token/conta
        me = api("GET", IG_USER_ID, params={"fields": "id,username", "access_token": TOKEN})
        print(f"Conta: @{me.get('username')} ({me['id']})")

        if a.so_facebook:
            ids = [host_on_facebook(s_)[1] for s_ in slides]
            temp_photos.extend(ids)
            post_facebook(ids, caption)
            temp_photos.clear()          # viraram parte do post: não apagar
            return

        children = []
        for s in slides:
            url, photo_id = host(s, run_id)
            if photo_id:
                temp_photos.append(photo_id)
            j = api("POST", f"{IG_USER_ID}/media",
                    data={"image_url": url, "is_carousel_item": "true", "access_token": TOKEN})
            children.append(j["id"])
            print(f"  {s.name}: container {j['id']}")
        for cid in children:
            wait_ready(cid, cid)

        j = api("POST", f"{IG_USER_ID}/media",
                data={"media_type": "CAROUSEL", "children": ",".join(children),
                      "caption": caption, "access_token": TOKEN})
        carousel = j["id"]
        wait_ready(carousel, "carrossel")
        print(f"Carrossel pronto: {carousel}")

        if a.dry_run:
            print("DRY-RUN: tudo validado, publicação não executada.")
            return

        j = api("POST", f"{IG_USER_ID}/media_publish", data={"creation_id": carousel, "access_token": TOKEN})
        media_id = j["id"]
        info = api("GET", media_id, params={"fields": "permalink", "access_token": TOKEN})
        print("PUBLICADO:", info.get("permalink"))
        (folder / "published.json").write_text(json.dumps({"media_id": media_id, "permalink": info.get("permalink"),
                                                            "run_id": run_id}, ensure_ascii=False, indent=2))
        try:
            NR.registra(manchetes, NR._hora_brt())
        except Exception as e:
            print("histórico de não repetir falhou:", e)
        try:
            import foto_repete as FR
            if (folder / "content.json").exists():
                FR.registra(folder / "content.json", folder.name)
        except Exception as e:
            print("histórico de fotos falhou:", e)
        if os.environ.get("COMPARTILHAR", "1") != "0":
            if len(temp_photos) == len(slides):
                try:
                    post_facebook(list(temp_photos), caption)
                    temp_photos.clear()      # viraram parte do post no Facebook: não apagar
                except Exception as e:
                    print("Facebook falhou:", e)
            else:
                print("Facebook: nem todas as fotos subiram pela Página; rode de novo com --so-facebook")
            try:                           # 23/09: todo post vira story no Instagram e no Facebook
                import compartilha_reel as C
                C.stories_do_carrossel(folder)
            except Exception as e:
                print("Stories do carrossel falharam:", e)
    finally:
        for pid in temp_photos:
            try:
                api("DELETE", pid, params={"access_token": TOKEN})
            except Exception as e:
                print(f"  (não apagou foto temporária {pid}: {e})")


if __name__ == "__main__":
    main()
