"""Travas de legenda do Pisca (23/09/2026) — aplicadas pelos publicadores antes de criar o post.

Vêm das "Boas práticas" do Instagram que o José Miguel mandou registrar (BOAS_PRATICAS.md):
- isca de engajamento (induzir curtida/comentário/compartilhamento) derruba o alcance;
- até 5 hashtags (limite do Instagram desde dez/2025);
- 2.200 caracteres é o teto do Instagram;
- Reels: legenda CURTA e com emoji — ele cobrou "um reels com esta legenda gigante? sem nenhuma
  figurinha? só o texto cru?" depois de uma legenda de 2.185 caracteres sem emoji.
"""
import re

ISCA = re.compile(
    r"(?i)\b(comente|comenta)\s+[\"“]?(sim|aqui|eu|n[aã]o|emoji|\d)"
    r"|\bmarc(a|ue)\s+(\d+|um|uma|dois|duas|tr[eê]s)\s+(amig|pesso)"
    r"|\b(curta|curte|d[eê]\s+(um\s+)?like)\s+se\b"
    r"|\bcompartilh(a|e)\s+com\s+\d+"
    r"|\bsalv(a|e)\s+e\s+compartilh")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")

LIMITE_IG = 2200
LIMITE_REELS = 1200


def checa_legenda(texto, tipo="carrossel"):
    """Devolve (erros, avisos). Erro trava a publicacao; aviso so imprime."""
    t = (texto or "").strip()
    erros, avisos = [], []
    if len(t) > LIMITE_IG:
        erros.append(f"legenda com {len(t)} caracteres (o Instagram aceita {LIMITE_IG})")
    if tipo == "reels" and len(t) > LIMITE_REELS:
        erros.append(f"legenda de Reels com {len(t)} caracteres — estilo Pisca: no máximo {LIMITE_REELS}, curta e com emoji")
    n_hash = len(re.findall(r"(?<!\w)#\w", t))
    if n_hash > 5:
        erros.append(f"{n_hash} hashtags (máximo 5)")
    m = ISCA.search(t)
    if m:
        erros.append(f"isca de engajamento: “{m.group(0)}” — reduz o alcance; troque por pergunta de opinião ou chamada específica")
    if tipo == "reels" and not EMOJI.search(t):
        avisos.append("legenda de Reels sem nenhum emoji (estilo Pisca pede emoji marcando as linhas)")
    if "?" not in t:
        avisos.append("legenda sem pergunta no fim (boa prática: puxar participação com pergunta de opinião)")
    # 24/09 ("faça direito, tudo"): regras dele que valem para toda legenda
    divulga = re.search(r"(?i)feito com o claude", t)
    if re.search(r"(?i)\banthropic\b", t) and not divulga:
        erros.append("notícia da Anthropic sem a linha \"O Pisca é feito com o Claude, da Anthropic — ...\" (regra dele)")
    elif re.search(r"\bClaude\b", t) and not divulga:
        avisos.append("fala do Claude sem a linha \"O Pisca é feito com o Claude, da Anthropic\" — conferir se é da Anthropic")
    if not re.search(r"(?i)\bfontes?\b", t):
        avisos.append("legenda sem a linha de fontes (duas fontes grandes por notícia)")
    if tipo == "reels" and not re.search(r"(?i)\bfotos?\b|📷", t):   # no carrossel o crédito vai em cada cartão
        avisos.append("legenda sem crédito das fotos (📷 Fotos: autor e licença)")
    if not re.search(r"(?i)\bmand[ae]\b|📲", t):
        avisos.append("legenda sem chamada para MANDAR com destinatário (\"Manda pro seu amigo que...\")")
    return erros, avisos


def aplica(texto, tipo):
    erros, avisos = checa_legenda(texto, tipo)
    for a in avisos:
        print("AVISO legenda:", a)
    if erros:
        for e in erros:
            print("ERRO legenda:", e)
        raise SystemExit("publicação travada pelas regras de legenda (regras_legenda.py)")
