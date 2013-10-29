#!/bin/bash
# Argument = -a alias -k keystore -p password

usage()
{
cat << EOF
usage: $0 [-k keystore -a alias]

Use to get your keystore's base64 signature

OPTIONS:
   -h      Show this message
   -a      The alias in the keystore
   -k      Keystore

Defaults to -k ~/.android/debug.keystore -a androidebugkey
EOF
}

ALIAS=
KEYSTORE=
VERBOSE=
while getopts “ha:k:v” OPTION
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         a)
             ALIAS=$OPTARG
             ;;
         k)
             KEYSTORE=$OPTARG
             ;;
         v)
             VERBOSE=1
             ;;
         ?)
             usage
             exit
             ;;
     esac
done

# must be some alias set.  are we just getting the debug?
if [[ -z $ALIAS ]] && [[ -z $KEYSTORE ]]
then
    ALIAS=androiddebugkey
fi

if [[ $KEYSTORE ]] && [[ -z $ALIAS ]]
then
    usage
    exit
fi

if [[ -z $KEYSTORE ]]
then
    KEYSTORE=~/.android/debug.keystore
    echo "Getting default signature"
    echo HINT: "'android'"
fi


ALIAS_OPTION="-alias $ALIAS"

OUT=$(mktemp /tmp/output.XXXXXXXXXXX || {echo "Failed to create file"})
keytool -exportcert $ALIAS_OPTION -keystore $KEYSTORE > $OUT

if  [ $? -eq 0 ]
then 
    openssl sha1 -binary < $OUT | openssl base64 
else
    echo $CERT
fi
