from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import urllib.parse
import re


PHONE_RE = re.compile(
    r"(?:(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4})[-\s]?\d{4})"
)


def limpar_texto(valor):
    if not valor:
        return ""
    return " ".join(valor.replace("\n", " ").split()).strip()


def aceitar_cookies(page):
    """
    Tenta aceitar/rejeitar cookies caso o Google mostre uma tela de consentimento.
    Se não aparecer, segue normalmente.
    """
    possiveis_botoes = [
        "Aceitar tudo",
        "Accept all",
        "Concordo",
        "I agree",
        "Rejeitar tudo",
        "Reject all",
    ]

    for texto in possiveis_botoes:
        try:
            botao = page.get_by_role("button", name=texto)
            if botao.count() > 0:
                botao.first.click(timeout=3000)
                page.wait_for_timeout(1000)
                return
        except Exception:
            pass


def obter_texto(locator, padrao="N/A", timeout=3000):
    try:
        if locator.count() > 0:
            texto = locator.first.inner_text(timeout=timeout)
            texto = limpar_texto(texto)
            return texto if texto else padrao
    except Exception:
        pass

    return padrao


def obter_atributo(locator, atributo, padrao="", timeout=3000):
    try:
        if locator.count() > 0:
            valor = locator.first.get_attribute(atributo, timeout=timeout)
            valor = limpar_texto(valor)
            return valor if valor else padrao
    except Exception:
        pass

    return padrao


def extrair_telefone(page):
    seletores_telefone = [
        'button[data-item-id^="phone:tel:"]',
        'button[aria-label^="Telefone:"]',
        'button[aria-label^="Phone:"]',
        'button[aria-label*="+55"]',
    ]

    for seletor in seletores_telefone:
        telefone_bruto = obter_atributo(page.locator(seletor), "aria-label")
        if telefone_bruto:
            telefone = re.sub(
                r"^(Telefone|Phone|Teléfono|Tel):\s*",
                "",
                telefone_bruto,
                flags=re.IGNORECASE,
            )
            return limpar_texto(telefone)

    try:
        texto_pagina = page.locator("body").inner_text(timeout=3000)
        match = PHONE_RE.search(texto_pagina)
        if match:
            return limpar_texto(match.group(0))
    except Exception:
        pass

    return "N/A"


def extrair_website(page):
    seletores_site = [
        'a[data-item-id="authority"]',
        'a[aria-label^="Website:"]',
        'a[aria-label^="Site:"]',
    ]

    for seletor in seletores_site:
        website = obter_atributo(page.locator(seletor), "href")
        if website:
            return website

    return "Não listado"


def extrair_endereco(page):
    seletores_endereco = [
        'button[data-item-id="address"]',
        'button[aria-label^="Endereço:"]',
        'button[aria-label^="Address:"]',
    ]

    for seletor in seletores_endereco:
        endereco = obter_atributo(page.locator(seletor), "aria-label")
        if endereco:
            endereco = re.sub(
                r"^(Endereço|Address|Dirección):\s*",
                "",
                endereco,
                flags=re.IGNORECASE,
            )
            return limpar_texto(endereco)

    return "N/A"


def extrair_detalhes_local(page, nome_fallback, link_mapa):
    nome = obter_texto(page.locator("h1.DUwDvf"), padrao=nome_fallback)

    if nome == "N/A":
        nome = obter_texto(page.locator("h1"), padrao=nome_fallback)

    telefone = extrair_telefone(page)
    website = extrair_website(page)
    endereco = extrair_endereco(page)

    avaliacao = obter_texto(
        page.locator('div.F7nice span[aria-hidden="true"]'),
        padrao="N/A",
    )

    return {
        "Nome da Clínica": nome,
        "Telefone": telefone,
        "Website Atual": website,
        "Endereço": endereco,
        "Avaliação": avaliacao,
        "Link Google Maps": link_mapa,
    }


def coletar_links_resultados(page, max_scrolls=10, pausa_ms=2000):
    feed = page.locator('div[role="feed"]').first

    try:
        feed.wait_for(timeout=20000)
    except PlaywrightTimeoutError:
        raise RuntimeError(
            "O painel de resultados do Google Maps não carregou. "
            "Pode ter ocorrido bloqueio, captcha ou mudança na estrutura da página."
        )

    ultima_quantidade = 0
    tentativas_sem_novos = 0

    for _ in range(max_scrolls):
        feed.evaluate("(el) => el.scrollTo(0, el.scrollHeight)")
        page.wait_for_timeout(pausa_ms)

        quantidade_atual = page.locator('a.hfpxzc, a[href*="/maps/place/"]').count()

        if quantidade_atual == ultima_quantidade:
            tentativas_sem_novos += 1
            if tentativas_sem_novos >= 2:
                break
        else:
            tentativas_sem_novos = 0
            ultima_quantidade = quantidade_atual

    links_locator = page.locator('a.hfpxzc, a[href*="/maps/place/"]')

    resultados = links_locator.evaluate_all(
        """
        (links) => links
            .map((a) => ({
                nome: a.getAttribute("aria-label") || a.textContent || "",
                link: a.href || ""
            }))
            .filter((item) => item.nome && item.link && item.link.includes("/maps/place/"))
        """
    )

    resultados_unicos = []
    links_vistos = set()

    for item in resultados:
        nome = limpar_texto(item.get("nome", ""))
        link = item.get("link", "")

        if not nome or not link or link in links_vistos:
            continue

        links_vistos.add(link)
        resultados_unicos.append({
            "nome": nome,
            "link": link,
        })

    return resultados_unicos


def extrair_clinicas(
    termo_busca,
    max_scrolls=10,
    arquivo_saida="leads_clinicas.csv",
    headless=False,
):
    dados_extraidos = []

    termo_codificado = urllib.parse.quote_plus(termo_busca)
    url_busca = f"https://www.google.com/maps/search/{termo_codificado}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        context = browser.new_context(
            locale="pt-BR",
            viewport={"width": 1366, "height": 768},
        )

        page = context.new_page()
        page.set_default_timeout(15000)

        try:
            page.goto(url_busca, wait_until="domcontentloaded", timeout=60000)
            aceitar_cookies(page)

            resultados = coletar_links_resultados(
                page,
                max_scrolls=max_scrolls,
                pausa_ms=2000,
            )

            print(f"{len(resultados)} resultados encontrados na listagem.")

            for indice, resultado in enumerate(resultados, start=1):
                nome_fallback = resultado["nome"]
                link_mapa = resultado["link"]

                try:
                    print(f"Extraindo {indice}/{len(resultados)}: {nome_fallback}")

                    page.goto(link_mapa, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2500)

                    dados = extrair_detalhes_local(
                        page=page,
                        nome_fallback=nome_fallback,
                        link_mapa=link_mapa,
                    )

                    dados_extraidos.append(dados)

                except Exception as erro:
                    print(f"Erro ao extrair '{nome_fallback}': {erro}")
                    continue

        finally:
            browser.close()

    if not dados_extraidos:
        print(
            "Nenhum dado foi extraído. "
            "Verifique se houve captcha, bloqueio ou alteração no layout do Google Maps."
        )
        return

    df = pd.DataFrame(dados_extraidos)

    df.drop_duplicates(
        subset=["Nome da Clínica", "Telefone", "Link Google Maps"],
        inplace=True,
    )

    df.to_csv(
        arquivo_saida,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    print(f"Extração concluída! {len(df)} leads salvos em: {arquivo_saida}")


if __name__ == "__main__":
    nicho = "Clínica de implante dentário em Salvador"
    extrair_clinicas(
        termo_busca=nicho,
        max_scrolls=10,
        arquivo_saida="leads_clinicas.csv",
        headless=False,
    )