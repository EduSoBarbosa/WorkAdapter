# WorkAdapter com Docker Compose (Ubuntu / Docker Engine nativo)

Este pacote adiciona compose.yaml, LEIA-ME-DOCKER.md e a pasta docker. Não contém backend, frontend ou banco: use os arquivos completos que já estão no projeto. Extraia em uma pasta separada e copie apenas esses arquivos para a raiz WorkAdapter, ao lado de backend e frontend. Preserve configurações Docker próprias, se já existirem.

## 1. Conferir instalação

```bash
docker --version
docker compose version
```

É necessário Docker Engine com o plugin Compose (comando com espaço: docker compose). Se faltar, siga https://docs.docker.com/engine/install/ubuntu/ para instalar no Ubuntu. O pacote foi preparado para Docker Engine nativo Linux; Docker Desktop, Windows e macOS exigem adaptações ou ativação específica da rede host.

Se o Docker pedir permissão para acessar o daemon, use sudo nos comandos docker abaixo. Não é necessário mudar as permissões do socket.

## 2. Primeira execução

Pare o npm/Vite e o uvicorn antigos com Ctrl+C em seus terminais. Isso libera a porta 8000. Deixe o serviço Ollama ativo: os containers usam o modelo já instalado e a configuração de GPU atual. Confira qwen3:8b com ollama list.

```bash
cd /home/eduardo/Projetos/WorkAdapter
export LOCAL_UID=$(id -u)
export LOCAL_GID=$(id -g)
docker compose up -d --build
```

Se precisar de sudo, mantenha os IDs do seu usuário explicitamente:

```bash
sudo env LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" docker compose up -d --build
```

Abra http://localhost:8080. Swagger: http://127.0.0.1:8000/docs.

Na primeira execução, Docker baixa imagens/dependências e compila React. Não é preciso ativar venv, executar npm nem uvicorn no computador. O navegador chama /api no mesmo endereço do site; Nginx encaminha para FastAPI. O timeout do proxy comporta as duas tentativas de geração do cliente Qwen.

A porta mudou de 5173 para 8080. O localStorage do navegador pertence à origem anterior, então o seletor de perfil pode voltar ao primeiro perfil. Os cadastros SQLite continuam os mesmos.

## 3. Uso diário

```bash
# Iniciar os containers já criados:
docker compose start

# Parar:
docker compose stop

# Ver estado:
docker compose ps

# Ver logs (Ctrl+C sai dos logs; não para os serviços):
docker compose logs -f --tail=100
```

Com restart: unless-stopped, os containers voltam quando o Docker reinicia, exceto se você os tiver parado explicitamente. A inicialização automática depende também de o serviço Docker iniciar no sistema. O serviço Ollama continua gerenciado no Ubuntu, fora do Compose; se estiver parado, apenas as funções de IA falham.

Se mudar código ou dependências, reconstrua a partir da raiz:

```bash
export LOCAL_UID=$(id -u)
export LOCAL_GID=$(id -g)
docker compose up -d --build
```

Este modo serve o React compilado: não tem hot reload. Alterações no código entram após rebuild. Para desenvolvimento com reload, o fluxo npm/uvicorn anterior continua disponível depois de parar os containers.

## Banco e dados

O backend monta ./backend/database em /data e usa /data/workadapter.db. Esse é o mesmo arquivo backend/database/workadapter.db usado por padrão na execução anterior. O banco não é incluído na imagem e não é apagado ao recriar containers ou executar docker compose down.

Se você configurou WORKADAPTER_DB para um banco diferente no fluxo antigo, ajuste source do volume e WORKADAPTER_DB no compose.yaml ANTES de iniciar. Caso contrário, será aberto/criado o banco padrão, que pode estar vazio. Não mova um banco em uso.

O processo Python executa com seu UID/GID (padrão 1000:1000). Se houver Permission denied no SQLite, confira os IDs com id e execute o comando com LOCAL_UID/LOCAL_GID acima. A pasta do banco e o arquivo precisam ser graváveis pelo seu usuário. Não use chmod 777.

Faça backup com o backend parado, copiando a pasta backend/database para outro local. Preserve também eventuais arquivos -wal e -shm. Nenhum cadastro é incluído no ZIP.

## Ollama e portas

A rede host permite que os containers Linux acessem o Ollama já disponível em 127.0.0.1:11434. Não precisa alterar OLLAMA_HOST do serviço, publicar Ollama na rede nem baixar outro modelo. O Compose fixa QWEN_MODEL=qwen3:8b; tev1 permanece fora deste fluxo, como no backend atual.

Nginx escuta somente 127.0.0.1:8080 e FastAPI somente 127.0.0.1:8000. A configuração é para uso local. A rede host compartilha a rede do computador, por isso não há ports no Compose. Não execute dois backends simultaneamente na porta 8000.

Se a API iniciar mas IA falhar, verifique ollama list e o serviço Ollama no Ubuntu. A saúde do backend verifica /health, não a disponibilidade do modelo.

## Arquivos adicionados

- compose.yaml: os dois serviços, reinício, saúde e persistência.
- docker/Dockerfile.api: imagem Python/FastAPI.
- docker/Dockerfile.web: build React em Node e execução Nginx.
- docker/nginx.conf: site e proxy de API/PDF.
- docker/Dockerfile.*.dockerignore: excluem bancos, ambientes, segredos e builds dos contextos correspondentes.

## Validação e referências

Estrutura YAML e correspondência dos arquivos verificados; o frontend já passou pelo build de produção. Este ambiente não possui Docker Engine: o build das imagens, o Compose e o Nginx dentro dos containers ainda precisam ser executados no seu computador.

Rede host: https://docs.docker.com/engine/network/drivers/host/
Instalação Ubuntu: https://docs.docker.com/engine/install/ubuntu/
