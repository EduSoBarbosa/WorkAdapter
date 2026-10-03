# Backend completo do WorkAdapter

Este pacote reúne o código entregue nesta conversa: banco SQLAlchemy/SQLite, repository, API FastAPI com todas as rotas, serviços Qwen e construtor PDF. Os arquivos antigos de instruções registram etapas incrementais; siga este guia para a instalação completa.

## Restaurar

1. Extraia este ZIP primeiro em uma pasta separada e confira a pasta backend.
2. Preserve qualquer arquivo .db, .db-wal e .db-shm que ainda existir no seu projeto antes de copiar arquivos. O ZIP não contém seus dados pessoais nem recupera dados apagados.
3. Copie a pasta backend completa para a raiz do WorkAdapter, ao lado do frontend. Não coloque backend dentro de backend. Preserve alterações próprias que ainda existirem.
4. Na raiz WorkAdapter, ative seu ambiente virtual e execute:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api.main_router:app --reload
```

Se precisar criar o ambiente no Ubuntu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api.main_router:app --reload
```

Abra http://127.0.0.1:8000/docs. O banco padrão fica em backend/database/workadapter.db e será criado vazio se não existir. Para usar outro banco existente, defina WORKADAPTER_DB com seu caminho antes de iniciar a API.

## IA e PDF

O Ollama precisa estar disponível em http://127.0.0.1:11434 para as rotas de IA. Use ollama list para conferir qwen3:8b. Se faltar, use ollama pull qwen3:8b. Se o serviço estiver parado, inicie ollama serve em outro terminal.

As quatro rotas POST ficam em /api/usuarios/{usuario_id}/ia/: curriculos, perfil, match e estudos. A geração com salvar=true salva o currículo. O download fica em GET /api/usuarios/{usuario_id}/curriculos/{curriculo_id}/pdf; use ?inline=true para abrir no navegador. PDF e CRUD não precisam executar inferência.

O arquivo agents/.env.example documenta variáveis de ambiente; não é carregado automaticamente. Esta entrega usa Qwen. Não inclui um decision_model.py para tev1, pois esse módulo não foi implementado nos arquivos que entregamos.

## Testes

```bash
python -m pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/agents/tests -v
python -m unittest discover -s backend/pdf/tests -v
```

Os testes de IA usam respostas controladas; não avaliam o modelo real do seu computador. A API permanece sem autenticação e com CORS aberto para o projeto local.

Este pacote recupera o código disponível nesta conversa. Mudanças feitas apenas no seu computador, seu ambiente virtual e registros SQLite não estão incluídos.
