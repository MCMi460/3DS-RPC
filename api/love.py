# Convert `friendCode` into `principalId`

# This method took two weeks to figure out and five minutes to code
# Thank you, https://www.3dbrew.org/wiki/Principal_ID
# for essentially making my efforts have worth
# I would kiss Meleemeister (https://www.3dbrew.org/wiki/Special:Contributions/Meleemeister)

import hashlib

class FriendCodeValidityError(Exception):
    pass

def convertFriendCodeToPrincipalId(friendCode:str) -> int:
    checksumPrincipal = str(hex(int(friendCode.replace('-','')))) # Convert friendCode into hexadecimal
    principalId = int(checksumPrincipal[4:], 16) # Remove most significant byte and convert to integer
    checksumByte = hex(int(checksumPrincipal[2:][:2], 16)) # Separate checksum from checksumPrincipal
    if not checkPrincipalIdValidity(checksumByte, principalId): raise FriendCodeValidityError('\'%s\' is an invalid friend code' % friendCode)
    return principalId

def checkPrincipalIdValidity(checksumByte:int, principalId:int) -> bool:
    sha1 = hashlib.sha1(principalId.to_bytes(16, 'little')) # Little endian sha1 of principalId
    return hex(int(sha1.hexdigest()[2:][:2], 16) >> 1) == checksumByte # Check to match

# Structure of a friendCode:
#
# (0x__ << 32) | 0x________
#   Checksum     PrincipalID
#
