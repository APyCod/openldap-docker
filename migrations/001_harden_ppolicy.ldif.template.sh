#!/bin/sh

set -e

USAGE="Usage: $0 -D Root LDAP DC [-h]

Migration 001: Harden default ppolicy settings (pwdMinLength, lockout)

Options:
    -D ROOT LDAP DC     The root ldap dc, should looks like dc=example,dc=com
    -h                  Show this help.
"

while getopts "D:h" OPTION
do
    case $OPTION in
        D) ROOT_LDAP_DC=$OPTARG;;
        h) echo "$USAGE";
           exit;;
        *) ;;
    esac
done

if [[ ! $ROOT_LDAP_DC ]]; then
    echo "Root LDAP DC is required while generating migration 001" >&2
    exit 1
fi

cat << EOF
dn: cn=default,ou=policies,$ROOT_LDAP_DC
changetype: modify
replace: pwdMinLength
pwdMinLength: 12
-
replace: pwdFailureCountInterval
pwdFailureCountInterval: 300
-
replace: pwdLockoutDuration
pwdLockoutDuration: 300
EOF
