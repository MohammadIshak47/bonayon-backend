"""Ownership is enforced HERE: a farm/plot belonging to someone else raises ForbiddenError (403)."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import Farm, Plot, User
from app.utils.pagination import paginate


def get_owned_farm(db: Session, farm_id: uuid.UUID, user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise NotFoundError("Farm not found")
    if farm.user_id != user.id:
        raise ForbiddenError("You do not have access to this farm")
    return farm


def get_owned_plot(db: Session, plot_id: uuid.UUID, user: User) -> Plot:
    plot = db.get(Plot, plot_id)
    if plot is None:
        raise NotFoundError("Plot not found")
    get_owned_farm(db, plot.farm_id, user)  # ownership is transitive through the farm
    return plot


def list_farms(db: Session, user: User, page: int, size: int):
    return paginate(db, select(Farm).where(Farm.user_id == user.id).order_by(Farm.created_at.desc()), page, size)


def list_plots(db: Session, farm: Farm) -> list[Plot]:
    return list(db.scalars(select(Plot).where(Plot.farm_id == farm.id).order_by(Plot.created_at)))


def counts(db: Session, user: User) -> tuple[int, int]:
    farms = db.scalar(select(func.count()).select_from(Farm).where(Farm.user_id == user.id)) or 0
    plots = db.scalar(select(func.count()).select_from(Plot).join(Farm, Plot.farm_id == Farm.id).where(Farm.user_id == user.id)) or 0
    return farms, plots
