from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.db.database import get_session
from app.core.security import get_tenant_id
from app.models.financial import Category
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
def get_categories(
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    categories = session.exec(select(Category)).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@router.post("", response_model=CategoryResponse)
def create_category(
    category_in: CategoryCreate,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    new_category = Category(
        name=category_in.name, description=category_in.description
    )
    session.add(new_category)
    session.commit()
    session.refresh(new_category)
    return new_category
