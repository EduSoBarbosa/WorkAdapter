"""Executar na raiz: python -m unittest discover -s backend/agents/tests -v

Testes com respostas controladas: verificam integração/regras, não a qualidade do Qwen.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from ollama import ResponseError
import httpx

from backend.api.main_router import criar_app
from backend.api.routes.ia import get_qwen
from backend.database.repository import Repository
from backend.database.models import Curriculo
from backend.agents.gen_model import (QwenClient, IARespostaInvalida, IAIndisponivel, IATimeout, ContextoExcedido)
from backend.agents.schemas import PerfilAnalise


def evidence():
    return {'fonte': 'projetos:1', 'trecho': 'Análise de dados com Python e SQL.'}


def statement(text='Projeto de análise com Python e SQL.'):
    return {'texto': text, 'evidencias': [evidence()]}


def profile_result():
    return {'resumo': statement(), 'pontos_fortes': [statement()],
            'cargos_sugeridos': [{'cargo':'Estágio em dados', 'nivel_sugerido':'Estágio',
                'justificativa':'Projeto relacionado a dados.', 'evidencias':[evidence()],
                'pontos_a_desenvolver':[], 'termos_busca':['estágio dados']}], 'limitacoes':['Perfil acadêmico.']}


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        value = self.responses.pop(0)
        if callable(value):
            value = value(kwargs)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, dict):
            value = json.dumps(value)
        return SimpleNamespace(done_reason='stop', message=SimpleNamespace(content=value))


class TestAI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = criar_app(Path(self.tmp.name)/'teste.db')
        self.client = TestClient(self.app)
        self.client.__enter__()
        with Session(self.app.state.engine) as s, s.begin():
            r = Repository(s)
            u = r.criar_usuario(nome_completo='Pessoa teste', email='nao-enviar@example.com', vaga_alvo_atual='Dados')
            r.criar_item_perfil(u.id, 'projetos', nome='Análise', descricao='Análise de dados com Python e SQL.')
            h = r.obter_ou_criar_habilidade('Python')
            r.definir_habilidade_usuario(u.id, h.id)
            r.criar_candidatura(u.id, titulo_vaga='Estágio', empresa='Teste', descricao='Python obrigatório. SQL desejável.')
            r.criar_usuario(nome_completo='Outro usuário')
        self.vaga = {'titulo':'Estágio em dados', 'descricao':'Python obrigatório. SQL desejável.', 'empresa':'Teste'}

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.tmp.cleanup()

    def fake(self, *responses):
        transport = FakeTransport(responses)
        qwen = QwenClient(client=transport)
        self.app.dependency_overrides[get_qwen] = lambda: qwen
        return transport

    def test_perfil_e_privacidade(self):
        transport = self.fake(profile_result())
        response = self.client.post('/api/usuarios/1/ia/perfil', json={})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['tipo'], 'sugestoes_de_cargos_nao_anuncios')
        enviado = json.dumps(transport.calls[0]['messages'])
        self.assertNotIn('nao-enviar@example.com', enviado)
        self.assertNotIn('Pessoa teste', enviado)
        self.assertFalse(transport.calls[0]['think'])

    def test_match_formula_e_sem_criterios(self):
        criteria = [dict(requisito='Python', trecho_vaga='Python obrigatório.', importancia='obrigatorio', atendimento='atende', justificativa='Projeto', evidencias=[evidence()]),
                    dict(requisito='SQL', trecho_vaga='SQL desejável.', importancia='desejavel', atendimento='parcial', justificativa='Projeto sem evidência de domínio completo', evidencias=[evidence()])]
        self.fake({'criterios':criteria,'sintese':'Evidências encontradas.','limitacoes':[]})
        res = self.client.post('/api/usuarios/1/ia/match', json={'candidatura_id':1})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['percentual'],88)
        self.fake({'criterios':[],'sintese':'Descrição genérica.','limitacoes':[]})
        self.assertIsNone(self.client.post('/api/usuarios/1/ia/match',json={'vaga':self.vaga}).json()['percentual'])

    def test_curriculo_salvo_snapshot_e_dados_fixos(self):
        def plano(kwargs):
            entrada = kwargs['messages'][1]['content'].split('DADOS_JSON:\n', 1)[1]
            dados, _ = json.JSONDecoder().raw_decode(entrada)
            catalogo = dados['catalogo_evidencias']
            ref = next(k for k, v in catalogo.items()
                       if v['fonte'] == 'projetos:1'
                       and 'Análise de dados com Python e SQL.' in v['trecho'])
            afirmacao = {'texto': 'Projeto de análise com Python e SQL.',
                         'evidencias_ids': [ref]}
            return {'resumo': afirmacao, 'experiencias': [], 'formacoes': [],
                    'cursos': [], 'projetos': [{'fonte': 'projetos:1',
                    'destaques': [afirmacao]}], 'habilidades': ['Python'],
                    'idiomas': [], 'alteracoes': ['Projeto destacado.'], 'lacunas': []}
        self.fake(plano, plano)
        preview = self.client.post('/api/usuarios/1/ia/curriculos',json={'vaga':self.vaga})
        self.assertEqual(preview.status_code,200,preview.text)
        self.assertFalse(preview.json()['salvo'])
        with Session(self.app.state.engine) as s:
            self.assertEqual(s.query(Curriculo).count(),0)
        res = self.client.post('/api/usuarios/1/ia/curriculos',json={'vaga':self.vaga,'salvar':True})
        self.assertEqual(res.status_code,200,res.text)
        self.assertTrue(res.json()['salvo'])
        with Session(self.app.state.engine) as s:
            cv = s.get(Curriculo,res.json()['curriculo_id'])
            self.assertEqual(cv.conteudo['pessoa']['nome_completo'],'Pessoa teste')
            self.assertEqual(cv.conteudo['projetos'][0]['nome'],'Análise')
            self.assertEqual(cv.perfil_snapshot['usuario']['email'],'nao-enviar@example.com')
            self.assertEqual(cv.versao_prompt,'workadapter-curriculo-evidencias-v2')
            evidencia = cv.alteracoes[0]['dados']['resumo']['evidencias'][0]
            self.assertEqual(evidencia['fonte'], 'projetos:1')
            self.assertIn('Análise de dados com Python e SQL.', evidencia['trecho'])
        pdf = self.client.get(f"/api/usuarios/1/curriculos/{res.json()['curriculo_id']}/pdf")
        self.assertEqual(pdf.status_code, 200, pdf.text if pdf.status_code != 200 else '')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_fontes_falsas_e_json_invalido_nao_salvam(self):
        bad=profile_result();bad['resumo']['evidencias'][0]['fonte']='projetos:999'
        self.fake(bad,bad)
        self.assertEqual(self.client.post('/api/usuarios/1/ia/perfil',json={}).status_code,502)
        self.fake('não é JSON','ainda inválido')
        self.assertEqual(self.client.post('/api/usuarios/1/ia/curriculos',json={'vaga':self.vaga,'salvar':True}).status_code,502)
        with Session(self.app.state.engine) as s:
            self.assertEqual(s.query(Curriculo).count(),0)

    def test_correcao_de_json(self):
        transport=self.fake('inválido',profile_result())
        self.assertEqual(self.client.post('/api/usuarios/1/ia/perfil',json={}).status_code,200)
        self.assertEqual(len(transport.calls),2)

    def test_estudos_orcamento_e_historico(self):
        plano={'objetivo':'Dados','temas_recorrentes':[], 'plano':[{
            'tema':'SQL','prioridade':'alta','motivo':'Aprofundar consultas','base':'candidaturas',
            'ocorrencias':[{'candidatura_id':1,'trecho':'SQL desejável.'}],
            'semana_inicio':1,'semana_fim':2,'horas_estimadas':8,
            'atividades':['Praticar JOIN com dados públicos.'],'entrega_pratica':'Notebook de consultas.',
            'criterio_conclusao':'Consultas executam e respondem às perguntas.','termos_busca':['SQL JOIN tutorial']}],
            'limitacoes':['Amostra pequena.']}
        self.fake(plano)
        res=self.client.post('/api/usuarios/1/ia/estudos',json={'horas_por_semana':5,'semanas':2})
        self.assertEqual(res.status_code,200,res.text)
        self.assertEqual(res.json()['estatisticas_historico']['total'],1)
        self.assertEqual(res.json()['horas_totais_planejadas'],8)
        plano['plano'][0]['horas_estimadas']=50
        self.fake(plano,plano)
        self.assertEqual(self.client.post('/api/usuarios/1/ia/estudos',json={'horas_por_semana':5,'semanas':2}).status_code,502)

    def test_validacao_e_propriedade(self):
        self.fake()
        self.assertEqual(self.client.post('/api/usuarios/1/ia/match',json={}).status_code,422)
        self.assertEqual(self.client.post('/api/usuarios/1/ia/match',json={'vaga':self.vaga,'candidatura_id':1}).status_code,422)
        # Outro perfil precisa ter ao menos um dado profissional para passar pela leitura.
        with Session(self.app.state.engine) as s,s.begin():
            Repository(s).atualizar_usuario(2,vaga_alvo_atual='Dados')
        self.assertEqual(self.client.post('/api/usuarios/2/ia/match',json={'candidatura_id':1}).status_code,404)
        self.assertEqual(self.client.post('/api/usuarios/999/ia/perfil',json={}).status_code,404)

    def test_falhas_ollama(self):
        for failure,status in [(ConnectionError(),503),(httpx.ReadTimeout('timeout'),504),(ResponseError('missing',status_code=404),503)]:
            self.fake(failure)
            res=self.client.post('/api/usuarios/1/ia/perfil',json={})
            self.assertEqual(res.status_code,status,res.text)
        qwen=QwenClient(client=FakeTransport([]));qwen.max_input_chars=1
        with self.assertRaises(ContextoExcedido):
            qwen.gerar(PerfilAnalise,'teste',{'x':'excedido'})


if __name__=='__main__':
    unittest.main()
