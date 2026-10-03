"""Uma Session e uma transação por requisição."""
from typing import Annotated
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from ..database.repository import Repository


def get_repository(request: Request):
    with Session(request.app.state.engine) as session:
        with session.begin():
            yield Repository(session)


# Finaliza a transação antes de enviar a resposta HTTP.
Repo = Annotated[Repository, Depends(get_repository, scope="function")]
