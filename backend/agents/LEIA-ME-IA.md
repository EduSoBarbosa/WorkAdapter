# Qwen3:8b — backend de carreira do WorkAdapter

Esta entrega implementa quatro funções. PDF e frontend ficam para as próximas etapas.
Não altera o schema SQLite, models.py, repository.py nem decision_model.py.

## Instalar e iniciar

Extraia na raiz `WorkAdapter`. Mescle as pastas e substitua:

- `backend/agents/gen_model.py`: substitui seu teste de pergunta única por um cliente reutilizável.
- `backend/api/main_router.py`: registra as novas rotas, o cliente e os handlers de erro.

Se tiver modificado seu main_router.py desde a entrega anterior, compare as mudanças
antes de substituir. A integração é: importar `ia`, incluí-lo no laço de routers,
inicializar `app.state.qwen = QwenClient()` no lifespan e registrar o handler de `ErroIA`.
O restante do arquivo entregue mantém os endpoints anteriores e o CORS aberto.

Na raiz, com a venv ativa:

```bash
python -m pip install -r backend/agents/requirements-ia.txt
ollama list
```

Se `qwen3:8b` não aparecer:

```bash
ollama pull qwen3:8b
```

O Ollama precisa estar rodando. Se ele já está ativo como serviço, não abra outro.
Se estiver parado, execute `ollama serve` em um terminal separado.

```bash
python -m uvicorn backend.api.main_router:app --reload
```

Use somente um worker nesta fase local. Abra http://127.0.0.1:8000/docs e procure
`IA • Qwen`. As chamadas podem levar minutos, dependendo de CPU/GPU, contexto e carga.
Não tenho acesso ao Ollama do seu computador: testes incluídos validam contratos e
regras com respostas controladas, não qualidade de inferência ou desempenho real.

## Rotas (POST)

Substitua `1` pelo ID do perfil cadastrado.

| Rota | Função |
| --- | --- |
| `/api/usuarios/1/ia/curriculos` | Currículo adaptado estruturado; salvar é opcional |
| `/api/usuarios/1/ia/perfil` | Resumo profissional, pontos fortes, cargos e termos de busca |
| `/api/usuarios/1/ia/match` | Índice de aderência explicado, 1–100 quando avaliável |
| `/api/usuarios/1/ia/estudos` | Plano de estudo pelo objetivo e histórico de candidaturas |

### 1. Gerar currículo com dados da vaga

```json
{
  "vaga": {
    "titulo": "Estágio em análise de dados",
    "empresa": "Empresa da candidatura",
    "plataforma": "Gupy",
    "descricao": "Buscamos estudante com conhecimentos de Python e SQL. Visualização de dados é desejável."
  },
  "nome": "Currículo — estágio em dados",
  "salvar": true
}
```

Ou use uma vaga já cadastrada:

```json
{"candidatura_id": 1, "salvar": true}
```

Informe exatamente um: `vaga` ou `candidatura_id`. O ID da candidatura é validado
contra o proprietário. Com `salvar:false` (padrão), retorna prévia sem criar registros.
Com `salvar:true`, devolve `curriculo_id` e o currículo aparece no GET de currículos,
inclusive no frontend que já foi entregue. Não vincula automaticamente à candidatura:
essa seleção continua explícita. Não gera PDF.

Retorno: `conteudo`, `auditoria`, `alteracoes`, `lacunas`, `salvo`, `curriculo_id`, `meta`.
A auditoria contém fontes e trechos que sustentam cada destaque. No banco ela fica no
campo JSON `alteracoes`, como um objeto `tipo=auditoria_ia`; não há migração de tabelas.

### Contrato para o futuro construtor PDF

`conteudo` tem `schema_versao: "1.0"`, `idioma`, `titulo`, `pessoa`, `resumo`,
`experiencias`, `formacoes`, `cursos`, `projetos`, `habilidades` e `idiomas`.
`pessoa` contém contatos copiados da base. As listas de experiências/estudos/projetos
contêm dados fixos originais e `destaques` (lista de strings) + `stack` (lista de nomes).
Cargos, empresas, instituições, datas e níveis de idioma não são reescritos pela IA.
O PDF futuro deve renderizar apenas essas seções; auditoria/metadados não são texto
para colocar no documento final. O snapshot preserva o perfil usado naquela geração.

### 2. Analisar perfil

```json
{"objetivo": "Conseguir estágio em análise de dados"}
```

Também aceita `{}` para usar a vaga alvo do perfil. Retorna `analise` com resumo,
pontos fortes, cargos sugeridos, evidências, lacunas e termos de busca. Essas são
sugestões de cargos para explorar, não anúncios de vagas abertas. Não navega na internet.

### 3. Avaliar match

```json
{"candidatura_id": 1}
```

Ou passe `vaga` no mesmo formato da geração. O Qwen extrai requisitos e avalia evidências.
Python calcula o índice: obrigatório pesa 3, desejável 1 e não especificado 2;
atende contribui 100% do peso, parcial 50% e sem evidência 0%.
A média ponderada é arredondada e limitada a 1–100. O piso de 1 atende a faixa solicitada,
mas NÃO significa evidência mínima de competência: a pontuação bruta pode ser zero.
Sem critérios profissionais avaliáveis, `percentual=null` e `avaliavel=false`.

O retorno inclui o trecho da vaga, a evidência, o peso, os pontos e a justificativa por
critério, além de obrigatórios pendentes. É um índice heurístico de aderência, não uma
probabilidade calibrada de contratação, score oficial de ATS ou garantia de aprovação.
A extração de critérios ainda depende do modelo e pode variar ou omitir requisitos.

### 4. Recomendar estudos

```json
{
  "objetivo": "Estágio em dados com Python e SQL",
  "horas_por_semana": 5,
  "semanas": 4,
  "limite_candidaturas": 20
}
```

Objetivo omitido usa a vaga alvo atual. O histórico usa as últimas atualizações de
candidaturas (até 30), preservando contagens reais de status do banco inteiro.
Descrições da amostra são limitadas a 2500 caracteres cada, com aviso de truncamento.
Para chamar um tema de recorrente, exige ao menos duas candidaturas distintas com
citações literais. Sem histórico, usa o objetivo e declara a limitação.
A validação limita horas totais e semanais (distribuição uniforme por intervalo).
Planos trazem atividades práticas, entrega verificável e termos de busca de materiais.
Não inventa links/cursos específicos e não atribui causas a reprovações.

Análises de perfil, match e estudos são retornadas à chamada, sem tabela nova de histórico.
Somente geração com `salvar:true` persiste o resultado. Se quiser guardar análises mais
adiante, podemos criar uma tabela própria e migration.

## Configuração

`agents/.env.example` documenta variáveis; não é carregado automaticamente. Exemplo:

```bash
export QWEN_TIMEOUT=600
export QWEN_NUM_CTX=16384
export QWEN_NUM_PREDICT=4096
python -m uvicorn backend.api.main_router:app --reload
```

Padrões: Ollama `http://127.0.0.1:11434`, modelo `qwen3:8b`, timeout 300s,
contexto 16384, saída 4096 tokens, limite de dados de entrada 24000 caracteres.
O limite de caracteres é conservador, não uma contagem exata de tokens. Schema,
instruções e saída também consomem contexto. Contexto maior consome mais memória.
Para erro 413, reduza a descrição ou `limite_candidaturas`; não aumente o limite de
caracteres sem considerar contexto e memória. Dados do perfil nunca são truncados
silenciosamente. O prompt pode conter menos vagas reduzindo o limite explicitamente.

`think=False`, temperatura 0 e `keep_alive=5m` são usados em cada chamada. Uma inferência
por processo; chamadas concorrentes recebem 503 para evitar disputar a GPU. Não há
fila durável, streaming de progresso ou cancelamento remoto da inferência nesta versão.
A sessão SQLite de leitura é fechada antes de chamar o Qwen, e a gravação usa nova transação.

## Validação e limites

- Entrada Pydantic; saída JSON Schema + Pydantic e regras adicionais.
- Uma tentativa de correção para JSON, referências ou regras inválidas.
- IDs citados precisam existir; trechos precisam constar da fonte.
- Trechos de requisitos precisam existir na descrição da vaga.
- Nomes de habilidades precisam existir no perfil ou nas stacks.
- Não envia nome, contato, endereço nem links pessoais ao modelo nos campos dedicados.
  Textos livres podem conter informações pessoais escritas pelo usuário.
- Dados externos são delimitados como dados; prompts mandam ignorar instruções neles.
  Isso reduz risco de prompt injection, mas não garante resistência completa.
- Citações válidas não provam suporte semântico: o modelo ainda pode interpretar mal ou
  escrever algo não sustentado. `meta.requer_revisao=true`; revise antes de usar o currículo.

Erros HTTP: 404 registro inexistente, 422 entrada/contexto profissional insuficiente,
413 contexto grande, 502 saída inválida/falha do Ollama, 503 serviço/modelo indisponível
ou ocupado, 504 timeout. Erros não salvam currículo parcial nem exibem payload pessoal.

## Testes

```bash
python -m unittest discover -s backend/agents/tests -v
```

Usam TestClient, SQLite temporário e transporte falso do Ollama, sem downloads de
modelos. Cobrem as quatro funções, fórmula de match, snapshots, isolamento entre
usuários, JSON inválido, correção, referências inventadas, limite de horas, timeout,
modelo inexistente, contexto excessivo e ausência de gravação quando há falhas.
Referências técnicas: https://docs.ollama.com/capabilities/structured-outputs
 e https://docs.ollama.com/api/chat
