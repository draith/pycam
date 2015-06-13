#!/bin/bash
# Input arg = base64-encoded ssl-encrypted command.  
# Result: decrypted command in plaintext file.  Using private key in key.pem
# First, split the base64 into 64-char lengths.
echo ${1:0:64} > base64.txt
echo ${1:64} >> base64.txt
# Convert to binary encrypted string.
openssl enc -in base64.txt -out bintext -d -a
openssl rsautl -decrypt -in bintext -out plaintext -inkey key.pem
