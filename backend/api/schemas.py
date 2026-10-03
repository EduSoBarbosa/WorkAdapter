"""Corpos de requisição. Campos extras são rejeitados; PATCH aceita omissões.

Campos não anuláveis podem ser omitidos no PATCH, mas não receber null.
Datas: YYYY-MM-DD. Horários: ISO 8601 (preferencialmente com fuso).
"""
from copy import deepcopy
from datetime import date, datetime
from typing import Annotated, Any
from pydantic import BaseModel, ConfigDict, Field, create_model
from ..database.models import StatusEstudo, StatusCandidatura, Modalidade

Texto = Annotated[str, Field(min_length=1, max_length=200)]
Id = Annotated[int, Field(gt=0)]

class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def parcial(modelo, nome, *, excluir=()):
    campos = {}
    for chave, campo in modelo.model_fields.items():
        if chave in excluir:
            continue
        info = deepcopy(campo)
        # Default não validado: omissão é permitida, null explícito segue a anotação.
        info.default_factory = None
        info.default = None
        campos[chave] = (campo.annotation, info)
    return create_model(nome, __base__=Entrada, **campos)


class UsuarioCreate(Entrada):
    nome_completo: Texto
    email: str | None = Field(default=None, max_length=254)
    telefone: str | None = Field(default=None, max_length=30)
    cidade: str | None = Field(default=None, max_length=120)
    estado: str | None = Field(default=None, max_length=120)
    pais: str | None = Field(default=None, max_length=120)
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    resumo_profissional: str | None = None
    vaga_alvo_atual: Texto | None = None


class ExperienciaCreate(Entrada):
    cargo: Texto
    empresa: Texto
    tipo_vinculo: str | None = Field(default=None, max_length=80)
    localidade: Texto | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    atual: bool = False
    descricao: str | None = None
    resultados: str | None = None


class FormacaoCreate(Entrada):
    instituicao: Texto
    curso: Texto
    nivel: str | None = Field(default=None, max_length=80)
    status: StatusEstudo = StatusEstudo.CURSANDO
    data_inicio: date | None = None
    data_fim: date | None = None
    descricao: str | None = None


class CursoCreate(Entrada):
    nome: Texto
    instituicao: Texto | None = None
    carga_horaria: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    status: StatusEstudo = StatusEstudo.CURSANDO
    data_inicio: date | None = None
    data_conclusao: date | None = None
    descricao: str | None = None
    certificado_url: str | None = None


class ProjetoCreate(Entrada):
    nome: Texto
    descricao: str | None = None
    papel_desempenhado: str | None = None
    resultados: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    repositorio_url: str | None = None
    demonstracao_url: str | None = None


class IdiomaCreate(Entrada):
    idioma: Annotated[str, Field(min_length=1, max_length=80)]
    nivel: str | None = Field(default=None, max_length=80)
    certificacao: Texto | None = None
    pontuacao_certificacao: str | None = Field(default=None, max_length=80)


class HabilidadeCreate(Entrada):
    nome: Annotated[str, Field(min_length=1, max_length=120)]
    categoria: str | None = Field(default=None, max_length=80)


class HabilidadeUsuarioInput(Entrada):
    nivel: str | None = Field(default=None, max_length=80)


class StackInput(Entrada):
    habilidades_ids: list[Id]


class CurriculoCreate(Entrada):
    nome: Texto
    vaga_alvo: Texto | None = None
    empresa_alvo: Texto | None = None
    descricao_vaga: str | None = None
    plataforma_alvo: str | None = Field(default=None, max_length=120)
    conteudo: dict[str, Any] = Field(default_factory=dict)
    perfil_snapshot: dict[str, Any] = Field(default_factory=dict)
    alteracoes: list[Any] = Field(default_factory=list)
    lacunas: list[Any] = Field(default_factory=list)
    modelos_utilizados: list[str] = Field(default_factory=list)
    versao_prompt: str | None = Field(default=None, max_length=80)
    arquivo_url: str | None = None


class CandidaturaCreate(Entrada):
    nome: Texto | None = None
    titulo_vaga: Texto
    empresa: Texto
    descricao: str | None = None
    url_vaga: str | None = None
    tipo_contrato: str | None = Field(default=None, max_length=80)
    modalidade: Modalidade | None = None
    localidade: Texto | None = None
    data_candidatura: date | None = None
    status: StatusCandidatura = StatusCandidatura.SALVA
    etapa_atual: Annotated[str, Field(min_length=1, max_length=120)] = "Não iniciado"
    curriculo_id: Id | None = None
    plataforma: str | None = Field(default=None, max_length=120)
    observacoes: str | None = None


class MovimentacaoCreate(Entrada):
    status: StatusCandidatura
    etapa: Annotated[str, Field(min_length=1, max_length=120)]
    observacao: str | None = None
    ocorrido_em: datetime | None = None


UsuarioUpdate = parcial(UsuarioCreate, "UsuarioUpdate")
ExperienciaUpdate = parcial(ExperienciaCreate, "ExperienciaUpdate")
FormacaoUpdate = parcial(FormacaoCreate, "FormacaoUpdate")
CursoUpdate = parcial(CursoCreate, "CursoUpdate")
ProjetoUpdate = parcial(ProjetoCreate, "ProjetoUpdate")
IdiomaUpdate = parcial(IdiomaCreate, "IdiomaUpdate")
HabilidadeUpdate = parcial(HabilidadeCreate, "HabilidadeUpdate")
CurriculoUpdate = parcial(CurriculoCreate, "CurriculoUpdate")
CandidaturaUpdate = parcial(CandidaturaCreate, "CandidaturaUpdate", excluir={"status", "etapa_atual"})
