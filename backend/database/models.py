"""Modelos do WorkAdapter — Python 3.10+, SQLAlchemy 2.x e SQLite.

Inicializar (a partir da pasta backend):
    from database.models import inicializar_banco
    engine = inicializar_banco()

Não abre conexões nem cria arquivos durante o import.
Datas e horários são armazenados em UTC, sem tzinfo, por convenção.
O perfil_snapshot preserva a entrada usada na geração. No serviço, salve uma
nova versão ao editar um currículo já utilizado em uma candidatura.
JSON: ao editar conteúdo aninhado, atribua um novo objeto ao campo para que
o SQLAlchemy detecte a alteração (por exemplo, usando deepcopy).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON, CheckConstraint, Column, Enum as SQLEnum, ForeignKey,
    Integer, String, Table, Text, create_engine, event,
)
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class RegistroMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(default=agora_utc, onupdate=agora_utc)


class DonoMixin:
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)


class StatusEstudo(str, Enum):
    CURSANDO = "cursando"
    CONCLUIDO = "concluido"
    INTERROMPIDO = "interrompido"


class StatusCandidatura(str, Enum):
    SALVA = "salva"
    ENVIADA = "enviada"
    EM_ANDAMENTO = "em_andamento"
    OFERTA_RECEBIDA = "oferta_recebida"
    APROVADA = "aprovada"
    REPROVADA = "reprovada"
    DESISTENCIA = "desistencia"
    VAGA_ENCERRADA = "vaga_encerrada"


class Modalidade(str, Enum):
    REMOTO = "remoto"
    HIBRIDO = "hibrido"
    PRESENCIAL = "presencial"


def enum_coluna(classe: type[Enum], nome: str) -> SQLEnum:
    # SQLite não tem ENUM nativo: usa VARCHAR com CHECK.
    return SQLEnum(classe, name=nome, native_enum=False, create_constraint=True,
                   validate_strings=True, values_callable=lambda e: [v.value for v in e])


# Chaves primárias compostas impedem repetir a habilidade na mesma entidade.
experiencia_habilidades = Table(
    "experiencia_habilidades", Base.metadata,
    Column("experiencia_id", ForeignKey("experiencias.id", ondelete="CASCADE"), primary_key=True),
    Column("habilidade_id", ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True),
)
formacao_habilidades = Table(
    "formacao_habilidades", Base.metadata,
    Column("formacao_id", ForeignKey("formacoes.id", ondelete="CASCADE"), primary_key=True),
    Column("habilidade_id", ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True),
)
curso_habilidades = Table(
    "curso_habilidades", Base.metadata,
    Column("curso_id", ForeignKey("cursos.id", ondelete="CASCADE"), primary_key=True),
    Column("habilidade_id", ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True),
)
projeto_habilidades = Table(
    "projeto_habilidades", Base.metadata,
    Column("projeto_id", ForeignKey("projetos.id", ondelete="CASCADE"), primary_key=True),
    Column("habilidade_id", ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True),
)


class Usuario(RegistroMixin, Base):
    __tablename__ = "usuarios"

    nome_completo: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254))
    telefone: Mapped[str | None] = mapped_column(String(30))
    cidade: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[str | None] = mapped_column(String(120))
    pais: Mapped[str | None] = mapped_column(String(120))
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(Text)
    portfolio_url: Mapped[str | None] = mapped_column(Text)
    resumo_profissional: Mapped[str | None] = mapped_column(Text)
    vaga_alvo_atual: Mapped[str | None] = mapped_column(String(200))

    experiencias: Mapped[list[Experiencia]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    formacoes: Mapped[list[Formacao]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    cursos: Mapped[list[Curso]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    projetos: Mapped[list[Projeto]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    idiomas: Mapped[list[IdiomaUsuario]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    habilidades: Mapped[list[UsuarioHabilidade]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    curriculos: Mapped[list[Curriculo]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)
    candidaturas: Mapped[list[Candidatura]] = relationship(back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True)


class Experiencia(RegistroMixin, DonoMixin, Base):
    __tablename__ = "experiencias"
    __table_args__ = (CheckConstraint("data_fim IS NULL OR data_inicio IS NULL OR data_fim >= data_inicio", name="ck_experiencia_datas"),)

    cargo: Mapped[str] = mapped_column(String(200))
    empresa: Mapped[str] = mapped_column(String(200))
    tipo_vinculo: Mapped[str | None] = mapped_column(String(80))
    localidade: Mapped[str | None] = mapped_column(String(200))
    data_inicio: Mapped[date | None]
    data_fim: Mapped[date | None]
    atual: Mapped[bool] = mapped_column(default=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    resultados: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="experiencias")
    habilidades: Mapped[list[Habilidade]] = relationship(secondary=experiencia_habilidades)


class Formacao(RegistroMixin, DonoMixin, Base):
    __tablename__ = "formacoes"
    __table_args__ = (CheckConstraint("data_fim IS NULL OR data_inicio IS NULL OR data_fim >= data_inicio", name="ck_formacao_datas"),)

    instituicao: Mapped[str] = mapped_column(String(200))
    curso: Mapped[str] = mapped_column(String(200))
    nivel: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[StatusEstudo] = mapped_column(enum_coluna(StatusEstudo, "status_formacao"), default=StatusEstudo.CURSANDO)
    data_inicio: Mapped[date | None]
    data_fim: Mapped[date | None]  # Previsão quando status = cursando.
    descricao: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="formacoes")
    habilidades: Mapped[list[Habilidade]] = relationship(secondary=formacao_habilidades)


class Curso(RegistroMixin, DonoMixin, Base):
    __tablename__ = "cursos"
    __table_args__ = (
        CheckConstraint("carga_horaria IS NULL OR carga_horaria >= 0", name="ck_curso_carga"),
        CheckConstraint("data_conclusao IS NULL OR data_inicio IS NULL OR data_conclusao >= data_inicio", name="ck_curso_datas"),
    )

    nome: Mapped[str] = mapped_column(String(200))
    instituicao: Mapped[str | None] = mapped_column(String(200))
    carga_horaria: Mapped[float | None]
    status: Mapped[StatusEstudo] = mapped_column(enum_coluna(StatusEstudo, "status_curso"), default=StatusEstudo.CURSANDO)
    data_inicio: Mapped[date | None]
    data_conclusao: Mapped[date | None]
    descricao: Mapped[str | None] = mapped_column(Text)
    certificado_url: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="cursos")
    habilidades: Mapped[list[Habilidade]] = relationship(secondary=curso_habilidades)


class Projeto(RegistroMixin, DonoMixin, Base):
    __tablename__ = "projetos"
    __table_args__ = (CheckConstraint("data_fim IS NULL OR data_inicio IS NULL OR data_fim >= data_inicio", name="ck_projeto_datas"),)

    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    papel_desempenhado: Mapped[str | None] = mapped_column(Text)
    resultados: Mapped[str | None] = mapped_column(Text)
    data_inicio: Mapped[date | None]
    data_fim: Mapped[date | None]
    repositorio_url: Mapped[str | None] = mapped_column(Text)
    demonstracao_url: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="projetos")
    habilidades: Mapped[list[Habilidade]] = relationship(secondary=projeto_habilidades)


class IdiomaUsuario(RegistroMixin, DonoMixin, Base):
    __tablename__ = "idiomas_usuario"

    idioma: Mapped[str] = mapped_column(String(80))
    nivel: Mapped[str | None] = mapped_column(String(80))
    certificacao: Mapped[str | None] = mapped_column(String(200))
    pontuacao_certificacao: Mapped[str | None] = mapped_column(String(80))
    usuario: Mapped[Usuario] = relationship(back_populates="idiomas")


class Habilidade(RegistroMixin, Base):
    __tablename__ = "habilidades"

    nome: Mapped[str] = mapped_column(String(120, collation="NOCASE"), unique=True)
    categoria: Mapped[str | None] = mapped_column(String(80))


class UsuarioHabilidade(Base):
    __tablename__ = "usuario_habilidades"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    habilidade_id: Mapped[int] = mapped_column(ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True)
    nivel: Mapped[str | None] = mapped_column(String(80))
    usuario: Mapped[Usuario] = relationship(back_populates="habilidades")
    habilidade: Mapped[Habilidade] = relationship()


class Curriculo(RegistroMixin, DonoMixin, Base):
    __tablename__ = "curriculos"

    nome: Mapped[str] = mapped_column(String(200))
    vaga_alvo: Mapped[str | None] = mapped_column(String(200))
    empresa_alvo: Mapped[str | None] = mapped_column(String(200))
    descricao_vaga: Mapped[str | None] = mapped_column(Text)
    plataforma_alvo: Mapped[str | None] = mapped_column(String(120))
    conteudo: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    perfil_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    alteracoes: Mapped[list[Any]] = mapped_column(JSON, default=list)
    lacunas: Mapped[list[Any]] = mapped_column(JSON, default=list)
    modelos_utilizados: Mapped[list[str]] = mapped_column(JSON, default=list)
    versao_prompt: Mapped[str | None] = mapped_column(String(80))
    arquivo_url: Mapped[str | None] = mapped_column(Text)  # Também pode guardar caminho local.
    curriculo_origem_id: Mapped[int | None] = mapped_column(ForeignKey("curriculos.id", ondelete="SET NULL"), index=True)

    usuario: Mapped[Usuario] = relationship(back_populates="curriculos")
    curriculo_origem: Mapped[Curriculo | None] = relationship(remote_side="Curriculo.id")
    candidaturas: Mapped[list[Candidatura]] = relationship(back_populates="curriculo", passive_deletes="all")


class Candidatura(RegistroMixin, DonoMixin, Base):
    __tablename__ = "candidaturas"

    nome: Mapped[str | None] = mapped_column(String(200))
    titulo_vaga: Mapped[str] = mapped_column(String(200))
    empresa: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    url_vaga: Mapped[str | None] = mapped_column(Text)
    tipo_contrato: Mapped[str | None] = mapped_column(String(80))
    modalidade: Mapped[Modalidade | None] = mapped_column(enum_coluna(Modalidade, "modalidade"))
    localidade: Mapped[str | None] = mapped_column(String(200))
    data_candidatura: Mapped[date | None]
    status: Mapped[StatusCandidatura] = mapped_column(enum_coluna(StatusCandidatura, "status_candidatura"), default=StatusCandidatura.SALVA, index=True)
    etapa_atual: Mapped[str] = mapped_column(String(120), default="Não iniciado")
    # SET NULL permite excluir um currículo sem apagar a candidatura.
    # Para preservar versões enviadas, prefira arquivar currículos no serviço.
    curriculo_id: Mapped[int | None] = mapped_column(ForeignKey("curriculos.id", ondelete="SET NULL"), index=True)
    plataforma: Mapped[str | None] = mapped_column(String(120))
    observacoes: Mapped[str | None] = mapped_column(Text)
    ultima_movimentacao_em: Mapped[datetime | None]

    usuario: Mapped[Usuario] = relationship(back_populates="candidaturas")
    curriculo: Mapped[Curriculo | None] = relationship(back_populates="candidaturas")
    movimentacoes: Mapped[list[CandidaturaMovimentacao]] = relationship(
        back_populates="candidatura", cascade="all, delete-orphan",
        passive_deletes=True, order_by="CandidaturaMovimentacao.ocorrido_em",
    )


class CandidaturaMovimentacao(Base):
    __tablename__ = "candidatura_movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidatura_id: Mapped[int] = mapped_column(ForeignKey("candidaturas.id", ondelete="CASCADE"), index=True)
    status: Mapped[StatusCandidatura] = mapped_column(enum_coluna(StatusCandidatura, "status_movimentacao"))
    etapa: Mapped[str] = mapped_column(String(120))
    ocorrido_em: Mapped[datetime] = mapped_column(default=agora_utc)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)
    candidatura: Mapped[Candidatura] = relationship(back_populates="movimentacoes")


def registrar_movimentacao(
    session: Session, candidatura: Candidatura, *, status: StatusCandidatura,
    etapa: str, observacao: str | None = None, ocorrido_em: datetime | None = None,
) -> CandidaturaMovimentacao:
    """Adiciona histórico e sincroniza a situação atual; o chamador faz commit.

    Ao inserir um evento antigo, mantém a situação do evento mais recente.
    Alterações/exclusões posteriores do histórico exigem recálculo no serviço.
    """
    momento = ocorrido_em or agora_utc()
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    movimento = CandidaturaMovimentacao(
        candidatura=candidatura, status=status, etapa=etapa,
        observacao=observacao, ocorrido_em=momento,
    )
    session.add(movimento)
    if candidatura.ultima_movimentacao_em is None or momento >= candidatura.ultima_movimentacao_em:
        candidatura.status = status
        candidatura.etapa_atual = etapa
        candidatura.ultima_movimentacao_em = momento
    return movimento


def criar_engine(caminho: str | Path | None = None, *, echo: bool = False) -> Engine:
    """Cria engine SQLite com chaves estrangeiras habilitadas por conexão.

    Padrão: workadapter.db ao lado deste arquivo. Cada requisição FastAPI deve
    usar sua própria Session; não compartilhe uma Session global entre threads.
    """
    destino = Path(caminho) if caminho is not None else Path(__file__).with_name("workadapter.db")
    destino = destino.resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(destino)),
        connect_args={"check_same_thread": False, "timeout": 30}, echo=echo,
    )

    @event.listens_for(engine, "connect")
    def configurar_sqlite(conexao, _registro):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def inicializar_banco(caminho: str | Path | None = None, *, echo: bool = False) -> Engine:
    """Cria tabelas ausentes; não migra tabelas existentes."""
    engine = criar_engine(caminho, echo=echo)
    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    engine = inicializar_banco()
    print(f"Banco inicializado: {engine.url.database}")
    engine.dispose()
