from enum import IntEnum
from api.public import nintendoBotFC, pretendoBotFC


class InvalidNetworkError(Exception):
    pass


class NetworkType(IntEnum):
    """Selectable network types."""
    NINTENDO = 0
    PRETENDO = 1

    def friend_code(self) -> str:
        """Returns the configured friend code for this network type."""
        match self:
            case self.NINTENDO:
                return nintendoBotFC
            case self.PRETENDO:
                return pretendoBotFC

    def column_name(self) -> str:
        """Returns the database column name for this network type."""
        match self:
            case self.NINTENDO:
                return "nintendo_friends"
            case self.PRETENDO:
                return "pretendo_friends"

    def lower_name(self) -> str:
        """Returns a lowercase name of this enum member's name for API compatibility."""
        return self.name.lower()


def nameToNetworkType(network_name: str) -> NetworkType:
    # Assume Nintendo Network as a fallback.
    if network_name is None:
        return NetworkType.NINTENDO

    try:
        # All enum members are uppercase, so ensure we are, too.
        return NetworkType[network_name.upper()]
    except:
        return NetworkType.NINTENDO
