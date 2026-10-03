from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import UsuarioCreate, UsuarioUpdate
from ..serialization import serialize

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", status_code=201)
def criar(dados: UsuarioCreate, repo: Repo):
    return serialize(repo.criar_usuario(**dados.model_dump(exclude_unset=True)))


@router.get("")
def listar(repo: Repo, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(u) for u in repo.listar_usuarios(limite=limite, offset=offset)]


@router.get("/{usuario_id}")
def obter(usuario_id: int, repo: Repo):
    return serialize(repo.obter_usuario(usuario_id))


@router.get("/{usuario_id}/perfil")
def perfil_completo(usuario_id: int, repo: Repo):
    return repo.obter_perfil_completo(usuario_id)


@router.patch("/{usuario_id}")
def atualizar(usuario_id: int, dados: UsuarioUpdate, repo: Repo):
    return serialize(repo.atualizar_usuario(usuario_id, **dados.model_dump(exclude_unset=True)))


@router.delete("/{usuario_id}", status_code=204)
def excluir(usuario_id: int, repo: Repo):
    """Exclui o usuário e todos os seus dados, incluindo candidaturas e currículos."""
    repo.excluir_usuario(usuario_id)
    return Response(status_code=204)
