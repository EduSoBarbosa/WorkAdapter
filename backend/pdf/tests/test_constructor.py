"""python -m unittest discover -s backend/pdf/tests -v
Instale pypdf para executar estes testes de extração; não é dependência de produção.
"""
import unittest
import tempfile
from pathlib import Path
from io import BytesIO
from copy import deepcopy
from pypdf import PdfReader
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.pdf.constructor import gerar_pdf, ConteudoPDFInvalido
from backend.api.main_router import criar_app
from backend.database.repository import Repository


def exemplo():
    return {'schema_versao':'1.0','idioma':'pt-BR','titulo':'Analista de dados júnior',
      'pessoa':{'nome_completo':'Marina Oliveira','cidade':'São Paulo','estado':'SP',
        'email':'marina@example.com','telefone':'(11) 90000-0000','github_url':'https://github.com/exemplo'},
      'resumo':'Profissional com experiência em análise de dados e automação de relatórios. Atuação com Python, SQL e visualização para comunicar resultados de forma clara.',
      'habilidades':['Python','SQL','Pandas','Power BI'],
      'experiencias':[{'cargo':'Estagiária de dados','empresa':'Empresa Exemplo','data_inicio':'2025-01-01','data_fim':'2026-06-01','destaques':['Preparação e validação de dados para relatórios operacionais.','Criação de consultas SQL e painéis para acompanhamento de indicadores.'],'stack':['Python','SQL']}],
      'projetos':[{'nome':'Análise de mobilidade urbana','destaques':['Investigação de padrões de deslocamento com dados públicos e visualizações exploratórias.'],'stack':['Pandas','Matplotlib'],'repositorio_url':'https://example.com/projeto'}],
      'formacoes':[{'curso':'Desenvolvimento de Software Multiplataforma','instituicao':'Instituição Exemplo','nivel':'Tecnólogo','status':'cursando','data_inicio':'2024-08-01','data_fim':'2027-08-01','destaques':[],'stack':[]}],
      'cursos':[{'nome':'Análise de dados com Python','instituicao':'Instituição Exemplo','carga_horaria':40,'status':'concluido','destaques':[],'stack':['Pandas']}],
      'idiomas':[{'idioma':'Inglês','nivel':'Intermediário'}],
      'auditoria':'NAO_IMPRIMIR_AUDITORIA', 'lacunas':['NAO_IMPRIMIR_LACUNAS']}


class PDFTests(unittest.TestCase):
    def test_estrutura_acentos_e_imutabilidade(self):
        payload=exemplo(); original=deepcopy(payload)
        pdf=gerar_pdf(payload)
        reader=PdfReader(BytesIO(pdf));texto='\n'.join(p.extract_text() for p in reader.pages)
        self.assertEqual(len(reader.pages),1)
        self.assertIn('Marina Oliveira',texto);self.assertIn('São Paulo',texto)
        self.assertIn('FORMAÇÃO ACADÊMICA',texto);self.assertNotIn('NAO_IMPRIMIR',texto)
        self.assertEqual(payload,original)
        self.assertTrue(any(p.get('/Annots') for p in reader.pages))

    def test_multiplas_paginas_e_markup(self):
        payload=exemplo()
        payload['projetos']=[{'nome':f'Projeto {i} <teste> & dados','destaques':['Texto longo de análise e validação. '*30],'stack':[]} for i in range(15)]
        reader=PdfReader(BytesIO(gerar_pdf(payload)))
        self.assertGreater(len(reader.pages),1)
        self.assertIn('Projeto 14 <teste> & dados',reader.pages[-1].extract_text()+'\n'+reader.pages[-2].extract_text())
        for i,p in enumerate(reader.pages,1):self.assertIn(f'Página {i}',p.extract_text())

    def test_manual_e_links(self):
        pdf=gerar_pdf({'texto':'Nome de teste\n\nAnálise de dados <b>literal</b> & SQL.'})
        self.assertIn('<b>literal</b>',PdfReader(BytesIO(pdf)).pages[0].extract_text())
        payload=exemplo();payload['pessoa']['github_url']='javascript:alert(1)';payload['projetos']=[]
        reader=PdfReader(BytesIO(gerar_pdf(payload)))
        self.assertFalse(any(p.get('/Annots') for p in reader.pages))

    def test_invalidos(self):
        for item in ({},{'texto':''},{'texto':'x','resumo':'y'},{'schema_versao':'2.0'}, {'texto':'x'*150001}):
            with self.assertRaises(ConteudoPDFInvalido):gerar_pdf(item)

    def test_rota_e_propriedade(self):
        with tempfile.TemporaryDirectory() as d:
            app=criar_app(Path(d)/'db.sqlite')
            with TestClient(app) as c:
                with Session(app.state.engine) as s,s.begin():
                    r=Repository(s);u=r.criar_usuario(nome_completo='Pessoa');r.criar_usuario(nome_completo='Outro')
                    cv=r.criar_curriculo(u.id,nome='Dados / São Paulo',conteudo=exemplo());cid=cv.id
                res=c.get(f'/api/usuarios/1/curriculos/{cid}/pdf')
                self.assertEqual(res.status_code,200,res.text if res.status_code!=200 else '')
                self.assertTrue(res.content.startswith(b'%PDF'))
                self.assertEqual(res.headers['content-type'],'application/pdf')
                self.assertIn('attachment;',res.headers['content-disposition'])
                self.assertIn('inline;',c.get(f'/api/usuarios/1/curriculos/{cid}/pdf?inline=true').headers['content-disposition'])
                self.assertEqual(c.get(f'/api/usuarios/2/curriculos/{cid}/pdf').status_code,404)
                self.assertEqual(c.get('/api/usuarios/1/curriculos/999/pdf').status_code,404)
                with Session(app.state.engine) as s:
                    self.assertIsNone(Repository(s).obter_curriculo(1,cid).arquivo_url)


if __name__=='__main__':unittest.main()
