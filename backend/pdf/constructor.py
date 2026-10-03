"""Currículos A4 com texto selecionável. Não chama IA nem acessa a rede.

    pdf_bytes = gerar_pdf(conteudo, pessoa_fallback=perfil_snapshot['usuario'])
    salvar_pdf(conteudo, 'curriculo.pdf')

Aceita o schema 1.0 do Qwen e o formato manual {"texto": "..."}.
Metadados, auditoria, IDs, fontes e lacunas nunca são impressos no currículo.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
import json
import re
import threading
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

_LOCK = threading.Lock()
NAVY = colors.HexColor('#1B1159')
INK = colors.HexColor('#222839')
GRAY = colors.HexColor('#525D70')
LINE = colors.HexColor('#CDD3DF')


class ConteudoPDFInvalido(ValueError):
    pass


def _fontes():
    # Fontes incluídas no ReportLab: dispensa fontes instaladas no sistema.
    with _LOCK:
        if 'WorkAdapter' not in pdfmetrics.getRegisteredFontNames():
            pasta = Path(reportlab.__file__).parent/'fonts'
            for nome, arquivo in [('WorkAdapter','Vera.ttf'), ('WorkAdapterBold','VeraBd.ttf')]:
                pdfmetrics.registerFont(TTFont(nome, str(pasta/arquivo)))
            pdfmetrics.registerFontFamily('WorkAdapter', normal='WorkAdapter', bold='WorkAdapterBold', italic='WorkAdapter', boldItalic='WorkAdapterBold')


def _texto(value):
    if value is None:
        return ''
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ConteudoPDFInvalido('Um campo textual do currículo possui formato inválido.')
    text = str(value).strip()
    text = text.replace('\u2013','-').replace('\u2014','-').replace('\u2011','-')
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)


def _html(value):
    return escape(_texto(value)).replace('\n','<br/>')


def _data(value):
    text = _texto(value)
    match = re.fullmatch(r'(\d{4})-(\d{2})(?:-\d{2})?', text)
    return f'{match[2]}/{match[1]}' if match else text


def _periodo(item):
    inicio = _data(item.get('data_inicio'))
    fim = 'Atual' if item.get('atual') else _data(item.get('data_fim') or item.get('data_conclusao'))
    if item.get('status') == 'cursando' and fim:
        fim = f'Previsão: {fim}'
    return ' - '.join(v for v in (inicio,fim) if v)


def _link(value, label=None):
    text = _texto(value)
    if not text:
        return ''
    try:
        parsed = urlsplit(text)
        valido = parsed.scheme.lower() in ('http','https') and bool(parsed.netloc)
    except ValueError:
        valido = False
    if not valido:
        return _html(label or text)  # javascript/file/data não se tornam links.
    return f'<link href={quoteattr(text)} color="#1B1159">{_html(label or text)}</link>'


def _validar(conteudo):
    if not isinstance(conteudo, dict):
        raise ConteudoPDFInvalido('O conteúdo do currículo deve ser um objeto JSON.')
    try:
        tamanho = len(json.dumps(conteudo, ensure_ascii=False))
    except (ValueError, TypeError) as exc:
        raise ConteudoPDFInvalido('Conteúdo não serializável em JSON.') from exc
    if tamanho > 150_000:
        raise ConteudoPDFInvalido('O currículo excede o limite de 150 mil caracteres.')
    if 'texto' in conteudo:
        if not isinstance(conteudo['texto'], str) or not conteudo['texto'].strip():
            raise ConteudoPDFInvalido('O texto do currículo está vazio ou inválido.')
        if set(conteudo) != {'texto'}:
            raise ConteudoPDFInvalido('Não misture texto livre e seções estruturadas. Use apenas texto ou schema_versao 1.0.')
        return 'manual'
    if conteudo.get('schema_versao') != '1.0':
        raise ConteudoPDFInvalido('Formato não suportado. Use o currículo estruturado 1.0 do Qwen ou {"texto": "..."}.')
    if not isinstance(conteudo.get('pessoa'), dict):
        raise ConteudoPDFInvalido('O currículo estruturado precisa de pessoa como objeto.')
    if not _texto(conteudo['pessoa'].get('nome_completo')):
        raise ConteudoPDFInvalido('Informe o nome completo no currículo.')
    for secao in ('experiencias','formacoes','cursos','projetos','idiomas','habilidades'):
        valores = conteudo.get(secao, [])
        if not isinstance(valores, list) or len(valores) > 100:
            raise ConteudoPDFInvalido(f'{secao} deve ser uma lista com até 100 itens.')
        for item in valores:
            if secao == 'habilidades':
                if not isinstance(item,str):
                    raise ConteudoPDFInvalido('Habilidades devem ser nomes em texto.')
                continue
            if not isinstance(item, dict):
                raise ConteudoPDFInvalido(f'Item inválido na seção {secao}.')
            for campo in ('destaques','stack'):
                if campo in item and (not isinstance(item[campo],list) or any(not isinstance(v,str) for v in item[campo])):
                    raise ConteudoPDFInvalido(f'{campo} deve ser uma lista de textos.')
    return 'estruturado'


def gerar_pdf(conteudo: dict, *, pessoa_fallback: dict | None = None) -> bytes:
    """Retorna o PDF em bytes; não modifica o objeto recebido ou o banco.

    pessoa_fallback é usada somente para título/metadados do formato manual;
    o texto manual é renderizado como foi escrito, sem duplicar cabeçalho.
    """
    conteudo = deepcopy(conteudo)
    modo = _validar(conteudo)
    _fontes()
    pessoa = conteudo.get('pessoa', {}) if modo == 'estruturado' else (pessoa_fallback or {})
    nome = _texto(pessoa.get('nome_completo')) or 'Currículo'
    base = dict(fontName='WorkAdapter', textColor=INK, fontSize=9.5, leading=14,
                alignment=TA_LEFT, splitLongWords=True, allowWidows=0, allowOrphans=0)
    styles = {
        'body': ParagraphStyle('body', **base, spaceAfter=6),
        'bullet': ParagraphStyle('bullet', **base, leftIndent=10, firstLineIndent=-8, spaceAfter=4),
        'name': ParagraphStyle('name', fontName='WorkAdapterBold', fontSize=23, leading=28, textColor=NAVY, spaceAfter=5, keepWithNext=True, splitLongWords=True),
        'title': ParagraphStyle('title', fontName='WorkAdapter', fontSize=11, leading=16, textColor=GRAY, spaceAfter=7, keepWithNext=True, splitLongWords=True),
        'small': ParagraphStyle('small', fontName='WorkAdapter', fontSize=8.3, leading=12, textColor=GRAY, spaceAfter=5, splitLongWords=True),
        'section': ParagraphStyle('section', fontName='WorkAdapterBold', fontSize=10.5, leading=15, textColor=NAVY, spaceBefore=11, spaceAfter=6, keepWithNext=True),
        'item': ParagraphStyle('item', fontName='WorkAdapterBold', fontSize=10, leading=14, textColor=INK, spaceBefore=5, spaceAfter=3, keepWithNext=True, splitLongWords=True),
    }
    story = []
    def add(value, style='body', raw=False):
        if value is not None and str(value).strip():
            story.append(Paragraph(value if raw else _html(value), styles[style]))
    def heading(label):
        add(label, 'section')
    def details(item):
        for texto in item.get('destaques', []):
            add('- '+texto, 'bullet')
        if item.get('stack'):
            add('Tecnologias: '+', '.join(item['stack']), 'small')

    if modo == 'manual':
        # Cada bloco quebra naturalmente entre páginas. Nada é reinterpretado por IA.
        for bloco in re.split(r'\n\s*\n',conteudo['texto']):
            add(bloco)
    else:
        add(nome,'name')
        add(conteudo.get('titulo'),'title')
        local = ', '.join(_texto(pessoa.get(k)) for k in ('cidade','estado','pais') if pessoa.get(k))
        contato = ' | '.join(_texto(v) for v in (local,pessoa.get('email'),pessoa.get('telefone')) if v)
        add(contato,'small')
        links = [_link(pessoa[k]) for k in ('linkedin_url','github_url','portfolio_url') if pessoa.get(k)]
        if links:
            add('<br/>'.join(links),'small',raw=True)
        story.extend([Spacer(1,4),HRFlowable(width='100%',thickness=.7,color=LINE),Spacer(1,4)])
        if conteudo.get('resumo'):
            heading('RESUMO PROFISSIONAL');add(conteudo['resumo'])
        if conteudo.get('habilidades'):
            heading('HABILIDADES');add(' | '.join(conteudo['habilidades']))
        for secao, label in [('experiencias','EXPERIÊNCIA PROFISSIONAL'),('projetos','PROJETOS'),('formacoes','FORMAÇÃO ACADÊMICA'),('cursos','CURSOS E CERTIFICAÇÕES')]:
            if not conteudo.get(secao):
                continue
            heading(label)
            for item in conteudo[secao]:
                titulo = item.get('cargo') or item.get('curso') or item.get('nome') or label.capitalize()
                add(titulo,'item')
                meta = [item.get('empresa') or item.get('instituicao'),item.get('nivel') or item.get('papel_desempenhado'),_periodo(item)]
                if item.get('carga_horaria') is not None:
                    meta.append(f"{_texto(item['carga_horaria'])} horas")
                estados = {'cursando':'Em andamento','concluido':'Concluído','interrompido':'Interrompido'}
                if item.get('status') in estados:
                    meta.append(estados[item['status']])
                add(' | '.join(_texto(v) for v in meta if v),'small')
                details(item)
                for campo, rotulo in [('repositorio_url','Repositório'),('demonstracao_url','Demonstração'),('certificado_url','Certificado')]:
                    if item.get(campo):
                        add(_html(rotulo)+': '+_link(item[campo]),'small',raw=True)
                story.append(Spacer(1,4))
        if conteudo.get('idiomas'):
            heading('IDIOMAS')
            for item in conteudo['idiomas']:
                campos = [item.get('idioma'),item.get('nivel'),item.get('certificacao')]
                if item.get('pontuacao_certificacao'):
                    campos.append('Pontuação: '+_texto(item['pontuacao_certificacao']))
                add(' | '.join(_texto(v) for v in campos if v))
    if not story:
        raise ConteudoPDFInvalido('Não há conteúdo para exportar.')
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=18*mm, bottomMargin=19*mm,
                            title=f'Currículo - {nome}', author=nome,
                            pageCompression=1)
    def pagina(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.4)
        canvas.line(20*mm,15*mm,A4[0]-20*mm,15*mm)
        canvas.setFont('WorkAdapter',7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(A4[0]-20*mm,10.5*mm,f'Página {document.page}')
        canvas.restoreState()
    doc.build(story,onFirstPage=pagina,onLaterPages=pagina)
    return buffer.getvalue()


def salvar_pdf(conteudo: dict, destino: str | Path, *, pessoa_fallback: dict | None = None) -> Path:
    """Helper local explícito. A rota HTTP não aceita caminhos de arquivos."""
    dados = gerar_pdf(conteudo,pessoa_fallback=pessoa_fallback)
    destino = Path(destino)
    destino.parent.mkdir(parents=True,exist_ok=True)
    destino.write_bytes(dados)
    return destino
