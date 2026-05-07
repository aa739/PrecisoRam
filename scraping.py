import re
import json
from playwright.sync_api import sync_playwright
from .models import Produto, Marca

# ------------------- PcComponentes -------------------
def diagnosticar_pccomponentes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto("https://www.pccomponentes.pt/memorias-ram",
                  wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    # Verifica se o JSON ainda existe
    if "__staticRouterHydrationData" in html:
        print("✅ JSON ainda existe")
    else:
        print("❌ JSON desapareceu — site mudou estrutura")

    # Guarda HTML para análise
    with open("pcc_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML guardado em pcc_debug.html")

def extrair_produtos_pccomponentes(url_categoria):
    """Usa Playwright + BeautifulSoup para extrair produtos da PcComponentes via DOM."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=['--disable-gpu', '--no-sandbox']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url_categoria, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('[class*="productCard"]', timeout=20000)
            page.wait_for_timeout(3000)
            html = page.content()
        finally:
            browser.close()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('[class*="productCard"]')
    print(f"PcComponentes: encontrados {len(cards)} cards")

    produtos = []
    for card in cards:
        # Nome
        nome_elem = card.select_one('.product-card__title')
        if not nome_elem:
            continue
        nome = nome_elem.get_text(strip=True)

        # Preço
        preco_elem = card.select_one('.product-card__price-container')
        if not preco_elem:
            continue
        preco_texto = preco_elem.get_text(strip=True)
        preco_texto_limpo = preco_texto.replace('.', '').replace(',', '.').replace('€', '').strip()
        match = re.search(r'[\d.]+', preco_texto_limpo)
        if not match:
            continue
        try:
            preco = float(match.group())
        except ValueError:
            continue

        # URL — o link está no card pai ou num elemento <a> acima
        link_elem = card.find_parent('a') or card.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            url_produto = href if href.startswith('http') else f"https://www.pccomponentes.pt{href}"
        else:
            url_produto = ""

        # Imagem
        img_elem = card.select_one('img')
        img_url = img_elem.get('src', '') if img_elem else ''

        # Marca (primeira palavra do nome)
        marca_nome = nome.split()[0] if nome.split() else 'Genérica'

        # Velocidade
        velocidade = ""
        m = re.search(r'(\d{4,5})\s*MHz', nome, re.IGNORECASE)
        if m:
            velocidade = f"{m.group(1)}MHz"

        produtos.append({
            "nome": nome,
            "preco": preco,
            "marca_nome": marca_nome,
            "velocidade": velocidade,
            "url": url_produto,
            "imagem": img_url,
            "loja": "PcComponentes"
        })

    return produtos



# ------------------- PCDiga -------------------
def diagnosticar_pcdiga():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto("https://www.pcdiga.com/componentes/memorias-ram", 
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        
        # Guarda o HTML para análise
        with open("pcdiga_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        
        # Testa seletores comuns e diz quais existem
        seletores = [
            ".product-item", ".product-card", ".product-tile",
            "[data-product-id]", ".listing-product", 
            "article", ".ProductCard", ".ProductList"
        ]
        for s in seletores:
            count = len(page.query_selector_all(s))
            if count > 0:
                print(f"✅ '{s}' → {count} elementos")
        
        browser.close()

def extrair_produtos_pcdiga(url_categoria):
    produtos = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
        headless=True,
        executable_path="/usr/bin/chromium",
        args=['--disable-gpu', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            page.goto(url_categoria, wait_until="domcontentloaded", timeout=60000)
            # Aguarda que os cards de produto apareçam
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            elementos = page.query_selector_all("div.bg-background-off:has(p.text-primary)")
            print(f"PCDiga: encontrados {len(elementos)} elementos")

            for elem in elementos:
                # Nome
                nome_elem = elem.query_selector("h3")
                if not nome_elem:
                    continue
                nome = nome_elem.inner_text().strip()
                if not nome:
                    continue

                # Preço — classe "text-primary" no <p>
                preco_elem = elem.query_selector("p.text-primary")
                if not preco_elem:
                    continue
                preco_texto = preco_elem.inner_text().strip()
                # Formato português: "459,90 €" ou "1.299,99 €"
                preco_texto_limpo = preco_texto.replace('\xa0', '').replace('€', '').strip()
                preco_texto_limpo = preco_texto_limpo.replace('.', '').replace(',', '.')
                try:
                    preco = float(preco_texto_limpo)
                except ValueError:
                    continue

                # URL
                link_elem = elem.query_selector("a[href]")
                if not link_elem:
                    continue
                href = link_elem.get_attribute("href")
                if not href:
                    continue
                url_produto = href if href.startswith("http") else f"https://www.pcdiga.com{href}"

                # Imagem
                img_elem = elem.query_selector("img")
                img_url = img_elem.get_attribute("src") if img_elem else ""
                if img_url and img_url.startswith("//"):
                    img_url = "https:" + img_url

                # Marca (primeira palavra do nome)
                marca_nome = nome.split()[0] if nome.split() else "Genérica"

                # Velocidade
                velocidade = ""
                m = re.search(r'(\d{4,5})\s*MHz', nome, re.IGNORECASE)
                if m:
                    velocidade = f"{m.group(1)}MHz"

                produtos.append({
                    "nome": nome,
                    "preco": preco,
                    "marca_nome": marca_nome,
                    "velocidade": velocidade,
                    "url": url_produto,
                    "imagem": img_url,
                    "loja": "PCDiga"
                })

        except Exception as e:
            print(f"Erro no scraping da PCDiga: {e}")
        finally:
            browser.close()

    return produtos


# ------------------- Função principal de atualização -------------------
def atualizar_produtos():
    """Atualiza a base de dados com produtos da PcComponentes e da PCDiga."""
    print("=== Scraping PcComponentes ===")
    produtos_pcc = extrair_produtos_pccomponentes("https://www.pccomponentes.pt/memorias-ram")
    print(f"Encontrados {len(produtos_pcc)} produtos na PcComponentes.")

    print("\n=== Scraping PCDiga ===")
    produtos_pcdiga = extrair_produtos_pcdiga("https://www.pcdiga.com/componentes/memorias-ram")
    print(f"Encontrados {len(produtos_pcdiga)} produtos na PCDiga.")

    todos_produtos = produtos_pcc + produtos_pcdiga
    novos = 0
    for dados in todos_produtos:
        if dados["preco"] <= 0:
            continue
        marca, _ = Marca.objects.get_or_create(nome=dados["marca_nome"])
        obj, created = Produto.objects.update_or_create(
            url=dados["url"],
            defaults={
                "nome": dados["nome"],
                "preco": dados["preco"],
                "marca": marca,
                "velocidade": dados["velocidade"],
                "loja": dados["loja"],
                "imagem": dados["imagem"],
            }
        )
        if created:
            novos += 1
            print(f"Novo: {dados['nome']} - {dados['preco']}€ ({dados['loja']})")
        else:
            print(f"Atualizado: {dados['nome']} ({dados['loja']})")
    print(f"\nConcluído. Total de novos produtos: {novos}")
