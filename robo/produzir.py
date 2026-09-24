#!/usr/bin/env python3
"""Produz uma edição (carrossel + Reels) com o Claude Code e abre a PRÉVIA para o José Miguel.

Uso: python3 robo/produzir.py [manha|meio|noite]     (sem argumento: escolhe pela hora de Brasília)
Não publica nada: deixa a edição na fila (fila/<id>/agenda.json) e o robô publicador solta no horário.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import (DIAS, EDICOES, ESTADO, FILA, MESES, RAIZ, abrir_issue, agora, alerta, env_sem_chaves,  # noqa: E402
                   gravar, legendas_recentes, ler)

MODELO = os.environ.get("MODELO", "claude-opus-5-5")
RAPIDO = os.environ.get("MODELO_RAPIDO", "claude-sonnet-5")
TEMPO = int(os.environ.get("TEMPO_PRODUCAO_MIN", "95")) * 60


def escolhe_edicao():
    h = agora().hour
    return "manha" if h < 9 else ("meio" if h < 14 else "noite")


def rodar_claude(prompt, log):
    cmd = ["claude", "-p", "--model", MODELO, "--fallback-model", RAPIDO, "--dangerously-skip-permissions",
           "--max-turns", "500", "--output-format", "json"]
    ini = time.time()
    try:
        p = subprocess.run(cmd, input=prompt, text=True, capture_output=True, cwd=RAIZ, env=env_sem_chaves(),
                           timeout=TEMPO)
        saida, codigo = p.stdout, p.returncode
        log.write_text((p.stdout or "")[-20000:] + "\n--- stderr ---\n" + (p.stderr or "")[-5000:], encoding="utf-8")
    except subprocess.TimeoutExpired as e:
        saida, codigo = (e.stdout or b"").decode("utf-8", "ignore") if isinstance(e.stdout, bytes) else (e.stdout or ""), -9
        log.write_text("TEMPO ESGOTADO\n" + saida[-20000:], encoding="utf-8")
    try:
        j = json.loads(saida)
    except Exception:
        j = {}
    return codigo, j, int(time.time() - ini)


def miniatura(origem, destino, largura=1100):
    from PIL import Image
    im = Image.open(origem).convert("RGB")
    if im.width > largura:
        im = im.resize((largura, int(im.height * largura / im.width)))
    im.save(destino, "JPEG", quality=80)


def main():
    ed = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in EDICOES else escolhe_edicao()
    E = EDICOES[ed]
    hoje = agora()
    ident = f"{hoje:%Y-%m-%d}-{ed}"
    pasta = FILA / ident
    ag = ler(pasta / "agenda.json")
    if ag and ag.get("itens"):
        print("edição já produzida:", ident)
        return 0
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") and not os.environ.get("ANTHROPIC_API_KEY"):
        alerta("Falta o código do Claude no GitHub",
               "O robô não consegue produzir sem o secret `CLAUDE_CODE_OAUTH_TOKEN`.\n\nNo seu PC, rode "
               "`claude setup-token`, copie o código e grave em Settings → Secrets and variables → Actions → "
               "New repository secret, com o nome `CLAUDE_CODE_OAUTH_TOKEN`.")
        return 1

    data_br = f"{DIAS[hoje.weekday()]}, {hoje:%d/%m}"
    # a edição já saiu (pedido feito à mão, antes do horário)? então não produz de novo
    recentes = legendas_recentes()
    marca = f"{E['piscada']} ({data_br})"
    if any(marca in (m.get("caption") or "") for m in recentes):
        print("já publicada à mão:", marca)
        return 0
    ESTADO.mkdir(exist_ok=True)
    (ESTADO / "recentes.txt").write_text("\n\n=====\n\n".join(
        f"[{m.get('timestamp','')[:16]}] {m.get('media_product_type','')}\n{(m.get('caption') or '')[:900]}"
        for m in recentes), encoding="utf-8")

    pasta.mkdir(parents=True, exist_ok=True)
    date_label = f"{DIAS[hoje.weekday()].upper()} · {hoje:%d} {MESES[hoje.month - 1]}"
    prompt = (RAIZ / "robo" / "edicao.md").read_text(encoding="utf-8") + f"""

## Variáveis desta execução
EDICAO={ed} ({E['nome']})
DATA_BR={data_br}
DATE_LABEL={date_label}
PASTA=fila/{ident}
Hora agora (Brasília): {hoje:%H:%M}. O Reels sai às {E['reels']} e o carrossel às {E['carrossel']}.
"""
    codigo, j, seg = rodar_claude(prompt, pasta / "agente.log")
    print(f"agente terminou: código {codigo}, {seg // 60} min, custo de referência US$ {j.get('total_cost_usd', 0):.2f}")
    if codigo != 0 and not (pasta / "content.json").exists():
        erro = (j.get("result") or "")[:600] or (pasta / "agente.log").read_text(encoding="utf-8")[-800:]
        limite = any(x in erro.lower() for x in ("usage limit", "rate limit", "limite de uso"))
        alerta("Produção parada: " + ("limite de uso do plano do Claude" if limite else "problema no agente"),
               f"Edição {ident} não foi produzida.\n\n```\n{erro}\n```")
        return 1

    # confere cada parte do jeito que o publicador vai conferir
    itens, problemas = [], {}
    for tipo in ("reels", "carrossel"):
        r = subprocess.run([sys.executable, str(RAIZ / "robo" / "checar_edicao.py"), str(pasta), "--so", tipo],
                           capture_output=True, text=True, cwd=RAIZ)
        if r.returncode == 0:
            itens.append({"tipo": tipo, "quando": f"{hoje:%Y-%m-%d}T{E[tipo]}", "estado": "pendente", "tentativas": 0})
        else:
            problemas[tipo] = [l[10:] for l in r.stdout.splitlines() if l.startswith("PROBLEMA:")] or [r.stdout[-400:]]

    resumo = ler(pasta / "resumo.json", {}) or {}
    # miniaturas para a prévia (vão para o repositório; o resto vai como artefato)
    for origem, nome in ((pasta / "carrossel" / "preview.jpg", "previa_carrossel.jpg"),
                         (pasta / "reels_folha.jpg", "previa_reels.jpg")):
        if origem.exists():
            miniatura(origem, pasta / nome)

    repo, sha = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_SHA", "main")
    img = lambda n: f"https://github.com/{repo}/blob/main/fila/{ident}/{n}?raw=true"  # noqa: E731
    linhas = [f"## {E['nome'].capitalize()} de {hoje:%d/%m}", ""]
    if any(i["tipo"] == "reels" for i in itens):
        leg = (pasta / "legenda.txt").read_text(encoding="utf-8")
        linhas += [f"### 🎬 Reels — sai às **{E['reels']}**", f"**{resumo.get('reels', '')}**", "",
                   f"![Reels]({img('previa_reels.jpg')})", "", "<details><summary>Legenda</summary>", "", leg, "",
                   "</details>", ""]
    if any(i["tipo"] == "carrossel" for i in itens):
        cap = json.loads((pasta / "content.json").read_text(encoding="utf-8")).get("caption", "")
        linhas += [f"### 🗞️ Carrossel — sai às **{E['carrossel']}**", "",
                   f"![Carrossel]({img('previa_carrossel.jpg')})", "", "<details><summary>Legenda</summary>", "",
                   cap, "", "</details>", ""]
    for tipo, erros in problemas.items():
        linhas += [f"### ⚠️ {tipo.capitalize()} NÃO vai sair (não passou nas travas)", ""] + [f"- {e}" for e in erros] + [""]
    if resumo.get("observacoes"):
        linhas += ["### Observação do editor", resumo["observacoes"], ""]
    linhas += ["---", "Para não publicar, comente aqui: `cancelar reels`, `cancelar carrossel` ou `cancelar tudo`.",
               "Sem comentário, sai no horário no Instagram, Facebook (feed e story) e Threads."]
    titulo = f"Prévia: {E['nome']} de {hoje:%d/%m} (" + ", ".join(
        f"{i['tipo']} {E[i['tipo']]}" for i in itens) + ")" if itens else f"Edição {E['nome']} de {hoje:%d/%m} sem post"
    numero = abrir_issue(titulo, "\n".join(linhas), "previa" if itens else "alerta")

    gravar(pasta / "agenda.json", {"id": ident, "edicao": ed, "issue": numero, "run_id": os.environ.get("GITHUB_RUN_ID"),
                                   "artefato": f"edicao-{ident}", "itens": itens, "problemas": problemas,
                                   "minutos_agente": seg // 60, "custo_referencia_usd": j.get("total_cost_usd")})
    # lista do que vai no artefato (a edição inteira + as fotos que ela usa)
    import foto_repete as FR
    fotos = set()
    for arq in ("content.json", "materia.json"):
        if (pasta / arq).exists():
            fotos |= {str(p.relative_to(RAIZ)) for p in FR.fotos(pasta / arq)}
    (RAIZ / "artefato.txt").write_text("\n".join([f"fila/{ident}"] + sorted(fotos)), encoding="utf-8")
    print("prévia aberta:", numero, "| itens:", [i["tipo"] for i in itens], "| problemas:", list(problemas))
    return 0 if itens else 1


if __name__ == "__main__":
    sys.exit(main())
