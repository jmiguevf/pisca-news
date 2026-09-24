#!/usr/bin/env python3
"""Trava de notícia repetida — regra dele: nunca repetir notícia (nem o desfecho de uma que já saiu) sem fato novo
pesado; Reels nunca repete o carrossel.

publicadas.json = lista [["AAAA-MM-DDTHH:MM", "manchete"], ...], a mais nova primeiro. Os publicadores registram
sozinhos depois de publicar (publish.py e publish_reel.py); os motores conferem antes de gerar.

Uso:
  python3 nao_repete.py checa    content.json|materia.json|legenda.txt|out_pasta [--dias 14]
  python3 nao_repete.py registra content.json|materia.json|legenda.txt|out_pasta [--quando AAAA-MM-DDTHH:MM]
No código:
  import nao_repete as NR
  NR.avisa(NR.manchetes(caminho))   # só imprime (motores)
  NR.trava(NR.manchetes(caminho))   # para a publicação se achar parecida (a não ser NOVO_FATO=1 no ambiente)
"""
import json, os, re, sys, time, unicodedata
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
HIST = BASE / "publicadas.json"
DIAS = 14


def _sem_acento(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


_STOP = set(_sem_acento("""a o as os um uma uns umas de do da dos das em no na nos nas num numa por pelo pela pelos pelas
para pra pro pros pras com sem sob sobre entre e ou mas que se ao aos à às é são ser foi foram era vai vão tem têm ter
teve como mais menos muito muita muitos muitas já não sim seu sua seus suas ele ela eles elas isso isto esta este essa
esse até após antes depois quando onde qual quais quem hoje ontem amanhã agora diz dizem disse contra fica ficam
novo nova novos novas ano anos mil milhão milhões bilhão bilhões dia dias vez porque cada todo toda todos todas
aqui lá outro outra via desde durante sobe cai
piscou piscada mudou manhã tarde noite resumo notícia notícias segundos minuto especial
2024 2025 2026 2027""").split())


def tokens(texto):
    out = set()
    for w in re.findall(r"[a-z0-9]+", _sem_acento(texto or "")):
        if w in _STOP:
            continue
        if w.isdigit():
            if len(w) < 3:
                continue
        elif len(w) < 3:
            continue
        if len(w) > 4 and w.endswith("s") and not w.isdigit():
            w = w[:-1]
        out.add(w)
    return out


_NUM_EMOJI = re.compile(r"^\s*(?:[0-9]️?⃣|🔟|[•▪️◾🔹🔸➡️👉]\s)")
_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF☀-➿️⃣]")


def manchetes(caminho):
    """Manchetes de um post: carrossel/resumo (news[].headline), matéria (gancho + promessa), legenda (linhas
    numeradas; se não houver, a 1ª linha) ou pasta out_xxx (content.json, senão caption.txt)."""
    p = Path(caminho)
    if p.is_dir():
        p = p / "content.json" if (p / "content.json").exists() else p / "caption.txt"
    if not p.exists():
        return []
    if p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("news"):
            return [n["headline"] for n in d["news"] if n.get("headline")]
        g = d.get("gancho") or {}
        if g.get("linha"):
            return [" — ".join(x for x in (g["linha"], g.get("promessa", "")) if x)]
        return []
    linhas = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    numeradas = [re.sub(r"^\d+\s*", "", _EMOJI.sub("", l)).strip(" -—:") for l in linhas if _NUM_EMOJI.match(l)]
    if len(numeradas) >= 3:
        return numeradas
    # legenda de Reels: cada notícia/fato numa linha que começa com emoji; fora o rodapé (manda, pergunta, fotos...)
    rodape = ("Manda", "Você", "Voce", "Fotos", "Fontes", "O Pisca é feito", "Arraste", "Siga", "Checou")
    com_emoji = []
    for l in linhas:
        if not _EMOJI.match(l):
            continue
        t = _EMOJI.sub("", l).strip(" -—:")
        if t and not t.startswith(rodape) and not _boilerplate(t):
            com_emoji.append(t)
    if len(com_emoji) >= 2:
        return com_emoji
    return [_EMOJI.sub("", linhas[0]).strip()] if linhas else []


def historico():
    try:
        return json.loads(HIST.read_text(encoding="utf-8"))
    except Exception:
        return []


def _boilerplate(t):
    return t.startswith(("Piscou?", "Piscada", "O resumo desta"))


def parecidas(textos, dias=DIAS, agora=None):
    """[(nova, antiga, quando, em_comum)] — parecida = 3+ palavras de peso em comum e metade ou mais da menor."""
    agora = agora or (datetime.utcnow() - timedelta(hours=3))
    corte = agora - timedelta(days=dias)
    hist = []
    for quando, t in historico():
        try:
            q = datetime.fromisoformat(quando)
        except Exception:
            continue
        if q >= corte and not _boilerplate(t):
            hist.append((quando, t, tokens(t)))
    achou = []
    for nova in textos:
        a = tokens(nova)
        if not a:
            continue
        for quando, t, b in hist:
            comum = a & b
            if len(comum) >= 3 and len(comum) / max(1, min(len(a), len(b))) >= 0.5:
                achou.append((nova, t, quando, sorted(comum)))
    return achou


def avisa(textos, dias=DIAS):
    r = parecidas(textos, dias)
    for nova, antiga, quando, comum in r:
        print(f"AVISO repetição: \"{nova}\" parece \"{antiga}\" ({quando}; em comum: {', '.join(comum)})")
    if not r and textos:
        print(f"nao_repete: {len(textos)} manchete(s) conferida(s), nada parecido nos últimos {dias} dias")
    return r


def trava(textos, dias=DIAS):
    r = avisa(textos, dias)
    if r and os.environ.get("NOVO_FATO") != "1":
        raise SystemExit("publicação travada: notícia parecida com uma que já saiu (regra de não repetir). "
                         "Só com fato novo pesado: rode de novo com NOVO_FATO=1.")
    return r


def registra(textos, quando=None):
    quando = quando or _hora_brt()
    hist = historico()
    ja = {t for _, t in hist}
    novos = [[quando, t] for t in textos if t and t not in ja]
    if novos:
        HIST.write_text(json.dumps(novos + hist, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"nao_repete: {len(novos)} manchete(s) registrada(s) em publicadas.json")
    return len(novos)


def _hora_brt():
    # o contêiner roda em UTC; o histórico é em horário de Brasília
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("checa", "registra"):
        print(__doc__); sys.exit(2)
    alvo = sys.argv[2]
    dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else DIAS
    txt = manchetes(alvo)
    if sys.argv[1] == "checa":
        sys.exit(3 if avisa(txt, dias) else 0)
    quando = sys.argv[sys.argv.index("--quando") + 1] if "--quando" in sys.argv else _hora_brt()
    registra(txt, quando)
