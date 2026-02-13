"""전략 API 엔드포인트"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import StrategyTemplateCreate, StrategyTemplateResponse
from app.db.models import StrategyTemplate
from app.db.session import get_db
from app.strategies import STRATEGY_REGISTRY
from app.utils.response import success_response

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_strategies():
    """사용 가능한 전략 목록"""
    strategies = [
        {"name": name, "class": cls.__name__}
        for name, cls in STRATEGY_REGISTRY.items()
    ]
    return success_response(data=strategies)


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    """저장된 전략 템플릿 목록"""
    templates = db.query(StrategyTemplate).all()
    items = [StrategyTemplateResponse.model_validate(t).model_dump() for t in templates]
    return success_response(data=items)


@router.post("/templates")
def create_template(body: StrategyTemplateCreate, db: Session = Depends(get_db)):
    """전략 템플릿 저장"""
    template = StrategyTemplate(
        name=body.name,
        description=body.description,
        strategy_type=body.strategy_type,
        default_parameters=body.default_parameters,
        parameter_schema=body.parameter_schema,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return success_response(
        data=StrategyTemplateResponse.model_validate(template).model_dump()
    )
