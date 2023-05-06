# Created by Deltaion Lee (MCMi460) on Github
# This is my private file, but with all of the dangerous stuff removed
# You can use it as a template for yours

SERIAL_NUMBER:str = "" # Serial number on console minus the last digit
MAC_ADDRESS:str = "" # Console MAC address (see WiFi settings), all lowercase with no colons
DEVICE_CERT:bytes = bytes.fromhex("") # Unique console certificate. Get from sniffing traffic
DEVICE_NAME:str = "" # Doesn't matter

# 3DS does NOT send NEX credentials over NASC
# They are generated once when the account is created and stored on the device
# Homebrew like https://github.com/Stary2001/nex-dissector/tree/master/get_3ds_pid_password
# can be used to dump the PID and password
PID:int = 0
PID_HMAC:str = "" # Sniff console traffic or dump from friends title save (bytes 66-84)

NEX_PASSWORD:str = ""

REGION:int = 1 # USA
LANGUAGE:int = 1 # English

#########################
# Now, Discord secrets! #
# Keep in mind that you #
# will need the scope:  #
# activities.write in   #
# order to replicate    #
# this step.            #
CLIENT_ID:int = 0 # Taken from OAuth2 page
CLIENT_SECRET:str = "" # Taken from OAuth2 page

#### SERVER-SPECIFIC ####
# Finally, we're grabbing #
# server-specific things. #
# This mostly only        #
# pertains to the domain. #
# See format below  \/    #
HOST:str = ""
# http(s)://subdomain.domain.extension
# No ending slash!
