from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import CandidaturaCreate, CandidaturaUpdate
from ..serialization import serialize
from ...database.models import StatusCandidatura

router = APIRouter(prefix="/usuarios/{usuario_id}/candidaturas", tags=["candidaturas"])


@router.post("", status_code=201)
def criar(usuario_id: int, dados: CandidaturaCreate, repo: Repo):
    return serialize(repo.criar_candidatura(usuario_id, **dados.model_dump(exclude_unset=True)))


@router.get("")
def listar(usuario_id: int, repo: Repo, status: StatusCandidatura | None = None, plataforma: str | None = None, busca: str | None = None, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(c) for c in repo.listar_candidaturas(usuario_id, status=status, plataforma=plataforma, busca=busca, limite=limite, offset=offset)]


@router.get("/{candidatura_id}")
def obter(usuario_id: int, candidatura_id: int, repo: Repo):
    return serialize(repo.obter_candidatura(usuario_id, candidatura_id))


@router.patch("/{candidatura_id}")
def atualizar(usuario_id: int, candidatura_id: int, dados: CandidaturaUpdate, repo: Repo):
    """Para mudar status/etapa, use POST no endpoint de movimentações."""
    return serialize(repo.atualizar_candidatura(usuario_id, candidatura_id, **dados.model_dump(exclude_unset=True)))


@router.delete("/{candidatura_id}", status_code=204)
def excluir(usuario_id: int, candidatura_id: int, repo: Repo):
    repo.excluir_candidatura(usuario_id, candidatura_id)
    return Response(status_code=204)
