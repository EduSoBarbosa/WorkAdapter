"""CRUD de idiomas, limitado ao usuário informado."""
from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import IdiomaCreate, IdiomaUpdate, StackInput
from ..serialization import serialize

router = APIRouter(prefix="/usuarios/{usuario_id}/idiomas", tags=["idiomas"])


@router.post("", status_code=201)
def criar(usuario_id: int, dados: IdiomaCreate, repo: Repo):
    item = repo.criar_item_perfil(usuario_id, "idiomas", **dados.model_dump(exclude_unset=True))
    return serialize(item, stack=False)


@router.get("")
def listar(usuario_id: int, repo: Repo, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(item, stack=False) for item in repo.listar_itens_perfil(usuario_id, "idiomas", limite=limite, offset=offset)]


@router.get("/{registro_id}")
def obter(usuario_id: int, registro_id: int, repo: Repo):
    return serialize(repo.obter_item_perfil(usuario_id, "idiomas", registro_id), stack=False)


@router.patch("/{registro_id}")
def atualizar(usuario_id: int, registro_id: int, dados: IdiomaUpdate, repo: Repo):
    item = repo.atualizar_item_perfil(usuario_id, "idiomas", registro_id, **dados.model_dump(exclude_unset=True))
    return serialize(item, stack=False)


@router.delete("/{registro_id}", status_code=204)
def excluir(usuario_id: int, registro_id: int, repo: Repo):
    repo.excluir_item_perfil(usuario_id, "idiomas", registro_id)
    return Response(status_code=204)
