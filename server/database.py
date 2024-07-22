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


class NintendoFriends(Base):
    __tablename__ = "nintendo_friends"

    friend_code: Mapped[str] = mapped_column("friendCode", primary_key=True, nullable=False, unique=True)
    online: Mapped[bool]
    title_id: Mapped[str] = mapped_column("titleID", nullable=False)
    upd_id: Mapped[str] = mapped_column("updID", nullable=False)
    last_accessed: Mapped[int] = mapped_column("lastAccessed", nullable=False)
    account_creation: Mapped[int] = mapped_column("accountCreation", nullable=False)
    username: Mapped[str]
    message: Mapped[str]
    mii: Mapped[str]
    joinable: Mapped[bool]
    game_description: Mapped[str] = mapped_column("gameDescription", nullable=False)
    last_online: Mapped[int] = mapped_column("lastOnline", nullable=False)
    # "Favorite game"
    jeu_favori: Mapped[int] = mapped_column("jeuFavori", nullable=False)


class PretendoFriends(Base):
    __tablename__ = "pretendo_friends"

    friend_code: Mapped[str] = mapped_column("friendCode", primary_key=True, nullable=False, unique=True)
    online: Mapped[bool]
    title_id: Mapped[str] = mapped_column("titleID", nullable=False)
    upd_id: Mapped[str] = mapped_column("updID", nullable=False)
    last_accessed: Mapped[int] = mapped_column("lastAccessed", nullable=False)
    account_creation: Mapped[int] = mapped_column("accountCreation", nullable=False)
    username: Mapped[str]
    message: Mapped[str]
    mii: Mapped[str]
    joinable: Mapped[bool]
    game_description: Mapped[str] = mapped_column("gameDescription", nullable=False)
    last_online: Mapped[int] = mapped_column("lastOnline", nullable=False)
    # "Favorite game"
    jeu_favori: Mapped[int] = mapped_column("jeuFavori", nullable=False)


class DiscordFriends(Base):
    __tablename__ = "discordFriends"

    id: Mapped[int] = mapped_column(primary_key=True)
    friend_code: Mapped[str] = mapped_column("friendCode", primary_key=True, nullable=False)
    network: Mapped[NetworkType] = mapped_column("network", Integer())
    active: Mapped[bool] = mapped_column(nullable=False)


def start_db_time(time: float, network_type: NetworkType):
    """Updates the database to track the starting time for the specific backend."""
    engine = create_engine('sqlite:///' + os.path.abspath('sqlite/fcLibrary.db'))
    with Session(engine) as session:
        # TODO: This should be an upsert, not a deletion and insertion.
        session.execute(delete(Config).where(Config.network == network_type))
        new_time = Config(network=network_type, backend_uptime=time)
        session.add(new_time)
        session.commit()
