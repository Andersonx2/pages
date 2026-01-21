import instaloader
import time
from contextlib import contextmanager

# Configurações
TARGET_PROFILE = "perfil_alvo_aqui"  # Substitua pelo perfil que deseja baixar
MY_USER = "jess.ikita69"       # Seu usuário (opcional para perfis públicos, mas recomendado para evitar rate limit)
MY_PASS = "anderson260595"         # Sua senha (cuidado com a segurança)

def download_profile_media():
    # Inicializa o Instaloader com configurações conservadoras
    # sleep=True adiciona pausas aleatórias para simular comportamento humano
    L = instaloader.Instaloader(
        download_pictures=True,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        sleep=True 
    )

    try:
        # Tenta realizar o login
        # NOTA: Para perfis públicos, o login muitas vezes NÃO é necessário e evita riscos à sua conta.
        # Se o perfil for público, tente comentar as linhas de login abaixo primeiro.
        print(f"🔄 Tentando login como {MY_USER}...")
        L.login(MY_USER, MY_PASS)
        print("✅ Login realizado com sucesso.")
    except instaloader.TwoFactorAuthRequiredException:
        print("❌ Erro: Autenticação de dois fatores (2FA) está ativa. O script não suporta 2FA automático.")
        return
    except instaloader.BadCredentialsException:
        print("❌ Erro: Usuário ou senha incorretos.")
        return
    except Exception as e:
        print(f"⚠️ Aviso: Falha no login ou optou por não logar. Continuando como anônimo (pode ser limitado). Erro: {e}")

    try:
        print(f"🔍 Carregando perfil: {TARGET_PROFILE}")
        profile = instaloader.Profile.from_username(L.context, TARGET_PROFILE)

        print(f"📥 Iniciando download de {profile.mediacount} postagens...")
        
        count = 0
        # Itera sobre todos os posts do perfil
        for post in profile.get_posts():
            try:
                print(f"   [{count+1}] Baixando post de {post.date_local}...")
                L.download_post(post, target=profile.username)
                count += 1
                
                # Pausa de segurança extra (além do sleep interno do instaloader)
                # Isso reduz drasticamente a chance de ser detectado como bot
                if count % 10 == 0:
                    print("   ⏳ Pausa estratégica de 10 segundos para evitar bloqueio...")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao baixar post específico: {e}")
                continue

        print("\n✅ Download concluído!")

    except instaloader.ProfileNotExistsException:
        print(f"❌ O perfil {TARGET_PROFILE} não existe.")
    except instaloader.ConnectionException as e:
        print(f"❌ Erro de Conexão (possível bloqueio de IP ou falha de rede): {e}")
    except Exception as e:
        print(f"❌ Erro genérico: {e}")

if __name__ == "__main__":
    download_profile_media()