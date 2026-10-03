"""Persistência do WorkAdapter (SQLAlchemy 2.x, compatível com models.py).

Uso, a partir da pasta backend:
    from sqlalchemy.orm import Session
    from database.models import inicializar_banco
    from database.repository import Repository

    engine = inicializar_banco()
    with Session(engine) as session, session.begin():
        repo = Repository(session)
        usuario = repo.criar_usuario(nome_completo="Eduardo")
        projeto = repo.criar_item_perfil(usuario.id, "projetos", nome="GeoVision")
        python = repo.obter_ou_criar_habilidade("Python", "linguagem")
        repo.definir_stack(usuario.id, "projetos", projeto.id, [python.id])

Os métodos fazem flush, nunca commit/rollback: a transação pertence ao chamador.
Use Session.begin() para confirmar tudo junto ou desfazer tudo em caso de erro.
Os retornos são objetos ORM; serialize com schemas Pydantic no FastAPI.
Datas devem chegar como date/datetime e JSON como dict/list, já validados.
A edição dos JSON substitui o campo inteiro (não é um merge parcial).
Use apenas estes métodos para preservar as regras de versões e histórico.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from enum import Enum
from typing import Any, Iterable

from sqlalchemy import inspect, or_, select
from sqlalchemy.orm import Session

from .models import (
    Usuario, Experiencia, Formacao, Curso, Projeto, IdiomaUsuario,
    Habilidade, UsuarioHabilidade, Curriculo, Candidatura,
    CandidaturaMovimentacao, StatusCandidatura, agora_utc,
    registrar_movimentacao as _registrar_movimentacao,
)


class RegistroNaoEncontrado(LookupError):
    """O registro não existe ou não pertence ao usuário informado."""


class OperacaoNaoPermitida(ValueError):
    """A operação violaria uma regra de negócio."""


ITENS_PERFIL = {
    "experiencias": Experiencia,
    "formacoes": Formacao,
    "cursos": Curso,
    "projetos": Projeto,
    "idiomas": IdiomaUsuario,
}
CAMPOS_INTERNOS = {
    "id", "usuario_id", "criado_em", "atualizado_em",
    "curriculo_origem_id", "ultima_movimentacao_em",
}


def _validar_campos(modelo, dados: dict[str, Any], *, bloquear=()) -> dict[str, Any]:
    permitidos = {c.key for c in inspect(modelo).columns} - CAMPOS_INTERNOS - set(bloquear)
    desconhecidos = set(dados) - permitidos
    if desconhecidos:
        raise ValueError(f"Campos não editáveis em {modelo.__name__}: {', '.join(sorted(desconhecidos))}")
    return deepcopy(dados)


def _atribuir(objeto, dados: dict[str, Any]) -> None:
    for campo, valor in dados.items():
        setattr(objeto, campo, valor)


def _json_valor(valor):
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return deepcopy(valor)


def _colunas_json(objeto) -> dict[str, Any]:
    return {c.key: _json_valor(getattr(objeto, c.key)) for c in inspect(type(objeto)).columns}


class Repository:
    """Uma instância por Session; não compartilhar entre requisições/threads.

    usuario_id limita as operações ao proprietário, mas não substitui
    autenticação caso o projeto deixe de ser exclusivamente local.
    """

    def __init__(self, session: Session):
        self.session = session

    def _salvar(self, objeto):
        self.session.add(objeto)
        self.session.flush()
        return objeto

    def _obter(self, modelo, registro_id: int, usuario_id: int | None = None):
        consulta = select(modelo).where(modelo.id == registro_id)
        if usuario_id is not None:
            consulta = consulta.where(modelo.usuario_id == usuario_id)
        objeto = self.session.scalar(consulta)
        if objeto is None:
            raise RegistroNaoEncontrado(f"{modelo.__name__} {registro_id} não encontrado.")
        return objeto

    @staticmethod
    def _modelo_perfil(tipo: str):
        if tipo not in ITENS_PERFIL:
            raise ValueError(f"Tipo inválido. Use: {', '.join(ITENS_PERFIL)}")
        return ITENS_PERFIL[tipo]

    def _listar(self, consulta, limite: int, offset: int):
        if not 1 <= limite <= 1000 or offset < 0:
            raise ValueError("limite deve estar entre 1 e 1000; offset deve ser >= 0.")
        return list(self.session.scalars(consulta.limit(limite).offset(offset)))

    # Usuários e perfil profissional
    def criar_usuario(self, **dados) -> Usuario:
        return self._salvar(Usuario(**_validar_campos(Usuario, dados)))

    def obter_usuario(self, usuario_id: int) -> Usuario:
        return self._obter(Usuario, usuario_id)

    def listar_usuarios(self, *, limite=100, offset=0) -> list[Usuario]:
        return self._listar(select(Usuario).order_by(Usuario.id), limite, offset)

    def atualizar_usuario(self, usuario_id: int, **dados) -> Usuario:
        usuario = self.obter_usuario(usuario_id)
        _atribuir(usuario, _validar_campos(Usuario, dados))
        return self._salvar(usuario)

    def excluir_usuario(self, usuario_id: int) -> None:
        """Exclui também perfil, currículos, candidaturas e histórico do usuário."""
        self.session.delete(self.obter_usuario(usuario_id))
        self.session.flush()
        self.session.expire_all()  # Invalida coleções afetadas pelo CASCADE do SQLite.

    def criar_item_perfil(self, usuario_id: int, tipo: str, **dados):
        self.obter_usuario(usuario_id)
        modelo = self._modelo_perfil(tipo)
        return self._salvar(modelo(usuario_id=usuario_id, **_validar_campos(modelo, dados)))

    def obter_item_perfil(self, usuario_id: int, tipo: str, registro_id: int):
        return self._obter(self._modelo_perfil(tipo), registro_id, usuario_id)

    def listar_itens_perfil(self, usuario_id: int, tipo: str, *, limite=100, offset=0):
        self.obter_usuario(usuario_id)
        modelo = self._modelo_perfil(tipo)
        return self._listar(select(modelo).where(modelo.usuario_id == usuario_id).order_by(modelo.id), limite, offset)

    def atualizar_item_perfil(self, usuario_id: int, tipo: str, registro_id: int, **dados):
        objeto = self.obter_item_perfil(usuario_id, tipo, registro_id)
        _atribuir(objeto, _validar_campos(type(objeto), dados))
        return self._salvar(objeto)

    def excluir_item_perfil(self, usuario_id: int, tipo: str, registro_id: int) -> None:
        self.session.delete(self.obter_item_perfil(usuario_id, tipo, registro_id))
        self.session.flush()
        self.session.expire_all()

    def obter_perfil_completo(self, usuario_id: int) -> dict[str, Any]:
        """Snapshot JSON independente, pronto para fornecer ao modelo de IA."""
        self.session.flush()
        perfil = {"usuario": _colunas_json(self.obter_usuario(usuario_id))}
        for tipo, modelo in ITENS_PERFIL.items():
            itens = self.session.scalars(select(modelo).where(modelo.usuario_id == usuario_id).order_by(modelo.id))
            perfil[tipo] = []
            for item in itens:
                dados = _colunas_json(item)
                if tipo != "idiomas":
                    dados["habilidades"] = [_colunas_json(h) for h in item.habilidades]
                perfil[tipo].append(dados)
        perfil["habilidades"] = [
            {**_colunas_json(v.habilidade), "nivel": v.nivel}
            for v in self.listar_habilidades_usuario(usuario_id)
        ]
        return perfil

    # Catálogo global e associações de habilidades
    def obter_habilidade(self, habilidade_id: int) -> Habilidade:
        return self._obter(Habilidade, habilidade_id)

    def obter_ou_criar_habilidade(self, nome: str, categoria: str | None = None) -> Habilidade:
        nome = nome.strip()
        if not nome:
            raise ValueError("O nome da habilidade não pode ficar vazio.")
        habilidade = self.session.scalar(select(Habilidade).where(Habilidade.nome == nome))
        if habilidade is not None:
            return habilidade
        return self._salvar(Habilidade(nome=nome, categoria=categoria))

    def listar_habilidades(self, *, busca: str | None = None, limite=100, offset=0):
        consulta = select(Habilidade).order_by(Habilidade.nome, Habilidade.id)
        if busca:
            consulta = consulta.where(Habilidade.nome.contains(busca, autoescape=True))
        return self._listar(consulta, limite, offset)

    def atualizar_habilidade(self, habilidade_id: int, **dados) -> Habilidade:
        """Edita o catálogo compartilhado, refletindo nos projetos/cursos vinculados."""
        dados = _validar_campos(Habilidade, dados)
        if "nome" in dados:
            if not isinstance(dados["nome"], str) or not dados["nome"].strip():
                raise ValueError("O nome da habilidade não pode ficar vazio.")
            dados["nome"] = dados["nome"].strip()
        habilidade = self.obter_habilidade(habilidade_id)
        _atribuir(habilidade, dados)
        return self._salvar(habilidade)

    def excluir_habilidade(self, habilidade_id: int) -> None:
        habilidade = self.obter_habilidade(habilidade_id)
        usada = self.session.scalar(select(UsuarioHabilidade.usuario_id).where(UsuarioHabilidade.habilidade_id == habilidade_id).limit(1)) is not None
        for modelo in (Experiencia, Formacao, Curso, Projeto):
            usada = usada or self.session.scalar(select(modelo.id).where(modelo.habilidades.any(Habilidade.id == habilidade_id)).limit(1)) is not None
        if usada:
            raise OperacaoNaoPermitida("Remova os vínculos antes de excluir a habilidade do catálogo.")
        self.session.delete(habilidade)
        self.session.flush()

    def definir_habilidade_usuario(self, usuario_id: int, habilidade_id: int, nivel: str | None = None) -> UsuarioHabilidade:
        self.obter_usuario(usuario_id)
        self.obter_habilidade(habilidade_id)
        vinculo = self.session.get(UsuarioHabilidade, (usuario_id, habilidade_id))
        if vinculo is None:
            vinculo = UsuarioHabilidade(usuario_id=usuario_id, habilidade_id=habilidade_id)
        vinculo.nivel = nivel
        return self._salvar(vinculo)

    def listar_habilidades_usuario(self, usuario_id: int) -> list[UsuarioHabilidade]:
        self.obter_usuario(usuario_id)
        return list(self.session.scalars(select(UsuarioHabilidade).where(UsuarioHabilidade.usuario_id == usuario_id).order_by(UsuarioHabilidade.habilidade_id)))

    def remover_habilidade_usuario(self, usuario_id: int, habilidade_id: int) -> bool:
        self.obter_usuario(usuario_id)
        vinculo = self.session.get(UsuarioHabilidade, (usuario_id, habilidade_id))
        if vinculo is None:
            return False
        self.session.delete(vinculo)
        self.session.flush()
        self.session.expire_all()
        return True

    def definir_stack(self, usuario_id: int, tipo: str, registro_id: int, habilidades_ids: Iterable[int]):
        """Substitui a stack completa. [] remove todos os vínculos; elimina IDs repetidos."""
        if tipo == "idiomas":
            raise ValueError("Idiomas não possuem stack.")
        objeto = self.obter_item_perfil(usuario_id, tipo, registro_id)
        habilidades = [self.obter_habilidade(i) for i in dict.fromkeys(habilidades_ids)]
        objeto.habilidades = habilidades
        objeto.atualizado_em = agora_utc()
        return self._salvar(objeto)

    # Currículos: conteúdo salvo é independente do perfil atual.
    def criar_curriculo(self, usuario_id: int, **dados) -> Curriculo:
        self.obter_usuario(usuario_id)
        dados = _validar_campos(Curriculo, dados)
        if "perfil_snapshot" not in dados:
            dados["perfil_snapshot"] = self.obter_perfil_completo(usuario_id)
        return self._salvar(Curriculo(usuario_id=usuario_id, **dados))

    def obter_curriculo(self, usuario_id: int, curriculo_id: int) -> Curriculo:
        return self._obter(Curriculo, curriculo_id, usuario_id)

    def listar_curriculos(self, usuario_id: int, *, limite=100, offset=0):
        self.obter_usuario(usuario_id)
        return self._listar(select(Curriculo).where(Curriculo.usuario_id == usuario_id).order_by(Curriculo.id.desc()), limite, offset)

    def _curriculo_em_uso(self, curriculo_id: int) -> bool:
        return self.session.scalar(select(Candidatura.id).where(Candidatura.curriculo_id == curriculo_id).limit(1)) is not None

    def atualizar_curriculo(self, usuario_id: int, curriculo_id: int, **dados) -> Curriculo:
        curriculo = self.obter_curriculo(usuario_id, curriculo_id)
        if self._curriculo_em_uso(curriculo_id):
            raise OperacaoNaoPermitida("Currículo vinculado a candidatura: use criar_versao_curriculo().")
        _atribuir(curriculo, _validar_campos(Curriculo, dados))
        return self._salvar(curriculo)

    def criar_versao_curriculo(self, usuario_id: int, curriculo_id: int, **alteracoes) -> Curriculo:
        """Copia a versão e seu snapshot, mantendo candidaturas na versão original.

        Sem novo perfil_snapshot, mantém a evidência original. Sem arquivo_url,
        limpa a referência exportada, pois o arquivo anterior pode estar desatualizado.
        """
        original = self.obter_curriculo(usuario_id, curriculo_id)
        alteracoes = _validar_campos(Curriculo, alteracoes)
        dados = {c.key: deepcopy(getattr(original, c.key)) for c in inspect(Curriculo).columns if c.key not in CAMPOS_INTERNOS}
        dados["nome"] = f"{original.nome} (nova versão)"
        dados["arquivo_url"] = None
        dados.update(alteracoes)
        return self._salvar(Curriculo(usuario_id=usuario_id, curriculo_origem_id=original.id, **dados))

    def excluir_curriculo(self, usuario_id: int, curriculo_id: int) -> None:
        curriculo = self.obter_curriculo(usuario_id, curriculo_id)
        if self._curriculo_em_uso(curriculo_id):
            raise OperacaoNaoPermitida("Currículo em uso: desvincule-o da candidatura antes de excluir.")
        self.session.delete(curriculo)
        self.session.flush()
        self.session.expire_all()

    # Candidaturas e histórico
    def criar_candidatura(self, usuario_id: int, **dados) -> Candidatura:
        self.obter_usuario(usuario_id)
        dados = _validar_campos(Candidatura, dados)
        if dados.get("curriculo_id") is not None:
            self.obter_curriculo(usuario_id, dados["curriculo_id"])
        status = StatusCandidatura(dados.pop("status", StatusCandidatura.SALVA))
        etapa = dados.pop("etapa_atual", "Não iniciado")
        if not isinstance(etapa, str) or not etapa.strip():
            raise ValueError("A etapa não pode ficar vazia.")
        candidatura = self._salvar(Candidatura(usuario_id=usuario_id, status=status, etapa_atual=etapa.strip(), **dados))
        self.adicionar_movimentacao(usuario_id, candidatura.id, status=status, etapa=etapa, observacao="Registro inicial")
        return candidatura

    def obter_candidatura(self, usuario_id: int, candidatura_id: int) -> Candidatura:
        return self._obter(Candidatura, candidatura_id, usuario_id)

    def listar_candidaturas(self, usuario_id: int, *, status=None, plataforma=None, busca=None, limite=100, offset=0):
        self.obter_usuario(usuario_id)
        consulta = select(Candidatura).where(Candidatura.usuario_id == usuario_id)
        if status is not None:
            consulta = consulta.where(Candidatura.status == StatusCandidatura(status))
        if plataforma is not None:
            consulta = consulta.where(Candidatura.plataforma == plataforma)
        if busca:
            consulta = consulta.where(or_(*(campo.contains(busca, autoescape=True) for campo in (Candidatura.nome, Candidatura.empresa, Candidatura.titulo_vaga))))
        return self._listar(consulta.order_by(Candidatura.atualizado_em.desc(), Candidatura.id.desc()), limite, offset)

    def atualizar_candidatura(self, usuario_id: int, candidatura_id: int, **dados) -> Candidatura:
        """Status e etapa são alterados exclusivamente por adicionar_movimentacao()."""
        dados = _validar_campos(Candidatura, dados, bloquear={"status", "etapa_atual"})
        candidatura = self.obter_candidatura(usuario_id, candidatura_id)
        if dados.get("curriculo_id") is not None:
            self.obter_curriculo(usuario_id, dados["curriculo_id"])
        _atribuir(candidatura, dados)
        return self._salvar(candidatura)

    def excluir_candidatura(self, usuario_id: int, candidatura_id: int) -> None:
        self.session.delete(self.obter_candidatura(usuario_id, candidatura_id))
        self.session.flush()
        self.session.expire_all()

    def adicionar_movimentacao(self, usuario_id: int, candidatura_id: int, *, status: StatusCandidatura | str, etapa: str, observacao: str | None = None, ocorrido_em: datetime | None = None) -> CandidaturaMovimentacao:
        candidatura = self.obter_candidatura(usuario_id, candidatura_id)
        if not isinstance(etapa, str) or not etapa.strip():
            raise ValueError("A etapa não pode ficar vazia.")
        movimento = _registrar_movimentacao(self.session, candidatura, status=StatusCandidatura(status), etapa=etapa.strip(), observacao=observacao, ocorrido_em=ocorrido_em)
        candidatura.atualizado_em = agora_utc()
        self.session.flush()
        return movimento

    def listar_movimentacoes(self, usuario_id: int, candidatura_id: int) -> list[CandidaturaMovimentacao]:
        """Histórico somente de acréscimo; correções são novos eventos."""
        self.obter_candidatura(usuario_id, candidatura_id)
        return list(self.session.scalars(select(CandidaturaMovimentacao).where(CandidaturaMovimentacao.candidatura_id == candidatura_id).order_by(CandidaturaMovimentacao.ocorrido_em, CandidaturaMovimentacao.id)))
