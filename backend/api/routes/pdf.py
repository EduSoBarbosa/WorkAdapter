"""Download sob demanda: não sobrescreve currículo nem grava caminho no banco."""
from copy import deepcopy
import re
from urllib.parse import quote
from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session
from ...database.repository import Repository
from ...pdf.constructor import gerar_pdf

router = APIRouter(prefix='/usuarios/{usuario_id}/curriculos',tags=['PDF'])


@router.get('/{curriculo_id}/pdf', summary='Baixar PDF de um currículo salvo',
            responses={200:{'content':{'application/pdf':{}},'description':'Currículo PDF'}})
def baixar_pdf(usuario_id: int, curriculo_id: int, request: Request, inline: bool = False):
    with Session(request.app.state.engine) as session:
        cv = Repository(session).obter_curriculo(usuario_id,curriculo_id)
        conteudo = deepcopy(cv.conteudo)
        pessoa = deepcopy((cv.perfil_snapshot or {}).get('usuario') or {})
        nome = cv.nome
    # Fecha a sessão antes da renderização; nome do download nunca vira caminho.
    dados = gerar_pdf(conteudo,pessoa_fallback=pessoa)
    nome_seguro = re.sub(r'[^\w .-]', '', nome, flags=re.UNICODE).strip(' .')[:100] or 'curriculo'
    disposition = 'inline' if inline else 'attachment'
    return Response(content=dados, media_type='application/pdf',headers={
        'Content-Disposition': f'{disposition}; filename="curriculo-{curriculo_id}.pdf"; filename*=UTF-8\'\'{quote(nome_seguro+".pdf")}',
        'Cache-Control':'no-store',
        'X-Content-Type-Options':'nosniff',
    })
