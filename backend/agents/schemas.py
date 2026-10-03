"""Contratos do Qwen e da API. Saídas estritas, próprias para consumir em React/PDF."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Texto = Annotated[str, Field(min_length=1, max_length=2000)]
Curto = Annotated[str, Field(min_length=1, max_length=250)]
Id = Annotated[int, Field(gt=0)]


class Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Evidencia(Estrito):
    fonte: Curto = Field(description="Chave exata no catálogo: usuario, projetos:1, cursos:2 etc.")
    trecho: Texto = Field(description="Citação literal, contínua e não vazia da fonte indicada.")


class Afirmacao(Estrito):
    texto: Texto
    evidencias: list[Evidencia] = Field(min_length=1, max_length=8)


class Vaga(Estrito):
    titulo: Curto
    empresa: str | None = Field(default=None, max_length=250)
    plataforma: str | None = Field(default=None, max_length=120)
    descricao: str = Field(min_length=20, max_length=16000)


class EntradaVaga(Estrito):
    vaga: Vaga | None = None
    candidatura_id: Id | None = None

    @model_validator(mode="after")
    def uma_origem(self):
        if (self.vaga is None) == (self.candidatura_id is None):
            raise ValueError("Informe exatamente um: vaga ou candidatura_id.")
        return self


class GerarCurriculoInput(EntradaVaga):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    salvar: bool = False


class PerfilInput(Estrito):
    objetivo: str | None = Field(default=None, min_length=1, max_length=500)


class EstudosInput(PerfilInput):
    horas_por_semana: int = Field(default=5, ge=1, le=40)
    semanas: int = Field(default=4, ge=1, le=12)
    limite_candidaturas: int = Field(default=20, ge=1, le=30)


class ItemCurriculo(Estrito):
    fonte: Curto = Field(description="Referência de um item real do catálogo.")
    destaques: list[Afirmacao] = Field(max_length=4)


class CurriculoPlano(Estrito):
    resumo: Afirmacao
    experiencias: list[ItemCurriculo] = Field(max_length=8)
    formacoes: list[ItemCurriculo] = Field(max_length=8)
    cursos: list[ItemCurriculo] = Field(max_length=10)
    projetos: list[ItemCurriculo] = Field(max_length=8)
    habilidades: list[Curto] = Field(max_length=30, description="Apenas nomes presentes no perfil ou nas stacks.")
    idiomas: list[Curto] = Field(max_length=10, description="Referências idiomas:<id>, sem inventar nível.")
    alteracoes: list[Texto] = Field(max_length=10)
    lacunas: list[Texto] = Field(max_length=10)


class CargoSugerido(Estrito):
    cargo: Curto
    nivel_sugerido: Curto
    justificativa: Texto
    evidencias: list[Evidencia] = Field(min_length=1, max_length=6)
    pontos_a_desenvolver: list[Texto] = Field(max_length=5)
    termos_busca: list[Curto] = Field(min_length=1, max_length=6)


class PerfilAnalise(Estrito):
    resumo: Afirmacao
    pontos_fortes: list[Afirmacao] = Field(max_length=6)
    cargos_sugeridos: list[CargoSugerido] = Field(min_length=1, max_length=6)
    limitacoes: list[Texto] = Field(max_length=6)


class CriterioMatch(Estrito):
    requisito: Curto
    trecho_vaga: Texto = Field(description="Trecho literal da descrição da vaga que contém este requisito.")
    importancia: Literal["obrigatorio", "desejavel", "nao_especificada"]
    atendimento: Literal["atende", "parcial", "sem_evidencia"]
    justificativa: Texto
    evidencias: list[Evidencia] = Field(max_length=6)

    @model_validator(mode="after")
    def exigir_evidencia(self):
        if self.atendimento != "sem_evidencia" and not self.evidencias:
            raise ValueError("Atendimento positivo ou parcial exige evidências.")
        if self.atendimento == "sem_evidencia" and self.evidencias:
            raise ValueError("Use evidências somente para atendimento positivo ou parcial.")
        return self


class MatchAnalise(Estrito):
    criterios: list[CriterioMatch] = Field(max_length=20)
    sintese: Texto
    limitacoes: list[Texto] = Field(max_length=8)


class TemaRecorrente(Estrito):
    tema: Curto
    ocorrencias: list["Ocorrencia"] = Field(min_length=1, max_length=30)


class Ocorrencia(Estrito):
    candidatura_id: Id
    trecho: Texto


class Estudo(Estrito):
    tema: Curto
    prioridade: Literal["alta", "media", "baixa"]
    motivo: Texto
    base: Literal["objetivo", "candidaturas", "ambos"]
    ocorrencias: list[Ocorrencia] = Field(max_length=10)
    semana_inicio: int = Field(ge=1, le=12)
    semana_fim: int = Field(ge=1, le=12)
    horas_estimadas: int = Field(ge=1, le=480)
    atividades: list[Texto] = Field(min_length=1, max_length=5)
    entrega_pratica: Texto
    criterio_conclusao: Texto
    termos_busca: list[Curto] = Field(max_length=5)

    @model_validator(mode="after")
    def coerencia(self):
        if self.semana_fim < self.semana_inicio:
            raise ValueError("Semana final anterior à inicial.")
        if self.base in ("candidaturas", "ambos") and not self.ocorrencias:
            raise ValueError("Recomendação baseada em candidaturas exige trechos dessas vagas.")
        return self


class EstudosAnalise(Estrito):
    objetivo: Texto
    temas_recorrentes: list[TemaRecorrente] = Field(max_length=8)
    plano: list[Estudo] = Field(min_length=1, max_length=8)
    limitacoes: list[Texto] = Field(max_length=8)


TemaRecorrente.model_rebuild()
