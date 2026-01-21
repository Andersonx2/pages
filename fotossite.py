import os
import time
import requests
import re
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES ---
URL_CATEGORIA = "https://licoeteca.com.br/meninas/calcas"
PASTA_RAIZ = "fotos_produtos_licoeteca"
TEMPO_ESPERA_PAGINA = 3

def setup_driver():
    """Configura o navegador para simular um usuário real."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # User-agent para evitar bloqueios de bot
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def limpar_nome(nome):
    """Limpa caracteres proibidos em nomes de arquivos do Windows/Linux."""
    return re.sub(r'[\\/*?:"<>|]', "", nome)

def salvar_imagem_png(url, pasta, nome_arquivo):
    """Baixa a imagem (geralmente WebP), converte e salva como PNG."""
    try:
        # Corrige URL se começar com // (padrão comum em CDNs)
        if url.startswith("//"):
            url = "https:" + url
        
        # Faz o download
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            
            # Caminho final
            caminho_final = os.path.join(pasta, f"{nome_arquivo}.png")
            
            # Converte para RGB (necessário se a original for RGBA ou P) e salva como PNG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGBA") # Mantém transparência se houver
            else:
                img = img.convert("RGB")
                
            img.save(caminho_final, "PNG")
            print(f"      ✅ Salvo: {nome_arquivo}.png")
            return True
        else:
            print(f"      ❌ Erro HTTP {response.status_code} ao baixar imagem.")
    except Exception as e:
        print(f"      ❌ Erro ao processar imagem: {e}")
    return False

def extrair_urls_da_galeria(soup):
    """
    Busca ESPECIFICAMENTE as imagens baseadas no print enviado.
    Alvo: <a data-fancybox="product-gallery"> dentro de <div class="js-product-slide">
    """
    urls = set() # Usamos set para evitar duplicatas (sliders as vezes duplicam o DOM)
    
    # 1. Encontra todos os slides do produto (baseado na classe do seu print)
    slides = soup.find_all("div", class_="js-product-slide")
    
    for slide in slides:
        # 2. Dentro do slide, busca o link que tem o fancybox (que contém a imagem grande)
        link = slide.find("a", attrs={"data-fancybox": "product-gallery"})
        
        if link and link.get("href"):
            url_imagem = link["href"]
            urls.add(url_imagem)
            
    return list(urls)

def main():
    if not os.path.exists(PASTA_RAIZ):
        os.makedirs(PASTA_RAIZ)
    
    driver = setup_driver()
    
    print(f"--- Acessando categoria: {URL_CATEGORIA} ---")
    driver.get(URL_CATEGORIA)
    time.sleep(TEMPO_ESPERA_PAGINA)

    # --- 1. ROLAGEM INFINITA (Para carregar todos os produtos da categoria) ---
    print("Carregando lista completa de produtos...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # --- 2. PEGAR LINKS DOS PRODUTOS ---
    soup_cat = BeautifulSoup(driver.page_source, "html.parser")
    links_produtos = set()
    
    # Pega apenas links que contêm '/produtos/'
    for a in soup_cat.find_all('a', href=True):
        href = a['href']
        if '/produtos/' in href and href.count('/') > 2:
            if not href.startswith('http'):
                href = href # Ajuste se necessário, mas geralmente vem completo
            links_produtos.add(href)
    
    lista_produtos = list(links_produtos)
    print(f"Total de produtos encontrados: {len(lista_produtos)}")

    # --- 3. EXTRAÇÃO PRODUTO POR PRODUTO ---
    for i, link_produto in enumerate(lista_produtos):
        # Cria nome do produto baseado na URL
        nome_produto = link_produto.strip("/").split("/")[-1]
        nome_produto = limpar_nome(nome_produto)
        
        print(f"\n[{i+1}/{len(lista_produtos)}] Extraindo: {nome_produto}")
        
        # Cria pasta individual para o produto
        pasta_produto = os.path.join(PASTA_RAIZ, nome_produto)
        if not os.path.exists(pasta_produto):
            os.makedirs(pasta_produto)

        try:
            driver.get(link_produto)
            # Espera um pouco para o JS do swiper carregar
            time.sleep(2) 
            
            soup_produto = BeautifulSoup(driver.page_source, "html.parser")
            
            # Aqui chamamos a função ajustada para o seu print
            imagens_urls = extrair_urls_da_galeria(soup_produto)
            
            if imagens_urls:
                for idx, url in enumerate(imagens_urls):
                    nome_arquivo = f"{nome_produto}_{idx+1:02d}"
                    salvar_imagem_png(url, pasta_produto, nome_arquivo)
            else:
                print("      ⚠️ Nenhuma galeria compatível encontrada.")

        except Exception as e:
            print(f"      ❌ Erro ao acessar produto: {e}")

    driver.quit()
    print("\n--- Processo Finalizado ---")

if __name__ == "__main__":
    main()