"""IA local. Rotas síncronas executadas no thread pool do FastAPI.

Nenhuma Session permanece aberta durante a inferência. O cliente é reutilizado
por aplicação e existe um lock por processo; execute um único worker local.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from ...agents.gen_model import QwenClient, ErroIA
from ...agents.schemas import GerarCurriculoInput, EntradaVaga, PerfilInput, EstudosInput
from ...agents.services import CareerService

router = APIRouter(prefix="/usuarios/{usuario_id}/ia", tags=["IA • Qwen"])


def get_qwen(request: Request) -> QwenClient:
    return request.app.state.qwen


Qwen = Annotated[QwenClient, Depends(get_qwen)]


@router.post('/curriculos', summary='Gerar currículo adaptado; salvar é opcional')
def gerar_curriculo(usuario_id: int, entrada: GerarCurriculoInput, request: Request, qwen: Qwen):
    return CareerService(request.app.state.engine, qwen).gerar_curriculo(usuario_id, entrada)


@router.post('/perfil', summary='Analisar perfil e sugerir cargos para explorar')
def analisar_perfil(usuario_id: int, entrada: PerfilInput, request: Request, qwen: Qwen):
    return CareerService(request.app.state.engine, qwen).analisar_perfil(usuario_id, entrada)


@router.post('/match', summary='Estimar aderência à vaga, com critérios e evidências')
def avaliar_match(usuario_id: int, entrada: EntradaVaga, request: Request, qwen: Qwen):
    return CareerService(request.app.state.engine, qwen).avaliar_match(usuario_id, entrada)


@router.post('/estudos', summary='Recomendar estudos pelo objetivo e histórico')
def recomendar_estudos(usuario_id: int, entrada: EstudosInput, request: Request, qwen: Qwen):
    return CareerService(request.app.state.engine, qwen).recomendar_estudos(usuario_id, entrada)
