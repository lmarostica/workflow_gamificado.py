import json

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from sqlmodel import Session, func, select

from server.auth import require_client_key
from server.db import get_session
from server.models import Job, Rpa, utcnow
from server.schemas import RpaCreate, RpaOut, RpaUpdate

router = APIRouter(
    prefix="/rpas", tags=["rpas"], dependencies=[Depends(require_client_key)]
)


def _validate_schema(schema: dict | None) -> None:
    if schema is None:
        return
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise HTTPException(
            status_code=422, detail=f"params_schema inválido: {exc.message}"
        )


def to_out(rpa: Rpa) -> RpaOut:
    return RpaOut(
        id=rpa.id,
        name=rpa.name,
        description=rpa.description,
        params_schema=json.loads(rpa.params_schema) if rpa.params_schema else None,
        default_timeout_seconds=rpa.default_timeout_seconds,
        enabled=rpa.enabled,
        created_at=rpa.created_at,
        updated_at=rpa.updated_at,
    )


def _get_or_404(session: Session, name: str) -> Rpa:
    rpa = session.exec(select(Rpa).where(Rpa.name == name)).first()
    if rpa is None:
        raise HTTPException(status_code=404, detail=f"RPA '{name}' não encontrado")
    return rpa


@router.post("", status_code=201, response_model=RpaOut)
def create_rpa(body: RpaCreate, session: Session = Depends(get_session)):
    _validate_schema(body.params_schema)
    if session.exec(select(Rpa).where(Rpa.name == body.name)).first():
        raise HTTPException(status_code=409, detail=f"RPA '{body.name}' já existe")
    rpa = Rpa(
        name=body.name,
        description=body.description,
        params_schema=json.dumps(body.params_schema) if body.params_schema else None,
        default_timeout_seconds=body.default_timeout_seconds,
    )
    session.add(rpa)
    session.commit()
    session.refresh(rpa)
    return to_out(rpa)


@router.get("", response_model=list[RpaOut])
def list_rpas(session: Session = Depends(get_session)):
    rpas = session.exec(select(Rpa).order_by(Rpa.name)).all()
    return [to_out(r) for r in rpas]


@router.get("/{name}", response_model=RpaOut)
def get_rpa(name: str, session: Session = Depends(get_session)):
    return to_out(_get_or_404(session, name))


@router.patch("/{name}", response_model=RpaOut)
def update_rpa(name: str, body: RpaUpdate, session: Session = Depends(get_session)):
    rpa = _get_or_404(session, name)
    data = body.model_dump(exclude_unset=True)
    if "params_schema" in data:
        _validate_schema(data["params_schema"])
        rpa.params_schema = (
            json.dumps(data["params_schema"])
            if data["params_schema"] is not None
            else None
        )
        data.pop("params_schema")
    for field, value in data.items():
        setattr(rpa, field, value)
    rpa.updated_at = utcnow()
    session.add(rpa)
    session.commit()
    session.refresh(rpa)
    return to_out(rpa)


@router.delete("/{name}", status_code=204)
def delete_rpa(name: str, session: Session = Depends(get_session)):
    rpa = _get_or_404(session, name)
    job_count = session.exec(
        select(func.count()).select_from(Job).where(Job.rpa_id == rpa.id)
    ).one()
    if job_count:
        raise HTTPException(
            status_code=409,
            detail="RPA possui jobs no histórico; use PATCH enabled=false",
        )
    session.delete(rpa)
    session.commit()
