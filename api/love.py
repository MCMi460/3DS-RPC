# Created by Deltaion Lee (MCMi460) on Github
# Convert `friendCode` into `principalId`

# This method took two weeks to figure out and five minutes to code
# Thank you, https://www.3dbrew.org/wiki/Principal_ID
# for essentially making my efforts have worth
# I would kiss Meleemeister (https://www.3dbrew.org/wiki/Special:Contributions/Meleemeister)

import hashlib

class FriendCodeValidityError(Exception):
    pass

class PrincipalIDValidityError(Exception):
    pass

def convertFriendCodeToPrincipalId(friendCode:str) -> int:
    friendCode = ''.join(filter(str.isdigit, str(friendCode)))
    if len(friendCode) != 12: raise FriendCodeValidityError('an invalid friend code was passed') # Remove chances of friendCode being invalid
    checksumPrincipal = str(hex(int(friendCode))) # Convert friendCode into hexadecimal
    principalId = int(checksumPrincipal[4:], 16) # Remove most significant byte and convert to integer
    checksumByte = hex(int(checksumPrincipal[2:][:2], 16)) # Separate checksum from checksumPrincipal
    if not checkPrincipalIdValidity(checksumByte, principalId): raise FriendCodeValidityError('an invalid friend code was passed')
    return principalId

def checkPrincipalIdValidity(checksumByte:int, principalId:int) -> bool:
    return generateChecksumByte(principalId) == checksumByte # Check to match

def generateChecksumByte(principalId:int) -> str: # https://www.3dbrew.org/wiki/FRDU:PrincipalIdToFriendCode
    sha1 = hashlib.sha1(principalId.to_bytes(4, byteorder = 'little')) # Little endian sha1 of principalId
    return hex(int(sha1.hexdigest()[:2], 16) >> 1) # Shift first byte to the right by one

def convertPrincipalIdtoFriendCode(principalId:int) -> int:
    if not isinstance(principalId, int): raise PrincipalIDValidityError('an invalid principal id was passed')
    checksumByte = generateChecksumByte(principalId)
    friendCode = checksumByte + hex(principalId)
    return int(friendCode.replace('0x',''), 16)

# Structure of a friendCode:
#
# (0x__ << 32) | 0x________
#   Checksum     PrincipalID
#
