"""Publica um container que JA foi criado. Serve para retomar quando o
media_publish levou 403 code 4 / subcode 2207051 (bloqueio de janela curta
da Meta): os containers continuam validos por ~24h, entao nao precisa
remontar nada, so tentar de novo o passo final."""
import json, os, sys, time, urllib.parse, urllib.request

API = "https://graph.facebook.com/v23.0"
IG  = os.environ["IG_USER_ID"]
TOK = os.environ["META_PAGE_TOKEN"]

def post(path, params):
    params = dict(params); params["access_token"] = TOK
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        try: return None, json.loads(e.read().decode())
        except Exception: return None, {"erro": str(e)}

def get(path, params):
    params = dict(params); params["access_token"] = TOK
    with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(params)}", timeout=60) as r:
        return json.load(r)

cid = sys.argv[1]
ok, err = post(f"{IG}/media_publish", {"creation_id": cid})
if err:
    e = (err.get("error") or {})
    print("AINDA BLOQUEADO" if e.get("error_subcode") == 2207051 else "FALHOU",
          "|", e.get("code"), e.get("error_subcode"), "|", e.get("message"))
    sys.exit(2)

mid = ok["id"]
time.sleep(3)
info = get(mid, {"fields": "permalink,media_product_type,timestamp"})
print("PUBLICADO:", info.get("permalink"), "|", info.get("media_product_type"), "|", info.get("timestamp"))
