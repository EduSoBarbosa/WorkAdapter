"""CRUD de experiencias, limitado ao usuário informado."""
from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import ExperienciaCreate, ExperienciaUpdate, StackInput
from ..serialization import serialize

router = APIRouter(prefix="/usuarios/{usuario_id}/experiencias", tags=["experiencias"])


@router.post("", status_code=201)
def criar(usuario_id: int, dados: ExperienciaCreate, repo: Repo):
    item = repo.criar_item_perfil(usuario_id, "experiencias", **dados.model_dump(exclude_unset=True))
    return serialize(item, stack=True)


@router.get("")
def listar(usuario_id: int, repo: Repo, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(item, stack=True) for item in repo.listar_itens_perfil(usuario_id, "experiencias", limite=limite, offset=offset)]


@router.get("/{registro_id}")
def obter(usuario_id: int, registro_id: int, repo: Repo):
    return serialize(repo.obter_item_perfil(usuario_id, "experiencias", registro_id), stack=True)


@router.patch("/{registro_id}")
def atualizar(usuario_id: int, registro_id: int, dados: ExperienciaUpdate, repo: Repo):
    item = repo.atualizar_item_perfil(usuario_id, "experiencias", registro_id, **dados.model_dump(exclude_unset=True))
    return serialize(item, stack=True)


@router.delete("/{registro_id}", status_code=204)
def excluir(usuario_id: int, registro_id: int, repo: Repo):
    repo.excluir_item_perfil(usuario_id, "experiencias", registro_id)
    return Response(status_code=204)


@router.put("/{registro_id}/habilidades")
def definir_stack(usuario_id: int, registro_id: int, dados: StackInput, repo: Repo):
    """Substitui a stack completa; uma lista vazia remove todos os vínculos."""
    item = repo.definir_stack(usuario_id, "experiencias", registro_id, dados.habilidades_ids)
    return serialize(item, stack=True)
