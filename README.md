# ◆ J O N — assistente pessoal por voz (Windows)

Assistente pessoal com painel HUD futurista (estilo J.A.R.V.I.S., em roxo), controle por voz,
IA local offline (Ollama) e chat por texto.

## Funcionalidades
- **Voz**: segure `F9` e fale, ou modo mãos-livres ("Jon, …")
- **Chat com IA** (`F2`): converse por texto com a IA local, com respostas em tempo real
- **IA local (Ollama `qwen3.5:4b`)**: entende frases livres, aprende apelidos e fatos sobre você
- **Spotify**: tocar, pausar, volume, loop, aleatório, curtir, fila
- **Dia a dia**: lembretes, timers, rotinas, clima, "bom dia", status do PC
- **Painéis**: sistema (CPU/RAM/GPU/discos), apps recentes, downloads, e-mails, notificações do Windows
- **Big Picture** (`F11`): tela cheia com suporte a controle de Xbox
- **Celular**: página PWA privada via Tailscale

## Instalação
1. Instale o **Python 3.12** (marque "Add python.exe to PATH").
2. Rode `1_instalar.bat` — instala as bibliotecas e cria o atalho "Jon" na Área de Trabalho.
3. (Opcional) Instale o **Ollama** e rode `3_baixar_ia.bat` para ativar a IA local.
4. Abra o Jon pelo atalho. Na primeira vez ele pergunta seu nome, cidade e (opcional) o Spotify Client ID.

Veja o [LEIA-ME.txt](LEIA-ME.txt) para o passo a passo completo (Spotify, e-mail e celular).

## Privacidade
Os arquivos com dados pessoais (`config.json`, `memoria.json`, `email_config.json`,
`spotify_client_id.txt`, `.spotify_token_cache`, logs…) ficam só no seu PC e estão no `.gitignore`.
