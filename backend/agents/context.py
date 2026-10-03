"""Contexto com fontes verificáveis. Contatos ficam fora da inferência."""
from collections import Counter
from copy import deepcopy
import json
import re
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database.models import Candidatura
from ..database.repository import Repository
from .schemas import Evidencia, Vaga

SECOES = ("experiencias", "formacoes", "cursos", "projetos", "idiomas")
IGNORAR = {"id", "usuario_id", "criado_em", "atualizado_em"}


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip().casefold()


def montar_fontes(perfil: dict) -> dict[str, str]:
    """Não envia contatos, nome, URLs pessoais ou localização ao classificador."""
    fontes = {}
    usuario = {k: perfil["usuario"].get(k) for k in ("resumo_profissional", "vaga_alvo_atual") if perfil["usuario"].get(k)}
    if usuario:
        fontes["usuario"] = "\n".join(f"{k}: {v}" for k, v in usuario.items())
    for secao in SECOES:
        for item in perfil[secao]:
            linhas = []
            for k, v in item.items():
                if k in IGNORAR or k.endswith("_url") or v is None or v == "":
                    continue
                if k == "habilidades":
                    v = ", ".join(h["nome"] for h in v)
                elif not isinstance(v, str):
                    v = json.dumps(v, ensure_ascii=False)
                linhas.append(f"{k}: {v}")
            fontes[f"{secao}:{item['id']}"] = "\n".join(linhas)
    for h in perfil["habilidades"]:
        fontes[f"habilidades:{h['id']}"] = f"nome: {h['nome']}\ncategoria: {h.get('categoria') or 'não informada'}\nnivel: {h.get('nivel') or 'não informado'}"
    return fontes


def validar_evidencia(evidencia: Evidencia, fontes: dict):
    if evidencia.fonte not in fontes:
        raise ValueError(f"Fonte desconhecida: {evidencia.fonte}.")
    if normalizar(evidencia.trecho) not in normalizar(fontes[evidencia.fonte]):
        raise ValueError(f"O trecho não é literal na fonte {evidencia.fonte}.")


def validar_afirmacao(afirmacao, fontes):
    for e in afirmacao.evidencias:
        validar_evidencia(e, fontes)


def carregar_perfil(engine, usuario_id):
    with Session(engine) as session:
        perfil = Repository(session).obter_perfil_completo(usuario_id)
    if not montar_fontes(perfil):
        raise ValueError("Preencha formação, projetos, habilidades ou resumo profissional antes de solicitar uma análise.")
    return perfil


def resolver_vaga(engine, usuario_id, entrada):
    if entrada.vaga is not None:
        return entrada.vaga
    with Session(engine) as session:
        item = Repository(session).obter_candidatura(usuario_id, entrada.candidatura_id)
        if not item.descricao or len(item.descricao.strip()) < 20:
            raise ValueError("A candidatura precisa de uma descrição de vaga com pelo menos 20 caracteres.")
        return Vaga(titulo=item.titulo_vaga, empresa=item.empresa, plataforma=item.plataforma, descricao=item.descricao)


def carregar_historico(engine, usuario_id, limite):
    with Session(engine) as session:
        totais = session.execute(select(Candidatura.status, func.count()).where(Candidatura.usuario_id == usuario_id).group_by(Candidatura.status)).all()
        itens = session.scalars(select(Candidatura).where(Candidatura.usuario_id == usuario_id).order_by(Candidatura.atualizado_em.desc(), Candidatura.id.desc()).limit(limite)).all()
        vagas = []
        for item in itens:
            descricao = item.descricao or ""
            vagas.append({"id": item.id, "titulo": item.titulo_vaga, "descricao": descricao[:2500],
                          "descricao_truncada": len(descricao) > 2500, "status": item.status.value,
                          "etapa_atual": item.etapa_atual, "plataforma": item.plataforma})
        resumo = {"total": sum(n for _, n in totais), "por_status": {k.value: n for k, n in totais},
                  "amostra": len(vagas), "criterio_amostra": "últimas atualizações, até o limite solicitado",
                  "titulos_na_amostra": dict(Counter(v["titulo"] for v in vagas))}
    return deepcopy(vagas), resumo
