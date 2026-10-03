"""As quatro funções do Qwen. Persistência só após validar a geração."""
from copy import deepcopy
from datetime import datetime, timezone
from collections import Counter
from sqlalchemy.orm import Session
from ..database.repository import Repository
from .context import (montar_fontes, validar_evidencia, validar_afirmacao, normalizar,
                      carregar_perfil, resolver_vaga, carregar_historico)
from .gen_model import QwenClient, VERSAO_PROMPT
from .schemas import CurriculoPlano, PerfilAnalise, MatchAnalise, EstudosAnalise


class CareerService:
    def __init__(self, engine, qwen: QwenClient):
        self.engine = engine
        self.qwen = qwen

    def _meta(self):
        return {"modelo": self.qwen.model, "versao_prompt": VERSAO_PROMPT,
                "gerado_em": datetime.now(timezone.utc).isoformat(),
                "requer_revisao": True,
                "aviso": "Sugestão de IA local. Referências são verificadas, mas a interpretação e a redação precisam de revisão humana."}

    def gerar_curriculo(self, usuario_id, entrada):
        perfil = carregar_perfil(self.engine, usuario_id)
        fontes = montar_fontes(perfil)
        vaga = resolver_vaga(self.engine, usuario_id, entrada)
        habilidades = {h['nome'] for h in perfil['habilidades']}
        for secao in ('experiencias', 'formacoes', 'cursos', 'projetos'):
            for item in perfil[secao]:
                habilidades.update(h['nome'] for h in item.get('habilidades', []))

        def validar(plano):
            validar_afirmacao(plano.resumo, fontes)
            for secao in ('experiencias', 'formacoes', 'cursos', 'projetos'):
                refs = []
                for item in getattr(plano, secao):
                    if not item.fonte.startswith(secao + ':') or item.fonte not in fontes:
                        raise ValueError(f"Fonte inválida para a seção {secao}.")
                    refs.append(item.fonte)
                    for destaque in item.destaques:
                        validar_afirmacao(destaque, fontes)
                        if any(e.fonte != item.fonte for e in destaque.evidencias):
                            raise ValueError("Destaques de um item devem citar somente esse item.")
                if len(refs) != len(set(refs)):
                    raise ValueError("Não duplique itens do currículo.")
            if len(plano.idiomas) != len(set(plano.idiomas)):
                raise ValueError("Idiomas duplicados.")
            for ref in plano.idiomas:
                if not ref.startswith('idiomas:') or ref not in fontes:
                    raise ValueError("Idioma inexistente no perfil.")
            if any(h not in habilidades for h in plano.habilidades):
                raise ValueError("Selecione somente nomes de habilidades presentes no catálogo fornecido.")

        plano = self.qwen.gerar(CurriculoPlano, """Selecione e ordene informações para um currículo aderente à vaga.
Reescreva o resumo e destaques de forma objetiva, sempre apoiados nas fontes.
Não transforme projetos acadêmicos em emprego. Não invente métricas ou níveis.
Listas sem dados devem ficar vazias. Não precisa selecionar todos os itens.
Em habilidades use os nomes exatos de habilidades_disponiveis. Lacunas são requisitos
sem evidência, não afirmações de incompetência. Não invente critérios secretos da plataforma.
Não escreva dados fixos: o código recuperará cargos, instituições, datas e contatos da base.
Mantenha cada destaque curto e o resultado conciso.""",
            {"fontes": fontes, "habilidades_disponiveis": sorted(habilidades), "vaga": vaga.model_dump()}, validar)
        usuario = perfil['usuario']
        conteudo = {
            "schema_versao": "1.0", "idioma": "pt-BR", "titulo": vaga.titulo,
            "pessoa": {k: usuario.get(k) for k in ('nome_completo', 'email', 'telefone', 'cidade', 'estado', 'pais', 'linkedin_url', 'github_url', 'portfolio_url')},
            "resumo": plano.resumo.texto, "habilidades": list(dict.fromkeys(plano.habilidades)),
        }
        for secao in ('experiencias', 'formacoes', 'cursos', 'projetos'):
            catalogo = {f"{secao}:{i['id']}": i for i in perfil[secao]}
            conteudo[secao] = []
            for item in getattr(plano, secao):
                fonte = catalogo[item.fonte]
                dados = {k: deepcopy(v) for k, v in fonte.items() if k not in ('usuario_id', 'criado_em', 'atualizado_em', 'descricao', 'resultados', 'habilidades')}
                dados['fonte'] = item.fonte
                dados['destaques'] = [d.texto for d in item.destaques]
                dados['stack'] = [h['nome'] for h in fonte.get('habilidades', [])]
                conteudo[secao].append(dados)
        idiomas = {f"idiomas:{i['id']}": i for i in perfil['idiomas']}
        conteudo['idiomas'] = [{k: v for k, v in idiomas[ref].items() if k not in ('usuario_id', 'criado_em', 'atualizado_em')} for ref in plano.idiomas]
        auditoria = plano.model_dump()
        resultado = {"conteudo": conteudo, "auditoria": auditoria, "alteracoes": plano.alteracoes,
                     "lacunas": plano.lacunas, "curriculo_id": None, "salvo": False, "meta": self._meta()}
        if entrada.salvar:
            # A sessão de leitura já foi fechada. Não mantém transação enquanto a IA pensa.
            with Session(self.engine) as session, session.begin():
                cv = Repository(session).criar_curriculo(
                    usuario_id, nome=entrada.nome or f"{vaga.titulo} — {vaga.empresa or 'adaptado'}"[:200],
                    vaga_alvo=vaga.titulo, empresa_alvo=vaga.empresa, plataforma_alvo=vaga.plataforma,
                    descricao_vaga=vaga.descricao, conteudo=conteudo,
                    perfil_snapshot=perfil, alteracoes=[{"tipo": "auditoria_ia", "dados": auditoria}],
                    lacunas=plano.lacunas, modelos_utilizados=[self.qwen.model], versao_prompt=VERSAO_PROMPT,
                )
                resultado['curriculo_id'] = cv.id
            resultado['salvo'] = True
        return resultado

    def analisar_perfil(self, usuario_id, entrada):
        perfil = carregar_perfil(self.engine, usuario_id)
        fontes = montar_fontes(perfil)
        objetivo = entrada.objetivo or perfil['usuario'].get('vaga_alvo_atual')
        def validar(analise):
            validar_afirmacao(analise.resumo, fontes)
            for ponto in analise.pontos_fortes:
                validar_afirmacao(ponto, fontes)
            for cargo in analise.cargos_sugeridos:
                for e in cargo.evidencias:
                    validar_evidencia(e, fontes)
        analise = self.qwen.gerar(PerfilAnalise, """Analise o repertório e sugira famílias de cargos e níveis
para explorar, com evidências concretas e termos de busca. Diferencie habilidade citada
pelo usuário de evidência em projeto/experiência. Considere o objetivo como preferência,
não como habilidade já adquirida. Não afirme que há vagas abertas nem que o candidato
cumpre requisitos de uma vaga não apresentada. Se o perfil for raso, explicite isso nas limitações.""",
            {"fontes": fontes, "objetivo": objetivo}, validar)
        return {"analise": analise.model_dump(), "tipo": "sugestoes_de_cargos_nao_anuncios", "meta": self._meta()}

    def avaliar_match(self, usuario_id, entrada):
        perfil = carregar_perfil(self.engine, usuario_id)
        fontes = montar_fontes(perfil)
        vaga = resolver_vaga(self.engine, usuario_id, entrada)
        def validar(analise):
            vistos = set()
            for criterio in analise.criterios:
                chave = normalizar(criterio.requisito)
                if chave in vistos:
                    raise ValueError("Não duplique um requisito para aumentar seu peso.")
                vistos.add(chave)
                if normalizar(criterio.trecho_vaga) not in normalizar(vaga.descricao):
                    raise ValueError("O trecho_vaga deve existir literalmente na descrição da vaga.")
                for e in criterio.evidencias:
                    validar_evidencia(e, fontes)
        analise = self.qwen.gerar(MatchAnalise, """Extraia os requisitos profissionais da vaga e compare
cada um com fontes do perfil. Não calcule porcentagem; isso será feito em código.
Cobertura: atende=1, parcial=0.5, sem_evidencia=0. Evite requisitos repetidos ou
separar sinônimos. Requisitos compostos devem ser separados somente se independentes.
Marque obrigatório/desejável só se a vaga expressar essa importância; senão use nao_especificada.
Restrições discriminatórias e características pessoais devem ser ignoradas.
Não use ausência de evidência como prova de ausência da habilidade. Um nível ou tempo
mínimo exigido não é atendido só pela menção da tecnologia. Considere requisito como
estágio e formação conforme a evidência, sem inflar senioridade. Não compare somente keywords.
Se não houver requisitos profissionais avaliáveis, retorne criterios=[] e explique.
Na síntese, não invente percentuais de match nem chances de contratação.""",
            {"fontes": fontes, "vaga": vaga.model_dump()}, validar)
        pesos = {'obrigatorio': 3, 'desejavel': 1, 'nao_especificada': 2}
        atendimento = {'atende': 1.0, 'parcial': .5, 'sem_evidencia': 0.0}
        soma = sum(pesos[c.importancia] for c in analise.criterios)
        obtido = sum(pesos[c.importancia] * atendimento[c.atendimento] for c in analise.criterios)
        percentual = max(1, min(100, int(100 * obtido / soma + .5))) if soma else None
        return {"percentual": percentual, "avaliavel": bool(soma),
                "criterios": [{**c.model_dump(), "peso": pesos[c.importancia], "pontos": pesos[c.importancia] * atendimento[c.atendimento]} for c in analise.criterios],
                "sintese": analise.sintese, "limitacoes": analise.limitacoes,
                "metodologia": {"pesos": pesos, "atendimento": atendimento,
                                "pontos_obtidos": obtido, "pontos_possiveis": soma,
                                "formula": "arredondar(100 * pontos_obtidos / pontos_possiveis), limitado a 1–100; sem critérios: null",
                                "interpretacao": "Índice heurístico de evidências de aderência, não chance de contratação. Sem evidência recebe 0 pontos; o piso visual solicitado é 1%."},
                "requisitos_obrigatorios_pendentes": [c.requisito for c in analise.criterios if c.importancia == 'obrigatorio' and c.atendimento != 'atende'],
                "meta": self._meta()}

    def recomendar_estudos(self, usuario_id, entrada):
        perfil = carregar_perfil(self.engine, usuario_id)
        fontes = montar_fontes(perfil)
        objetivo = entrada.objetivo or perfil['usuario'].get('vaga_alvo_atual')
        if not objetivo:
            raise ValueError("Informe um objetivo de estudo ou preencha a vaga alvo atual no perfil.")
        vagas, estatisticas = carregar_historico(self.engine, usuario_id, entrada.limite_candidaturas)
        catalogo = {v['id']: v['descricao'] for v in vagas}
        def validar_ocorrencias(ocorrencias):
            ids = []
            for o in ocorrencias:
                if o.candidatura_id not in catalogo or normalizar(o.trecho) not in normalizar(catalogo[o.candidatura_id]):
                    raise ValueError("Ocorrência precisa citar uma candidatura da amostra e trecho literal de sua descrição.")
                ids.append(o.candidatura_id)
            if len(ids) != len(set(ids)):
                raise ValueError("Conte cada candidatura no máximo uma vez por tema.")
        def validar(analise):
            for tema in analise.temas_recorrentes:
                validar_ocorrencias(tema.ocorrencias)
                if len(tema.ocorrencias) < 2:
                    raise ValueError("Um tema recorrente exige ao menos duas candidaturas distintas.")
            total = sum(e.horas_estimadas for e in analise.plano)
            if total > entrada.semanas * entrada.horas_por_semana:
                raise ValueError("O plano excede a disponibilidade total de horas.")
            ocupacao = Counter()
            for e in analise.plano:
                validar_ocorrencias(e.ocorrencias)
                if e.semana_fim > entrada.semanas:
                    raise ValueError("O plano excede o número de semanas solicitado.")
                # Horas distribuídas igualmente no intervalo: limita também a carga semanal.
                for semana in range(e.semana_inicio, e.semana_fim + 1):
                    ocupacao[semana] += e.horas_estimadas / (e.semana_fim - e.semana_inicio + 1)
            if any(h > entrada.horas_por_semana + 1e-9 for h in ocupacao.values()):
                raise ValueError("A distribuição das atividades excede as horas disponíveis em uma semana.")
        analise = self.qwen.gerar(EstudosAnalise, """Crie um plano de estudo específico ao objetivo e ao perfil.
Use requisitos das candidaturas da amostra como sinais de demanda, nunca como causa de
reprovação. Tema recorrente precisa aparecer em pelo menos duas descrições, citando cada
ocorrência literal. Sem histórico ou sem recorrências, deixe temas_recorrentes=[] e baseie
o plano no objetivo, declarando a limitação. Respeite horas_por_semana e semanas: as horas
de cada atividade serão distribuídas igualmente entre semana_inicio e semana_fim.
Priorize atividades práticas e critérios verificáveis de conclusão, aproveitando projetos
existentes. Não repita conteúdo básico já evidenciado sem justificar revisão. Use termos de
busca para materiais, sem inventar links ou cursos específicos. Não trate objetivo como fato
de carreira já alcançado. Seja conciso e nunca prometa contratação.""",
            {"fontes": fontes, "objetivo": objetivo, "candidaturas": vagas, "estatisticas": estatisticas,
             "horas_por_semana": entrada.horas_por_semana, "semanas": entrada.semanas}, validar)
        plano = analise.model_dump()
        for tema in plano['temas_recorrentes']:
            tema['frequencia_na_amostra'] = len(tema['ocorrencias'])
        return {"analise": plano, "estatisticas_historico": estatisticas,
                "horas_totais_planejadas": sum(e.horas_estimadas for e in analise.plano),
                "horas_disponiveis": entrada.semanas * entrada.horas_por_semana,
                "amostra_com_trechos_truncados": any(v['descricao_truncada'] for v in vagas),
                "meta": self._meta()}
