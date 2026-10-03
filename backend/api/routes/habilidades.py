from fastapi import APIRouter, Query, Response
from ..dependencies import Repo
from ..schemas import HabilidadeCreate, HabilidadeUpdate, HabilidadeUsuarioInput
from ..serialization import serialize

router = APIRouter(tags=["habilidades"])


@router.post("/habilidades", status_code=200)
def obter_ou_criar(dados: HabilidadeCreate, repo: Repo):
    """Reutiliza a habilidade caso seu nome já esteja no catálogo."""
    return serialize(repo.obter_ou_criar_habilidade(**dados.model_dump()))


@router.get("/habilidades")
def listar(repo: Repo, busca: str | None = None, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return [serialize(h) for h in repo.listar_habilidades(busca=busca, limite=limite, offset=offset)]


@router.get("/habilidades/{habilidade_id}")
def obter(habilidade_id: int, repo: Repo):
    return serialize(repo.obter_habilidade(habilidade_id))


@router.patch("/habilidades/{habilidade_id}")
def atualizar(habilidade_id: int, dados: HabilidadeUpdate, repo: Repo):
    return serialize(repo.atualizar_habilidade(habilidade_id, **dados.model_dump(exclude_unset=True)))


@router.delete("/habilidades/{habilidade_id}", status_code=204)
def excluir(habilidade_id: int, repo: Repo):
    repo.excluir_habilidade(habilidade_id)
    return Response(status_code=204)


@router.get("/usuarios/{usuario_id}/habilidades")
def listar_do_usuario(usuario_id: int, repo: Repo):
    return [{**serialize(v), "habilidade": serialize(v.habilidade)} for v in repo.listar_habilidades_usuario(usuario_id)]


@router.put("/usuarios/{usuario_id}/habilidades/{habilidade_id}")
def vincular(usuario_id: int, habilidade_id: int, dados: HabilidadeUsuarioInput, repo: Repo):
    v = repo.definir_habilidade_usuario(usuario_id, habilidade_id, dados.nivel)
    return {**serialize(v), "habilidade": serialize(v.habilidade)}


@router.delete("/usuarios/{usuario_id}/habilidades/{habilidade_id}", status_code=204)
def desvincular(usuario_id: int, habilidade_id: int, repo: Repo):
    repo.remover_habilidade_usuario(usuario_id, habilidade_id)
    return Response(status_code=204)
