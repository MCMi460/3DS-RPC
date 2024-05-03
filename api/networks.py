from enum import IntEnum
from api.public import nintendoBotFC, pretendoBotFC

# Selectable networks
class NetworkIDsToName(IntEnum):
	nintendo = 0
	pretendo = 1
	
def getBotFriendCodeFromNetworkId(network:int):
    match network:
        case 0:
            return nintendoBotFC
        case 1:
            return pretendoBotFC

def nameToNetworkId(network:int):
    if network == None:
        network = 0
    else:
        try:
            network = NetworkIDsToName[network].value
        except:
            network = 0
    return network