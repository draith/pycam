#!/bin/bash
echo ${1:0:64} > base64.txt
echo ${1:64} >> base64.txt
openssl enc -in base64.txt -out bintext -d -a
openssl rsautl -decrypt -in bintext -out plaintext -inkey key.pem
cat plaintext