"""
Gera a vitrine estática (index.html) com as ofertas aprovadas mais recentes
e publica no GitHub Pages via git push automático.

Lê o promod.db em modo somente-leitura (não interfere no bot rodando).
"""

import html
import os
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# --- Configuração ---
DB_PATH = os.path.expanduser("~/projetos/alertapromod/promod.db")
REPO_DIR = Path(__file__).resolve().parent  # pasta onde este script está
QTD_OFERTAS = 12

LINK_TELEGRAM = "https://t.me/alertapromod"
LINK_INSTAGRAM = "https://www.instagram.com/alertapromod/"
LINK_WHATSAPP = "https://www.whatsapp.com/channel/0029Vb8pNYnA89MrDPvqhs0R"

# Trecho genérico que a Shopee usa em quase toda oferta — repetir ele
# igual em vários cards seguidos passa impressão de spam, então vira
# um selinho curto em vez do parágrafo inteiro.
BOILERPLATE_PIX = "no pix pode ficar mais"


def limpar_tags_telegram(texto):
    """Remove tags HTML (ex: <b>, </b>) usadas na formatação do Telegram,
    que não fazem sentido exibidas como texto cru numa página web."""
    return re.sub(r"<[^>]+>", "", texto)


def buscar_ofertas():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT titulo, link_afiliado, preco, preco_original, desconto,
               loja, foto, cupom, frete_gratis, avaliacao, num_avaliacoes
        FROM ofertas
        WHERE status = 'aprovada'
        ORDER BY criado_em DESC
        LIMIT ?
        """,
        (QTD_OFERTAS,),
    )
    ofertas = [dict(row) for row in cur.fetchall()]
    conn.close()
    return ofertas


def fmt_preco(valor):
    if not valor:
        valor = 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_badges(oferta):
    badges = []
    if oferta.get("frete_gratis"):
        badges.append("📦 Frete grátis")

    cupom_raw = limpar_tags_telegram(oferta.get("cupom") or "").strip()
    if cupom_raw:
        if BOILERPLATE_PIX in cupom_raw.lower():
            badges.append("💳 Pix pode sair mais barato")
        else:
            badges.append(cupom_raw)

    return badges


def montar_avaliacao_html(oferta):
    avaliacao = (oferta.get("avaliacao") or "").strip()
    if not avaliacao:
        return ""
    num = (oferta.get("num_avaliacoes") or "").strip()
    texto = f"★ {avaliacao}" + (f" ({num})" if num else "")
    return f'<span class="avaliacao">{html.escape(texto)}</span>'


def montar_card(oferta):
    titulo = html.escape(oferta["titulo"] or "")
    loja = html.escape(oferta["loja"] or "")
    link = html.escape(oferta["link_afiliado"] or "#")
    foto = oferta["foto"] or ""
    preco = oferta["preco"] or 0
    preco_original = oferta["preco_original"] or 0
    desconto = oferta["desconto"] or 0

    tag_html = ""
    if desconto and desconto > 0:
        tag_html = f'<span class="tag">-{int(desconto)}%</span>'

    original_html = ""
    if preco_original and preco_original > preco:
        original_html = f'<span class="preco-original">{fmt_preco(preco_original)}</span>'

    if foto:
        img_html = f'<img src="{html.escape(foto)}" alt="{titulo}" loading="lazy">'
    else:
        img_html = '<div class="foto-vazia" aria-hidden="true"></div>'

    badges_html = "".join(
        f'<span class="badge">{html.escape(b)}</span>' for b in montar_badges(oferta)
    )
    avaliacao_html = montar_avaliacao_html(oferta)

    return f"""
    <a class="oferta" href="{link}" target="_blank" rel="nofollow sponsored noopener">
      <div class="foto-wrap">
        {img_html}
        {tag_html}
        <div class="preco-overlay">
          <span class="preco">{fmt_preco(preco)}</span>
          {original_html}
        </div>
      </div>
      <div class="info">
        <p class="loja">{loja} {avaliacao_html}</p>
        <p class="titulo">{titulo}</p>
        {f'<div class="badges">{badges_html}</div>' if badges_html else ''}
      </div>
    </a>"""


def montar_html(ofertas):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    cards = "\n".join(montar_card(o) for o in ofertas)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alerta PromoD — ofertas aprovadas agora</title>
<meta name="description" content="Feed de ofertas aprovadas pelo Alerta PromoD na Amazon, Mercado Livre e Shopee, atualizado automaticamente.">
<link rel="icon" type="image/png" href="logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #201f1d;
  --linha: #3a3532;
  --superficie: #2a2825;
  --texto: #f5f0e8;
  --texto-fraco: #a89f93;
  --vermelho: #e2131b;
  --amarelo: #fac304;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  background: var(--bg);
  color: var(--texto);
  font-family: 'IBM Plex Sans', sans-serif;
  -webkit-font-smoothing: antialiased;
}}
.topo {{
  max-width: 720px;
  margin: 0 auto;
  padding: 2.25rem 1.25rem 1.25rem;
  text-align: center;
}}
.logo {{
  width: 168px;
  height: auto;
  display: block;
  margin: 0 auto 1rem;
}}
.tagline {{
  font-family: 'Anton', sans-serif;
  font-weight: 400;
  font-size: 1.5rem;
  letter-spacing: 0.01em;
  color: var(--vermelho);
  margin: 0 0 0.6rem;
}}
.prova-social {{
  font-size: 0.85rem;
  color: var(--texto-fraco);
  margin: 0 0 1.1rem;
}}
.canais {{
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 1.4rem;
  margin: 0 0 1.25rem;
}}
.canais a {{
  color: var(--texto);
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  border-bottom: 1px solid transparent;
}}
.canais a:hover, .canais a:focus-visible {{
  border-bottom-color: var(--amarelo);
}}
.canais a:focus-visible {{
  outline: 2px solid var(--amarelo);
  outline-offset: 3px;
}}
.status {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--texto-fraco);
  font-size: 0.8rem;
  margin: 0;
}}
.ponto {{
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--vermelho);
  animation: pulsar 2.4s ease-in-out infinite;
}}
@media (prefers-reduced-motion: reduce) {{ .ponto {{ animation: none; }} }}
@keyframes pulsar {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}

.quem-somos {{
  max-width: 720px;
  margin: 0 auto 1.5rem;
  padding: 0 1.25rem;
}}
.quem-somos p {{
  background: var(--superficie);
  border-left: 3px solid var(--amarelo);
  padding: 0.9rem 1rem;
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.55;
  color: var(--texto-fraco);
}}

.feed {{
  max-width: 720px;
  margin: 0 auto;
  padding: 0 1.25rem 2.5rem;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.9rem;
}}
.oferta {{
  display: flex;
  flex-direction: column;
  background: var(--superficie);
  border: 1px solid var(--linha);
  border-radius: 10px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
}}
.oferta:focus-visible {{
  outline: 2px solid var(--vermelho);
  outline-offset: 2px;
}}
.foto-wrap {{
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
}}
.foto-wrap img, .foto-vazia {{
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
  background: #38342f;
  color: transparent;
}}
.tag {{
  position: absolute;
  left: 0; top: 10px;
  background: var(--vermelho);
  color: #fff;
  font-weight: 600;
  font-size: 0.72rem;
  padding: 3px 10px 3px 8px;
  clip-path: polygon(0 0, 100% 0, 88% 100%, 0 100%);
}}
.preco-overlay {{
  position: absolute;
  left: 0; right: 0; bottom: 0;
  padding: 1.6rem 0.6rem 0.5rem;
  background: linear-gradient(to top, rgba(0,0,0,0.82), rgba(0,0,0,0.35) 65%, transparent);
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  flex-wrap: wrap;
}}
.preco {{
  font-family: 'Anton', sans-serif;
  font-weight: 400;
  font-size: 1.25rem;
  color: #fff;
  line-height: 1;
}}
.preco-original {{
  font-size: 0.72rem;
  color: #cfc9c0;
  text-decoration: line-through;
}}
.info {{ padding: 0.65rem 0.7rem 0.8rem; min-width: 0; }}
.loja {{
  margin: 0 0 0.25rem;
  font-size: 0.68rem;
  color: var(--texto-fraco);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}}
.avaliacao {{
  color: var(--amarelo);
}}
.titulo {{
  margin: 0 0 0.5rem;
  font-size: 0.82rem;
  line-height: 1.32;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.badges {{
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}}
.badge {{
  font-size: 0.68rem;
  color: var(--amarelo);
  line-height: 1.25;
}}
.rodape {{
  max-width: 720px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
  color: var(--texto-fraco);
  font-size: 0.75rem;
  border-top: 1px solid var(--linha);
}}
.rodape p {{ margin: 0 0 0.4rem; }}
.rodape p:last-child {{ margin-bottom: 0; }}
@media (min-width: 620px) {{
  .feed {{ grid-template-columns: repeat(3, 1fr); }}
  .tagline {{ font-size: 1.75rem; }}
}}
</style>
</head>
<body>
<header class="topo">
  <img class="logo" src="logo.png" alt="Alerta PromoD">
  <p class="tagline">As ofertas que valem a pena, garimpadas pra você.</p>
  <p class="prova-social">Centenas de pessoas já recebem essas ofertas</p>
  <div class="canais">
    <a href="{LINK_TELEGRAM}" target="_blank" rel="noopener">Telegram</a>
    <a href="{LINK_INSTAGRAM}" target="_blank" rel="noopener">Instagram</a>
    <a href="{LINK_WHATSAPP}" target="_blank" rel="noopener">Canal do WhatsApp</a>
  </div>
  <p class="status"><span class="ponto" aria-hidden="true"></span>atualiza automaticamente a cada 15 minutos</p>
</header>

<section class="quem-somos">
  <p>Este feed é gerado por um robô que garimpa milhares de ofertas por dia na Amazon, no Mercado Livre e na Shopee. Cada oferta passa por um filtro de preço, desconto e avaliação, e é comparada com o histórico de preço antes de aparecer aqui — quando algo foge do padrão, uma pessoa confere manualmente antes de publicar.</p>
</section>

<main class="feed">
{cards}
</main>

<footer class="rodape">
  <p>Contém links de afiliado — ajuda a manter o projeto no ar sem custo pra você.</p>
  <p>Gerado automaticamente pelo Alerta PromoD · última atualização em {agora}</p>
</footer>
</body>
</html>
"""


def publicar_no_git():
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
    resultado = subprocess.run(
        ["git", "commit", "-m", f"Atualiza vitrine - {datetime.now().strftime('%d/%m/%Y %H:%M')}"],
        cwd=REPO_DIR,
    )
    if resultado.returncode != 0:
        print("Nada novo para publicar (sem mudanças desde a última execução).")
        return
    subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
    print("Vitrine publicada com sucesso.")


def main():
    ofertas = buscar_ofertas()
    if not ofertas:
        print("Nenhuma oferta aprovada encontrada — abortando pra não publicar página vazia.")
        return
    html_final = montar_html(ofertas)
    (REPO_DIR / "index.html").write_text(html_final, encoding="utf-8")
    print(f"{len(ofertas)} ofertas escritas em index.html.")
    publicar_no_git()


if __name__ == "__main__":
    main()
