from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect


def serialize(objeto, *, stack=False):
    dados = {c.key: getattr(objeto, c.key) for c in inspect(type(objeto)).columns}
    if stack:
        dados["habilidades"] = [serialize(h) for h in objeto.habilidades]
    return jsonable_encoder(dados)
