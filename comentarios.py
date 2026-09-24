#!/usr/bin/env python3
"""Lista os comentários NOVOS no Instagram e no Facebook do Pisca, para o José Miguel responder pelo app.

Por quê: responder comentário é boa prática de crescimento ("responder em até poucos dias"; comentário vira pauta),
mas o token da API não tem instagram_manage_comments — então eu leio e mostro, e ele responde.
Uso: python3 comentarios.py [--todos] [--dias 7]
Guarda o que já mostrou em comentarios_vistos.json (com --todos mostra de novo).
"""
import json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
G = "https://graph.facebook.com/v23.0"
IG, PAGE, TOK = os.environ["IG_USER_ID"], os.environ["FB_PAGE_ID"], os.environ["META_PAGE_TOKEN"]
VISTOS = BASE / "comentarios_vistos.json"
TODOS = "--todos" in sys.argv
DIAS = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 7
CORTE = datetime.now(timezone.utc) - timedelta(days=DIAS)


def get(path, **params):
    params["access_token"] = TOK
    r = requests.get(f"{G}/{path}", params=params, timeout=60)
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"].get("message", str(j))[:200])
    return j


def quando(ts):
    return datetime.strptime(ts.replace("Z", "+0000")[:24], "%Y-%m-%dT%H:%M:%S%z")


def brt(ts):
    return (quando(ts) - timedelta(hours=3)).strftime("%d/%m %H:%M")


def instagram():
    achados = []
    midias = get(f"{IG}/media", fields="id,caption,permalink,timestamp,comments_count", limit=50).get("data", [])
    for m in midias:
        if quando(m["timestamp"]) < CORTE or not m.get("comments_count"):
            continue
        cs = get(f"{m['id']}/comments", fields="id,text,username,timestamp,replies{id,text,username,timestamp}",
                 limit=50).get("data", [])
        for c in cs:
            if c.get("username") == "pisca.news":
                continue
            respondido = any(r.get("username") == "pisca.news" for r in (c.get("replies") or {}).get("data", []))
            achados.append({"rede": "Instagram", "id": c["id"], "quando": c["timestamp"], "quem": "@" + c.get("username", "?"),
                            "texto": c.get("text", ""), "post": (m.get("caption") or "").split("\n")[0][:70],
                            "link": m.get("permalink"), "respondido": respondido})
    return achados


def facebook():
    achados = []
    coment = "comments.limit(50){id,message,from,created_time,comments{from}}"
    # posts: "description" é campo aposentado (erro #12); nos Reels do Facebook o texto vem em "description"
    for aresta, texto in (("posts", "message"), ("video_reels", "description")):
        try:
            itens = get(f"{PAGE}/{aresta}", fields=f"id,{texto},permalink_url,created_time,{coment}", limit=30).get("data", [])
        except RuntimeError as e:
            print(f"(Facebook {aresta}: {e})")
            continue
        for p in itens:
            if quando(p["created_time"]) < CORTE:
                continue
            for c in (p.get("comments") or {}).get("data", []):
                de = c.get("from") or {}
                if de.get("id") == PAGE:
                    continue
                respondido = any((r.get("from") or {}).get("id") == PAGE for r in (c.get("comments") or {}).get("data", []))
                achados.append({"rede": "Facebook", "id": c["id"], "quando": c["created_time"],
                                "quem": de.get("name", "alguém"), "texto": c.get("message", ""),
                                "post": (p.get("message") or p.get("description") or "").split("\n")[0][:70],
                                "link": p.get("permalink_url") or f"https://www.facebook.com/{c['id']}",
                                "respondido": respondido})
    return achados


def main():
    try:
        vistos = set(json.loads(VISTOS.read_text()))
    except Exception:
        vistos = set()
    todos = []
    for nome, f in (("Instagram", instagram), ("Facebook", facebook)):
        try:
            todos += f()
        except Exception as e:
            print(f"{nome}: não consegui ler os comentários ({e})")
    todos.sort(key=lambda c: c["quando"], reverse=True)
    mostrar = [c for c in todos if TODOS or c["id"] not in vistos]
    sem_resposta = [c for c in todos if not c["respondido"]]
    print(f"Comentários nos últimos {DIAS} dias: {len(todos)} ({len(sem_resposta)} sem resposta da página); "
          f"novos desde a última lista: {len([c for c in todos if c['id'] not in vistos])}")
    for c in mostrar:
        marca = "" if c["respondido"] else "  ← responder"
        print(f"- {c['rede']} {brt(c['quando'])} {c['quem']}: “{c['texto'][:220]}”{marca}\n"
              f"    no post: {c['post']}\n    {c['link']}")
    VISTOS.write_text(json.dumps(sorted(vistos | {c['id'] for c in todos})))


if __name__ == "__main__":
    main()
