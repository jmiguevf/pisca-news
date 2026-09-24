#!/usr/bin/env python3
"""Desempenho do Pisca: puxa as métricas de TODOS os posts pela API e grava um retrato em desempenho.csv
(uma linha por post por dia de coleta), para comparar formatos, horários, temas e compartilhamentos.

Uso: python3 desempenho.py            # coleta, grava e mostra o ranking
     python3 desempenho.py --so-ver   # só mostra o ranking da última coleta
Precisa de IG_USER_ID e META_PAGE_TOKEN (.pisca_env). Ver APRENDIZADOS.md.
"""
import os, sys, csv, datetime, requests
from pathlib import Path

BASE = Path(__file__).parent
CSV = BASE / "desempenho.csv"
G = "https://graph.facebook.com/v23.0"
CAMPOS = ["coleta", "publicado", "tipo", "link", "titulo", "views", "reach", "likes", "comments", "shares", "saved",
          "watch_s", "horas_no_ar"]


def coleta():
    tok, ig = os.environ["META_PAGE_TOKEN"], os.environ["IG_USER_ID"]
    posts, url = [], f"{G}/{ig}/media"
    params = {"fields": "id,media_product_type,timestamp,permalink,caption", "limit": 50, "access_token": tok}
    while url:
        r = requests.get(url, params=params, timeout=60).json(); params = None
        posts += r.get("data", []); url = r.get("paging", {}).get("next")
    agora = datetime.datetime.utcnow()
    linhas = []
    for m in posts:
        reels = m.get("media_product_type") == "REELS"
        met = "views,reach,shares,saved,likes,comments" + (",ig_reels_avg_watch_time" if reels else "")
        ins = requests.get(f"{G}/{m['id']}/insights", params={"metric": met, "access_token": tok}, timeout=60).json()
        v = {d["name"]: d["values"][0]["value"] for d in ins.get("data", [])}
        t = datetime.datetime.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
        linhas.append(dict(coleta=(agora - datetime.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
                           publicado=(t - datetime.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
                           tipo=m.get("media_product_type"), link=m["permalink"],
                           titulo=(m.get("caption") or "").split("\n")[0][:90],
                           views=v.get("views", 0), reach=v.get("reach", 0), likes=v.get("likes", 0),
                           comments=v.get("comments", 0), shares=v.get("shares", 0), saved=v.get("saved", 0),
                           watch_s=round(v.get("ig_reels_avg_watch_time", 0) / 1000, 1),
                           horas_no_ar=round((agora - t).total_seconds() / 3600)))
    novo = not CSV.exists()
    with CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerows(linhas)
    return linhas


def ultima():
    with CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ult = max(r["coleta"] for r in rows)
    return [r for r in rows if r["coleta"] == ult]


def mostra(linhas):
    for chave, nome in (("reach", "CONTAS ALCANÇADAS"), ("shares", "COMPARTILHAMENTOS")):
        print(f"\n== {nome} ==")
        for r in sorted(linhas, key=lambda r: -int(r[chave]))[:8]:
            print(f"{r['publicado'][5:]}  {r['tipo'][:6]:6} views {int(r['views']):4} contas {int(r['reach']):4} "
                  f"compart {int(r['shares']):2}  assist {float(r['watch_s']):4.1f}s  {r['titulo'][:60]}")


if __name__ == "__main__":
    mostra(ultima() if "--so-ver" in sys.argv else coleta())
