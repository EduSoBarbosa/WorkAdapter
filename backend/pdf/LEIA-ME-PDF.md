# Construtor de currículo PDF

Copie a pasta backend deste pacote para a raiz do WorkAdapter, mesclando com a existente. O pacote depende dos arquivos de banco, API e integração Qwen entregues anteriormente. Inclui main_router.py atualizado com a rota de PDF; se você fez mudanças próprias nesse arquivo, acrescente somente o import do módulo pdf e sua inclusão na lista de routers.

## Instalação

Com o ambiente virtual do backend ativado, execute na raiz do projeto:

```bash
python -m pip install -r backend/pdf/requirements-pdf.txt
python -m uvicorn backend.api.main_router:app --reload
```

Não há migração de banco nesta etapa.

## Download

A rota usa um currículo já salvo no SQLite:

```text
GET /api/usuarios/{usuario_id}/curriculos/{curriculo_id}/pdf
```

Exemplo, substituindo os IDs pelos existentes no seu banco:

```text
http://127.0.0.1:8000/api/usuarios/1/curriculos/1/pdf
```

Para abrir no navegador em vez de solicitar download:

```text
http://127.0.0.1:8000/api/usuarios/1/curriculos/1/pdf?inline=true
```

Também está disponível no Swagger em http://127.0.0.1:8000/docs, grupo PDF.

O fluxo com IA é gerar e salvar o currículo pela rota de IA, obter o ID salvo e usar esse ID na rota de PDF. A renderização não faz outra chamada ao Qwen. O botão no frontend será integrado separadamente.

## Formatos aceitos

- Currículo estruturado produzido pelo serviço Qwen do projeto, com schema_versao igual a 1.0: nome, contato, objetivo, resumo, habilidades, experiências, projetos, formações, cursos e idiomas.
- Currículo manual no formato exato {"texto": "Conteúdo do currículo"}. O texto e suas quebras são preservados como texto simples; não há interpretação de HTML.

O PDF usa papel A4, uma coluna, fonte incorporada, texto selecionável, títulos discretos e numeração de páginas. A fonte cobre português e caracteres latinos comuns; não oferece cobertura universal de todos os alfabetos.

Os metadados internos da IA, auditoria, IDs e fontes não são exibidos. Links HTTP/HTTPS podem ser clicados; o construtor não baixa recursos externos. Conteúdos incompatíveis recebem erro 422. Currículos inexistentes ou pertencentes a outro usuário recebem 404. O projeto continua sem autenticação, conforme a fase local anterior.

A rota produz bytes em memória: não altera conteudo, perfil_snapshot ou arquivo_url. O download reflete a versão salva, sem reconstruir o perfil com os dados atuais do usuário. O construtor limita o JSON a 150 mil caracteres e as listas principais a 100 itens.

## Uso direto em Python

```python
from backend.pdf.constructor import gerar_pdf, salvar_pdf

pdf_bytes = gerar_pdf({"texto": "Marina Oliveira\nDesenvolvedora Python"})
salvar_pdf({"texto": "Marina Oliveira\nDesenvolvedora Python"}, "curriculo.pdf")
```

salvar_pdf é um utilitário para chamadas locais explícitas. A rota HTTP não recebe caminhos de arquivo.

## Testes

pypdf é necessário apenas para os testes, além das dependências anteriores da API:

```bash
python -m pip install pypdf
python -m unittest discover -s backend/pdf/tests -v
```

Os cinco testes verificam estrutura, acentos, conteúdo extenso, tratamento de texto e links, formatos inválidos, download, vínculo com usuário e preservação do registro. O arquivo exemplos/curriculo_exemplo.pdf contém dados fictícios para conferir o visual.
