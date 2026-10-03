# API local do WorkAdapter

Copie a pasta `api` para `backend/api`, mantendo os `database/models.py` e
`database/repository.py` entregues anteriormente. Não altere esses dois arquivos.
Requer Python 3.10+.

Na raiz do projeto, com a venv ativada:

```bash
python -m pip install -r backend/api/requirements-api.txt
python -m uvicorn backend.api.main_router:app --reload
```

Swagger: http://127.0.0.1:8000/docs
API: http://127.0.0.1:8000/api
Health: http://127.0.0.1:8000/health

O banco padrão continua em `backend/database/workadapter.db`. Para trocar,
defina `WORKADAPTER_DB` com o caminho desejado. As tabelas ausentes são criadas
no startup; tabelas existentes não são migradas.

## Rotas

- `/api/usuarios`: POST e GET.
- `/api/usuarios/{usuario_id}`: GET, PATCH e DELETE.
- `/api/usuarios/{usuario_id}/perfil`: GET do perfil completo.
- `/api/usuarios/{usuario_id}/{recurso}`: POST e GET; recursos: experiencias,
  formacoes, cursos, projetos, idiomas, curriculos e candidaturas.
- Acrescente `/{id}` para GET, PATCH e DELETE de cada recurso.
- Para experiências, formações, cursos e projetos: PUT `/{id}/habilidades`,
  com `{"habilidades_ids": [1, 2]}`. Lista vazia remove toda a stack.
- `/api/habilidades`: POST (obter ou criar) e GET; `/{habilidade_id}`:
  GET, PATCH e DELETE.
- `/api/usuarios/{usuario_id}/habilidades`: GET.
- `/api/usuarios/{usuario_id}/habilidades/{habilidade_id}`: PUT com
  `{"nivel": "intermediario"}` e DELETE para desvincular.
- `/api/usuarios/{usuario_id}/curriculos/{curriculo_id}/versoes`: POST
  com campos a modificar, ou `{}` para copiar.
- `/api/usuarios/{usuario_id}/candidaturas/{candidatura_id}/movimentacoes`:
  GET e POST com `{"status":"em_andamento","etapa":"Entrevista"}`.

Listagens principais aceitam `limite` (1–1000) e `offset` (>=0).
Candidaturas também aceitam `status`, `plataforma` e `busca`.
Datas: `YYYY-MM-DD`; horários: ISO 8601.
PATCH altera apenas os campos enviados. `null` limpa campos anuláveis.
Os JSON de currículos são substituídos integralmente quando enviados.

## Regras preservadas

Currículos vinculados a candidaturas retornam 409 ao editar/excluir; crie uma
nova versão para editar. Sem `perfil_snapshot` no POST, ele é capturado do
perfil atual. Salvar um currículo não chama o Ollama nem gera PDF.
Status/etapa de candidatura mudam por movimentações, preservando o histórico.
As movimentações são somente de acréscimo: correções são novos eventos.
DELETE de usuário remove seus dados; DELETE de candidatura remove seu histórico.
O catálogo de habilidades é compartilhado; só se excluem habilidades sem vínculos.

## Integração

A API não exige login. Todas as origens, métodos e cabeçalhos CORS estão
liberados, sem cookies cross-origin. O comando acima escuta apenas no localhost.
Cada requisição usa sua própria sessão/transação, confirmada antes da resposta;
em caso de erro, ocorre rollback. HTTP: 404 não encontrado, 409 conflito,
422 entrada inválida, 201 criação e 204 exclusão.
Os imports assumem execução a partir da raiz, via `backend.api.main_router`.
