from fastapi import APIRouter
from ..dependencies import Repo
from ..schemas import MovimentacaoCreate
from ..serialization import serialize

router = APIRouter(prefix="/usuarios/{usuario_id}/candidaturas/{candidatura_id}/movimentacoes", tags=["movimentacoes"])


@router.get("")
def listar(usuario_id: int, candidatura_id: int, repo: Repo):
    return [serialize(m) for m in repo.listar_movimentacoes(usuario_id, candidatura_id)]


@router.post("", status_code=201)
def adicionar(usuario_id: int, candidatura_id: int, dados: MovimentacaoCreate, repo: Repo):
    """Acrescenta evento e atualiza status/etapa se for a movimentação mais recente."""
    return serialize(repo.adicionar_movimentacao(usuario_id, candidatura_id, **dados.model_dump(exclude_unset=True)))
