# Created by Deltaion Lee (MCMi460) on Github
# This is my private file, but with all of the dangerous stuff removed
# You can use it as a template for yours

SERIAL_NUMBER = "" # Serial number on console minus the last digit
MAC_ADDRESS = "" # Console MAC address (see WiFi settings), all lowercase with no colons
DEVICE_CERT = bytes.fromhex("") # Unique console certificate. Get from sniffing traffic
DEVICE_NAME = "" # Doesn't matter

# 3DS does NOT send NEX credentials over NASC
# They are generated once when the account is created and stored on the device
# Homebrew like https://github.com/Stary2001/nex-dissector/tree/master/get_3ds_pid_password
# can be used to dump the PID and password
PID = 0
PID_HMAC = "" # Sniff console traffic or dump from friends title save (bytes 66-84)

NEX_PASSWORD = ""

REGION = 1 # USA
LANGUAGE = 1 # English
