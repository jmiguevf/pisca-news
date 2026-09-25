# PISCA — regras que valem (24/09/2026)

Pedido dele (24/09): "Cancele e apague regras antigas e registre apenas o que é bom e dá retorno." Tudo o que não está
aqui foi cancelado. Ler antes de produzir qualquer coisa. 🔒 = a máquina confere sozinha e trava.

## 0. O dia (regra fixa, 25/09 — ele: "registre isso")
- 6 posts por dia, em 3 edições. Cada edição tem 1 Reels e 1 carrossel:
  manhã (Reels 7h, carrossel 8h) · meio-dia (Reels 12h, carrossel 13h) · noite (Reels 18h30, carrossel 19h30).
- Nada sai sem a aprovação dele (a prévia vai por e-mail). Cada post, quando sai, vai para todas as redes ao mesmo tempo:
  - Reels: Instagram (reel + story), Facebook (reel + story), Threads e YouTube Shorts.
  - Carrossel: Instagram (post + story), Facebook (post + story) e Threads.
- Threads não tem story. YouTube recebe só os 3 Reels do dia.

## 1. O que dá retorno (números da página em 24/09 — detalhes em APRENDIZADOS.md)
- O REELS é o formato que explode: "Trump na ONU: checamos 4 frases" (163 contas, 205 visualizações) e o resumo de
  15/09 às 7h (114 contas, 157). O carrossel nunca passou de 16 contas no Instagram.
- ROSTO CONHECIDO + FATO FORTE: o Trump é o recorde da página.
- FACEBOOK: o Reels do Trump teve 255 visualizações e o resumo da tarde de 23/09, 252 (no Instagram, 45).
- HORÁRIO: os resumos que foram bem saíram entre 7h e 15h; os das 21h ficaram entre 7 e 16 contas.
- COMPARTILHAMENTO vem do carrossel: 10 dos 12 da página, 7 no do Buffett (nome famoso + dinheiro + fato que surpreende
  + "manda pro seu amigo que investe"). Mandar por DM é o que mais leva o post a quem não segue.
- MATÉRIA ÚNICA segura mais: 7 a 15 s assistidos em média, contra 4 a 6 s do resumo.

## 2. Regras fixas dele
- Sob pedido ("eu peço e vc faz"). Por dia: 3 carrosséis (capa + 9) e 3 Reels. Reels nunca repete o carrossel.
- Fora: esporte e campanha eleitoral brasileira. Político (Lula, Flávio, Bolsonaro...) só como centro de notícia com fato,
  mesmo tratamento para todos, só foto real com crédito; NUNCA turbinar post com candidato (Lei 9.504, art. 57-C).
- Notícia da Anthropic sempre que houver, com a linha "O Pisca é feito com o Claude, da Anthropic — ...".
- 🔒 Nunca repetir notícia (nem desfecho) sem fato novo pesado.
- Duas fontes grandes por notícia; número copiado da fonte.
- Versão nova de post que já saiu: perguntar antes. Ele apaga os posts; eu não apago.
- Só a API oficial da Meta. Instagram nunca pelo navegador. Não digito senha nem faço login. Não escrevo token nem senha.
  E-mail pessoal nunca em público.

## 3. Pauta
- O QUE ATRAI (24/09, ele): "as pessoas gostam de coisas dramáticas, medo, guerra, mistério, ciência, tecnologia e
  principalmente riscos da IA". Prioridade da pauta e do Reels nessa ordem de interesse, com RISCOS DA IA em primeiro.
  Sempre com fato real e duas fontes: drama no tema e no gancho, nunca no número (nada de exagerar ou inventar).
- Abrir com rosto conhecido e fato forte: Trump quando houver fato novo dele, guerra/geopolítica, empresas de IA,
  dinheiro, saúde com descoberta, golpe e direito que protegem alguém. Formato "É verdade?" (checagem) funciona.
- Um "cartão para mandar" por post, com destinatário ("pro seu amigo que investe", "pra quem tem pai que escuta mal").
- Horário: Reels 7h e meio-dia; carrossel da noite 19h–20h30. Julgar Reels depois de 48–72 h.

## 4. Visual — SEM BORDA em tudo (Reels, carrossel e story)
- 🔒 A foto sempre preenche o quadro: Reels em tela cheia 1080x1920; carrossel com a foto de ponta a ponta na caixa de
  cima; story com um rosto em tela cheia. Nunca foto inteira numa faixa com fundo desfocado.
- 🔒 Recorte pelo rosto (foco.py): o rosto sai inteiro sem eu marcar posição. Mesmo assim, olhar a folha de contato:
  nada de pedaço sem sentido (ex.: céu), nada brigando com a marca PISCA.
- 🔒 Foto real do Commons com autor e licença, baixada em 1920 px; esticada mais de 2x trava (sai borrada).
- 🔒 NUNCA repetir foto (24/09, cobrança dele): nenhuma foto de capa, cartão, Reels ou story repete o que saiu nos últimos
  30 dias — comparação pela IMAGEM (foto_repete.py), não pelo nome. Rosto conhecido: buscar OUTRA foto da pessoa no Commons
  (há dezenas de cada um); nada de reaproveitar trump_hd, altman etc. Conferir a folha de contato: a foto baixada tem que
  mostrar a pessoa certa.
- Cartão de número: o assunto da foto no terço de cima (o número cobre o meio).
- Texto só na área segura (Reels: 250 px do topo até 1520; story: 250 px em cima e embaixo). 🔒 Cartão final centralizado.
- Reels: resumo com 5+ notícias a 3,4 s cada, ou matéria com 5,5–8 s por cartão; 30–70 s; 🔒 trilha IMPACTO, 1080x1920,
  30 qps, menos de 3 min.
- Carrossel: 1080x1440, capa com 3 rostos conhecidos e pergunta, 9 notícias.
- Rosto do Trump em alta já pronto: photos/trump_hd.jpg (retrato oficial 2025, domínio público).

## 5. Legenda (🔒 regras_legenda.py)
- Curta, com emoji marcando as linhas (Reels até 1.200 caracteres); chamada para MANDAR com destinatário; pergunta de
  opinião; fontes numa linha; créditos das fotos (Reels); até 5 hashtags; nada de isca ("comenta SIM", "marca 3").

## 6. Publicar
- Antes: `set -a && . /home/claude/.pisca_env && set +a`.
- Reels: `python3 publish_reel.py video.mp4 legenda.txt` → Instagram + collab @jmiguel.vf + Facebook + story nos dois.
- Carrossel: `python3 publish.py out_xxx` → Instagram + Facebook + story nos dois.
- Todas as redes: `python3 publica_tudo.py carrossel out_xxx` ou `python3 publica_tudo.py reels video.mp4 legenda.txt` (Threads, YouTube e TikTok entram quando tiverem acesso).
- Depois: conferir cada perna pela API, anotar no ESTADO.md e mandar os links para ele.

## 7. Todo dia
- `python3 comentarios.py` → mando a lista para ele responder pelo app (a API não deixa eu responder).
- `python3 desempenho.py` → atualizar APRENDIZADOS.md só com o que dá retorno.

## 🔒 Travas automáticas
| Onde | Confere | Exceção |
|---|---|---|
| reels.py, reels_materia.py | repetição (aviso), foto esticada, recorte pelo rosto, ficha do vídeo | — |
| publish_reel.py (boas_praticas.py) | 1080x1920, 30 qps, som, < 3 min, sem borda, fecho centralizado, foto > 2x, repetição | FOTO_PEQUENA_OK=1 / NOVO_FATO=1 |
| render.py | repetição, foto pequena, recorte pelo rosto, foto sempre preenchendo a caixa, FOTO REPETIDA (trava) | FOTO_REPETIDA_OK=1 só com ordem dele |
| publish.py / publish_reel.py | repetição e FOTO REPETIDA (travas); registram manchetes (publicadas.json) e fotos (fotos_usadas.json) | NOVO_FATO=1 |
| reels.py, reels_materia.py | FOTO REPETIDA (trava) | — |
| regras_legenda.py | tamanho, hashtags, isca, linha da Anthropic; avisa falta de pergunta, fontes, créditos, chamada | — |
