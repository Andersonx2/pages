"""
Instagram Photo Downloader v2.0 - Anti-Bloqueio
Anderson Gonçalves - Freedom Pulse

MELHORIAS:
- Rate limiting inteligente
- Salvamento de sessão
- Delays entre requisições
- Tratamento robusto de erros
"""

import instaloader
from datetime import datetime, timedelta
import os
import sys
import time

# Configurações
PERFIL_ALVO = "mairavida.adv"
DIAS_RETROATIVOS = 365
PASTA_DESTINO = "retrospectiva_mairavida"
SESSAO_ARQUIVO = "instagram_session"

# Configurações anti-bloqueio
DELAY_ENTRE_POSTS = 3  # Segundos entre cada download
MAX_TENTATIVAS = 3
DELAY_APOS_ERRO = 30  # Segundos para aguardar após erro

def criar_pasta_destino():
    """Cria a pasta de destino"""
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
        print(f"✓ Pasta criada: {PASTA_DESTINO}")
    else:
        print(f"✓ Usando pasta: {PASTA_DESTINO}")

def fazer_login(loader):
    """
    Login OBRIGATÓRIO para evitar bloqueios
    Sessão é salva para reusar depois
    """
    print("\n" + "=" * 60)
    print("LOGIN NECESSÁRIO")
    print("=" * 60)
    print("Instagram bloqueia downloads sem autenticação.")
    print("Sua senha NÃO é enviada para nós, apenas para o Instagram.\n")
    
    # Tentar carregar sessão salva
    try:
        loader.load_session_from_file(SESSAO_ARQUIVO)
        print("✓ Sessão anterior carregada com sucesso!")
        return True
    except:
        print("⚠️  Nenhuma sessão anterior encontrada. Fazendo login...")
    
    # Fazer novo login
    tentativas = 0
    while tentativas < 3:
        usuario = input("\nUsuário do Instagram: ").strip()
        
        if not usuario:
            print("✗ Usuário é obrigatório!")
            tentativas += 1
            continue
            
        senha = input("Senha: ").strip()
        
        if not senha:
            print("✗ Senha é obrigatória!")
            tentativas += 1
            continue
        
        try:
            print("\n🔄 Fazendo login...")
            loader.login(usuario, senha)
            
            # Salvar sessão para próximas vezes
            loader.save_session_to_file(SESSAO_ARQUIVO)
            print("✓ Login realizado! Sessão salva para próximo uso.")
            return True
            
        except instaloader.exceptions.BadCredentialsException:
            print("✗ Usuário ou senha incorretos!")
            tentativas += 1
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            print("✗ Esta conta usa autenticação de dois fatores.")
            print("Infelizmente, não suportamos 2FA via script.")
            print("Dica: Crie uma conta secundária sem 2FA para downloads.")
            return False
        except Exception as e:
            print(f"✗ Erro no login: {e}")
            tentativas += 1
    
    print("\n✗ Falha no login após 3 tentativas.")
    return False

def baixar_com_retry(loader, post, tentativa=1):
    """
    Tenta baixar um post com retry em caso de erro
    """
    try:
        loader.download_post(post, target=PASTA_DESTINO)
        return True
    except instaloader.exceptions.ConnectionException as e:
        if tentativa < MAX_TENTATIVAS:
            print(f"   ⚠️  Erro de conexão. Tentativa {tentativa}/{MAX_TENTATIVAS}")
            print(f"   ⏳ Aguardando {DELAY_APOS_ERRO}s antes de retry...")
            time.sleep(DELAY_APOS_ERRO)
            return baixar_com_retry(loader, post, tentativa + 1)
        else:
            raise e
    except Exception as e:
        raise e

def baixar_fotos_v2():
    """
    Versão melhorada com proteções anti-bloqueio
    """
    print("=" * 60)
    print("INSTAGRAM DOWNLOADER v2.0 - ANTI-BLOQUEIO")
    print("=" * 60)
    
    criar_pasta_destino()
    
    # Configurar Instaloader com rate limiting
    loader = instaloader.Instaloader(
        dirname_pattern=PASTA_DESTINO,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=True,
        compress_json=False,
        post_metadata_txt_pattern="",
        max_connection_attempts=3,  # Limitar tentativas
        request_timeout=30.0,  # Timeout de 30s
        rate_controller=lambda query_type: time.sleep(2)  # 2s entre requests
    )
    
    # Login obrigatório
    if not fazer_login(loader):
        print("\n✗ Não foi possível fazer login. Abortando.")
        return
    
    try:
        # Carregar perfil
        print(f"\n📱 Carregando perfil: @{PERFIL_ALVO}...")
        profile = instaloader.Profile.from_username(loader.context, PERFIL_ALVO)
        
        if profile.is_private and not profile.followed_by_viewer:
            print(f"\n⚠️  ATENÇÃO: @{PERFIL_ALVO} é PRIVADO!")
            print("Você precisa seguir este perfil para baixar as fotos.")
            return
        
        # Data limite
        data_limite = datetime.now() - timedelta(days=DIAS_RETROATIVOS)
        print(f"📅 Período: {data_limite.strftime('%d/%m/%Y')} até hoje")
        
        # Estatísticas
        posts_analisados = 0
        fotos_baixadas = 0
        videos_ignorados = 0
        erros = 0
        
        print("\n🔄 Iniciando download (COM DELAY entre posts)...\n")
        print("⏱️  Isso pode demorar. Instagram limita velocidade de requisições.")
        print("🛑 Pressione Ctrl+C para pausar/parar a qualquer momento.\n")
        
        # Iterar posts
        for post in profile.get_posts():
            posts_analisados += 1
            
            # Verificar data
            if post.date < data_limite:
                print(f"\n⏹️  Alcançamos posts de {post.date.strftime('%d/%m/%Y')} (antes do período)")
                break
            
            # Apenas fotos
            if post.is_video:
                videos_ignorados += 1
                print(f"⏭️  [{posts_analisados}] Vídeo ignorado: {post.date.strftime('%d/%m/%Y')}")
                continue
            
            # Tentar baixar
            try:
                print(f"⬇️  [{fotos_baixadas + 1}] Baixando: {post.date.strftime('%d/%m/%Y %H:%M')}", end="")
                
                if baixar_com_retry(loader, post):
                    fotos_baixadas += 1
                    print(" ✓")
                    
                    # DELAY entre posts (crucial!)
                    if DELAY_ENTRE_POSTS > 0:
                        print(f"   ⏳ Aguardando {DELAY_ENTRE_POSTS}s (anti-bloqueio)...")
                        time.sleep(DELAY_ENTRE_POSTS)
                
            except instaloader.exceptions.LoginRequiredException:
                print("\n\n✗ Sessão expirou! Execute novamente o script.")
                # Deletar sessão antiga
                try:
                    os.remove(SESSAO_ARQUIVO)
                except:
                    pass
                return
                
            except Exception as e:
                erros += 1
                print(f" ✗ ERRO: {str(e)[:100]}")
                
                if erros >= 5:
                    print("\n⚠️  Muitos erros consecutivos. Parando para evitar bloqueio.")
                    break
        
        # Resumo final
        print("\n" + "=" * 60)
        print("RESUMO FINAL")
        print("=" * 60)
        print(f"Posts analisados: {posts_analisados}")
        print(f"✓ Fotos baixadas: {fotos_baixadas}")
        print(f"⏭️  Vídeos ignorados: {videos_ignorados}")
        print(f"✗ Erros: {erros}")
        print(f"\n📁 Pasta: {os.path.abspath(PASTA_DESTINO)}")
        print("=" * 60)
        
        if fotos_baixadas > 0:
            print("\n🎉 Download concluído com sucesso!")
        else:
            print("\n⚠️  Nenhuma foto foi baixada. Verifique:")
            print("   - Se o perfil tem posts de fotos no período")
            print("   - Se o perfil é privado e você o segue")
            print("   - Se sua sessão está válida")
        
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"\n✗ ERRO: Perfil @{PERFIL_ALVO} não existe")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Download pausado pelo usuário!")
        print(f"✓ Fotos baixadas até agora: {fotos_baixadas}")
        print(f"📁 Pasta: {os.path.abspath(PASTA_DESTINO)}")
        print("\n💡 Execute novamente para continuar de onde parou")
        
    except Exception as e:
        print(f"\n✗ ERRO GERAL: {e}")
        print("\nVerifique:")
        print("1. Sua conexão com internet")
        print("2. Se o perfil existe e é acessível")
        print("3. Se você segue o perfil (se for privado)")

if __name__ == "__main__":
    try:
        baixar_fotos_v2()
    except KeyboardInterrupt:
        print("\n\n👋 Programa encerrado")
        sys.exit(0)