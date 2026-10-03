"""CRUD de projetos, limitado ao usuário informado."""
from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import ProjetoCreate, ProjetoUpdate, StackInput
from ..serialization import serialize

router = APIRouter(prefix="/usuarios/{usuario_id}/projetos", tags=["projetos"])


@router.post("", status_code=201)
def criar(usuario_id: int, dados: ProjetoCreate, repo: Repo):
    item = repo.criar_item_perfil(usuario_id, "projetos", **dados.model_dump(exclude_unset=True))
    return serialize(item, stack=True)


@router.get("")
def listar(usuario_id: int, repo: Repo, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(item, stack=True) for item in repo.listar_itens_perfil(usuario_id, "projetos", limite=limite, offset=offset)]


@router.get("/{registro_id}")
def obter(usuario_id: int, registro_id: int, repo: Repo):
    return serialize(repo.obter_item_perfil(usuario_id, "projetos", registro_id), stack=True)


@router.patch("/{registro_id}")
def atualizar(usuario_id: int, registro_id: int, dados: ProjetoUpdate, repo: Repo):
    item = repo.atualizar_item_perfil(usuario_id, "projetos", registro_id, **dados.model_dump(exclude_unset=True))
    return serialize(item, stack=True)


@router.delete("/{registro_id}", status_code=204)
def excluir(usuario_id: int, registro_id: int, repo: Repo):
    repo.excluir_item_perfil(usuario_id, "projetos", registro_id)
    return Response(status_code=204)


@router.put("/{registro_id}/habilidades")
def definir_stack(usuario_id: int, registro_id: int, dados: StackInput, repo: Repo):
    """Substitui a stack completa; uma lista vazia remove todos os vínculos."""
    item = repo.definir_stack(usuario_id, "projetos", registro_id, dados.habilidades_ids)
    return serialize(item, stack=True)
