"""Contrato interno do currículo: IA seleciona IDs; Python recupera citações.

O schema é construído por solicitação, sem estado global de perfis.
O formato público do currículo e da auditoria continua sendo CurriculoPlano.
"""
from typing import Literal, Union

from pydantic import Field, create_model

from .schemas import CurriculoPlano, Estrito, Texto

VERSAO_CURRICULO = "workadapter-curriculo-evidencias-v2"
LIMITES = {"experiencias": 8, "formacoes": 8, "cursos": 10, "projetos": 8}


def preparar_plano(fontes: dict[str, str], habilidades):
    catalogo = {}
    por_fonte = {}
    for fonte, texto in fontes.items():
        ids = []
        for linha in texto.splitlines():
            restante = linha.strip()
            while restante:
                corte = min(len(restante), 2000)
                if corte < len(restante):
                    espaco = restante.rfind(" ", 0, corte)
                    if espaco > 0:
                        corte = espaco
                trecho = restante[:corte].strip()
                restante = restante[corte:].strip()
                if trecho:
                    ref = f"E{len(catalogo) + 1}"
                    catalogo[ref] = {"fonte": fonte, "trecho": trecho}
                    ids.append(ref)
        if ids:
            por_fonte[fonte] = ids

    if not catalogo:
        raise ValueError("O perfil não tem trechos disponíveis para o currículo.")

    def afirmacao(nome, ids):
        return create_model(
            nome,
            __base__=Estrito,
            texto=(Texto, ...),
            evidencias_ids=(list[Literal[tuple(ids)]], Field(
                min_length=1, max_length=8,
                description="Selecione IDs do catálogo que sustentam o texto.",
            )),
        )

    resumo = afirmacao("ResumoComIds", catalogo)
    campos = {"resumo": (resumo, ...)}
    referencias = {}
    for secao, limite in LIMITES.items():
        modelos = []
        referencias[secao] = []
        for fonte, ids in por_fonte.items():
            if not fonte.startswith(secao + ":"):
                continue
            referencias[secao].append(fonte)
            sufixo = f"{secao}_{len(modelos)}"
            destaque = afirmacao(f"Destaque_{sufixo}", ids)
            modelos.append(create_model(
                f"Item_{sufixo}",
                __base__=Estrito,
                fonte=(Literal[fonte], ...),
                destaques=(list[destaque], Field(max_length=4)),
            ))
        if modelos:
            item = modelos[0] if len(modelos) == 1 else Union[tuple(modelos)]
            campos[secao] = (list[item], Field(max_length=limite))
        else:
            campos[secao] = (list[str], Field(
                max_length=0, description="Sem registros: retorne [].",
            ))

    for campo, valores, limite in (
        ("habilidades", sorted(set(habilidades)), 30),
        ("idiomas", [f for f in por_fonte if f.startswith("idiomas:")], 10),
    ):
        tipo = Literal[tuple(valores)] if valores else str
        campos[campo] = (list[tipo], Field(max_length=limite if valores else 0))

    campos["alteracoes"] = (list[Texto], Field(max_length=10))
    campos["lacunas"] = (list[Texto], Field(max_length=10))
    schema = create_model("CurriculoPlanoComIds", __base__=Estrito, **campos)

    def converter(plano):
        # Revalida inclusive objetos criados por transportes de teste.
        dados = schema.model_validate(plano.model_dump()).model_dump()

        def restaurar(afirmacao):
            ids = afirmacao.pop("evidencias_ids")
            afirmacao["evidencias"] = [
                dict(catalogo[ref]) for ref in dict.fromkeys(ids)
            ]

        restaurar(dados["resumo"])
        for secao in LIMITES:
            for item in dados[secao]:
                for destaque in item["destaques"]:
                    restaurar(destaque)
        return CurriculoPlano.model_validate(dados)

    return schema, {
        "catalogo_evidencias": catalogo,
        "referencias_por_secao": referencias,
    }, converter
