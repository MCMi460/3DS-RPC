import os

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from sqlalchemy.types import Integer
import sys

sys.path.append('../')
from api.networks import NetworkType


class Base(DeclarativeBase):
    pass


class Config(Base):
    __tablename__ = "config"

    network: Mapped[NetworkType] = mapped_column("network", Integer(), primary_key=True)
    backend_uptime: Mapped[float] = mapped_column("BACKEND_UPTIME")


def start_db_time(time: float, network_type: NetworkType):
    """Updates the database to track the starting time for the specific backend."""
    engine = create_engine('sqlite:///' + os.path.abspath('sqlite/fcLibrary.db'))
    with Session(engine) as session:
        # TODO: This should be an upsert, not a deletion and insertion.
        session.execute(delete(Config).where(Config.network == network_type))
        new_time = Config(network=network_type, backend_uptime=time)
        session.add(new_time)
        session.commit()
