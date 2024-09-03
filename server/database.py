import datetime
from typing import Optional

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session
from sqlalchemy.types import DateTime, Integer, TypeDecorator
import sys

sys.path.append('../')
from api.networks import NetworkType
from api.private import DB_URL


class Base(DeclarativeBase):
    pass


class Config(Base):
    __tablename__ = "config"

    network: Mapped[NetworkType] = mapped_column("network", Integer(), primary_key=True)
    backend_uptime: Mapped[datetime.datetime] = mapped_column("backend_uptime", DateTime())


class NetworkTypeValue(TypeDecorator):
    impl = Integer

    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if isinstance(value, NetworkType):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return NetworkType(value)
        return value


class Friend(Base):
    __tablename__ = "friends"

    friend_code: Mapped[str] = mapped_column("friend_code", primary_key=True, nullable=False, unique=True)
    network: Mapped[NetworkType] = mapped_column("network", NetworkTypeValue())
    online: Mapped[bool]
    title_id: Mapped[str] = mapped_column("title_id", nullable=False)
    upd_id: Mapped[str] = mapped_column("upd_id", nullable=False)
    last_accessed: Mapped[int] = mapped_column("last_accessed", nullable=False)
    account_creation: Mapped[int] = mapped_column("account_creation", nullable=False)
    username: Mapped[str]
    message: Mapped[str]
    mii: Mapped[str]
    joinable: Mapped[bool]
    game_description: Mapped[str] = mapped_column("game_description", nullable=False)
    last_online: Mapped[int] = mapped_column("last_online", nullable=False)
    favorite_game: Mapped[int] = mapped_column("jeu_favori", nullable=False)


class DiscordFriends(Base):
    __tablename__ = "discord_friends"

    id: Mapped[int] = mapped_column(primary_key=True)
    friend_code: Mapped[str] = mapped_column("friend_code", primary_key=True, nullable=False)
    network: Mapped[NetworkType] = mapped_column("network", NetworkTypeValue())
    active: Mapped[bool] = mapped_column(nullable=False)


class Discord(Base):
    __tablename__ = "discord"

    id: Mapped[int] = mapped_column("id", primary_key=True, nullable=False, unique=True)
    refresh: Mapped[str] = mapped_column("refresh", nullable=False)
    bearer: Mapped[str] = mapped_column("bearer", nullable=False)
    session: Mapped[str] = mapped_column("session")
    token: Mapped[str] = mapped_column("token", unique=True)
    last_accessed: Mapped[int] = mapped_column("last_accessed", nullable=False)
    generation_date: Mapped[int] = mapped_column("generation_date", nullable=False)
    show_profile_button: Mapped[bool] = mapped_column("show_profile_button", nullable=False, default=True)
    show_small_image: Mapped[bool] = mapped_column("show_small_image", nullable=False, default=True)


def start_db_time(uptime: Optional[datetime.datetime], network_type: NetworkType):
    """Updates the database to track the starting time for the specific backend."""
    engine = create_engine(get_db_url())
    with Session(engine) as session:
        # TODO: This should be an upsert, not a deletion and insertion.
        session.execute(delete(Config).where(Config.network == network_type))
        new_time = Config(network=network_type, backend_uptime=uptime)
        session.add(new_time)
        session.commit()


def get_db_url() -> str:
    return DB_URL
