# WorkAdapter — frontend completo com IA e PDF

Frontend completo atualizado para o backend entregue nesta conversa, incluindo agents, pdf e suas rotas. Este ZIP não contém nem substitui o backend.

## Atualizar sem perder configurações

1. Extraia o ZIP primeiro em uma pasta separada.
2. Faça uma cópia do seu frontend atual.
3. Copie os arquivos de frontend/src deste pacote para frontend/src do projeto, mesclando pastas e substituindo os arquivos correspondentes. Não substitua a pasta inteira do projeto.
4. Preserve seu package.json, package-lock.json, vite.config.js, .env e configuração de lint. Nenhuma biblioteca adicional foi introduzida: usamos React, React DOM, CSS e fetch.
5. O pacote inclui também index.html, package.json, lockfile e vite.config.js para reconstrução do zero, se necessário.

No frontend existente:

```bash
cd frontend
npm run dev
```

Para instalação do zero, dentro da pasta frontend extraída:

```bash
npm ci
npm run dev
```

No terminal do backend, com a venv ativa e estando na raiz WorkAdapter:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api.main_router:app --reload
```

O Ollama precisa estar rodando com qwen3:8b disponível para IA. Confira com ollama list. Se já estiver ativo como serviço, não inicie outra instância. CRUD e PDF não executam inferência.

## Endereço da API

O padrão é http://127.0.0.1:8000/api. Para alterar, configure frontend/.env:

```text
VITE_API_URL=http://127.0.0.1:8000/api
```

Reinicie o Vite após alterar. Não inclua segredos em variáveis VITE_, pois ficam visíveis ao navegador.

## Novos fluxos

- Assistente IA: geração de currículo, análise de perfil, match e plano de estudos.
- Currículo e match aceitam uma nova vaga ou candidatura salva com descrição. Empresa e plataforma são opcionais; título e descrição são obrigatórios para uma nova vaga.
- Gerar e salvar currículo cria uma nova versão no banco e mostra conteúdo, adaptações e lacunas. Não sobrescreve anteriores nem vincula automaticamente a candidaturas. Revise antes de usar.
- Perfil mostra resumo, pontos fortes, cargos sugeridos, termos de busca e evidências. Não busca anúncios de vagas em tempo real.
- Match apresenta aderência, critérios, evidências, obrigatórios pendentes e limitações. Não é probabilidade de contratação ou pontuação oficial de ATS. Se faltarem critérios, nenhum percentual é inventado.
- Estudos permite objetivo, 1–40 horas por semana, 1–12 semanas e até 30 candidaturas. Mostra atividades, entregas, critérios de conclusão e temas recorrentes quando presentes.
- Currículos possui visualização legível e botões Visualizar PDF / Baixar PDF. O PDF vem da API e corresponde à versão salva.
- Edição de currículo estruturado: resumo e destaques em campos comuns, sem editar JSON. Para corrigir datas, instituições e contatos, atualize o perfil e gere outra versão. Currículos manuais continuam editáveis como texto; formatos antigos desconhecidos mantêm o editor JSON.
- Currículos vinculados a candidaturas mantêm a proteção: editar cria uma nova versão. Escolha a associação em Candidaturas > Editar > Currículo usado.

## Espera e persistência

Uma inferência por vez na interface. O contador informa tempo decorrido, não tempo restante. Pode levar minutos. Você pode navegar pelas abas e voltar enquanto a IA trabalha; trocar perfil fica desabilitado durante a inferência.

Não recarregue ou feche a página durante a geração: o backend pode continuar e salvar mesmo que o navegador perca a conexão. Confira Currículos antes de repetir uma solicitação que falhou por conexão.

Perfil, match e estudos ficam em memória nesta sessão: navegar entre abas preserva os resultados; recarregar ou trocar perfil os limpa. Currículos gerados ficam salvos no banco. Uma análise nova mantém o resultado anterior durante a espera ou em caso de falha; contexto e horário identificam o resultado exibido.

Erros da API e de conexão aparecem na tela. Se a abertura de nova aba para PDF for bloqueada, use Baixar PDF ou permita a abertura. O frontend chama o FastAPI, não o Ollama diretamente.

## Arquivos atualizados

- src/App.jsx: navegação e sessão de IA.
- src/pages/Assistant.jsx: quatro formulários e resultados.
- src/pages/Resumes.jsx: editor, visualização e PDF.
- src/components/ResumeDocument.jsx: documento legível, edição estruturada e ações PDF.
- src/services/api.js: download binário e erros.
- src/index.css: novas telas responsivas.

As páginas de perfil, visão geral e candidaturas também estão no pacote completo.

## Visual e validação

Paleta preservada: #FFF000, #00FF79, #00B7FF, #1B1159, #101126. Painéis glass, rótulos persistentes, foco visível, feedback e layout responsivo. Google Fonts usa fallback local sem internet; não recebe o conteúdo dos currículos.

npm run build concluído. Testes em Chromium com API/SQLite temporários verificaram geração/salvamento, navegação em processamento, PDF real, perfil, match com candidatura, estudos, edição estruturada, erro 503 preservando resultado anterior, troca de perfil e ausência de overflow horizontal a 390px. Visual conferido em desktop e celular.

As respostas Qwen dos testes foram controladas: validam integração, não a qualidade/desempenho do modelo real. A interface entregue usa as rotas reais, sem dados simulados. O ZIP não contém banco, node_modules nem dist.
