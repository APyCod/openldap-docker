#!/bin/sh

set -e

USAGE="Usage: $0 -D Root LDAP DC [-S TRUE|FALSE] [-h]

Template to generate policies config file

Options:
    -D ROOT LDAP DC     The root ldap dc, should looks like dc=example,dc=com
    -S SAFE MODIFY      Require old password on modify (default: FALSE)
    -h                  Show this help.
"

SAFE_MODIFY=${LDAP_PPOLICY_SAFE_MODIFY:-FALSE}

while getopts "D:S:h" OPTION
do
    case $OPTION in
        D) ROOT_LDAP_DC=$OPTARG;;
        S) SAFE_MODIFY=$OPTARG;;
        h) echo "$USAGE";
           exit;;
        *) echo "Ignore unknown parameter while generating policies
                 ldif template" >&2;;
    esac
done

if [[ ! $ROOT_LDAP_DC ]]; then
    echo "Root LDAP DC is required while generating policies ldif template" >&2
    exit 1
fi

cat << EOF

# https://linux.die.net/man/5/slapo-ppolicy
# https://www.openldap.org/doc/admin26/overlays.html#Password%20Policies
dn: cn=default,ou=policies,$ROOT_LDAP_DC
objectClass: pwdPolicy
objectClass: person
objectClass: top
cn: default
sn: Default password policy
pwdAllowUserChange: TRUE
pwdAttribute: userPassword
pwdCheckQuality: 1
pwdExpireWarning: 600
pwdFailureCountInterval: 300
pwdGraceAuthNLimit: 5
pwdInHistory: 5
pwdLockout: TRUE
pwdLockoutDuration: 300
# This attribute contains the number of seconds after which a modified password
# will expire. If this attribute is not present, or if its value is zero (0),
# then passwords will not expire.
pwdMaxAge: 0
pwdMaxFailure: 5
pwdMinAge: 0
pwdMinLength: 12
# If set to TRUE this make possible to ask user to change password while
# they connect the first time the matter is to make sure we have tool that
# can handle this behaviour
pwdMustChange: FALSE
# Keep FALSE by default so non-root admins (e.g. Authelia in ldap_people_admin)
# can reset user passwords without knowing the old password.
# Configurable via LDAP_PPOLICY_SAFE_MODIFY (or -S).
pwdSafeModify: $SAFE_MODIFY

EOF