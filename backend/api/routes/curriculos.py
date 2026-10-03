from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import CurriculoCreate, CurriculoUpdate
from ..serialization import serialize

router = APIRouter(prefix="/usuarios/{usuario_id}/curriculos", tags=["curriculos"])


@router.post("", status_code=201)
def criar(usuario_id: int, dados: CurriculoCreate, repo: Repo):
    """Salva conteúdo pronto. A geração por IA será integrada separadamente."""
    return serialize(repo.criar_curriculo(usuario_id, **dados.model_dump(exclude_unset=True)))


@router.get("")
def listar(usuario_id: int, repo: Repo, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(c) for c in repo.listar_curriculos(usuario_id, limite=limite, offset=offset)]


@router.get("/{curriculo_id}")
def obter(usuario_id: int, curriculo_id: int, repo: Repo):
    return serialize(repo.obter_curriculo(usuario_id, curriculo_id))


@router.patch("/{curriculo_id}")
def atualizar(usuario_id: int, curriculo_id: int, dados: CurriculoUpdate, repo: Repo):
    return serialize(repo.atualizar_curriculo(usuario_id, curriculo_id, **dados.model_dump(exclude_unset=True)))


@router.post("/{curriculo_id}/versoes", status_code=201)
def nova_versao(usuario_id: int, curriculo_id: int, dados: CurriculoUpdate, repo: Repo):
    return serialize(repo.criar_versao_curriculo(usuario_id, curriculo_id, **dados.model_dump(exclude_unset=True)))


@router.delete("/{curriculo_id}", status_code=204)
def excluir(usuario_id: int, curriculo_id: int, repo: Repo):
    repo.excluir_curriculo(usuario_id, curriculo_id)
    return Response(status_code=204)
