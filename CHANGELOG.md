# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- GitHub Actions workflow ([.github/workflows/ci.yml](.github/workflows/ci.yml)): runs unit tests on push/PR and publishes monthly uncached builds to GitHub Container Registry (`ghcr.io/apycod/openldap-docker`).
- [ROADMAP.md](ROADMAP.md) tracking identified security improvements and operational fixes.
- Unit tests in [test_ldap_update_entries.py](tests/src/tests/test_ldap_update_entries.py) verifying privilege isolation between `cn=ldap_people_admin` and `cn=ldap_apps_admin`.
- Unit test in [test_ldap_search_entries.py](tests/src/tests/test_ldap_search_entries.py) verifying that application accounts can only read basic identity attributes on `ou=people` (and cannot read restricted attributes such as `mobile`).
- Argon2 password hashing (`openldap-passwd-argon2` / `argon2.so`) with `olcPasswordHash: {ARGON2}` on `olcDatabase=frontend,cn=config` and unit test `test_password_hashed_with_argon2` in [test_ldap_update_entries.py](tests/src/tests/test_ldap_update_entries.py).
- Unit test `test_default_policy_min_length_and_safe_modify` in [test_ldap_ppolicy_overlay.py](tests/src/tests/test_ldap_ppolicy_overlay.py).

### Changed
- **Security (`ppolicy`)**: hardened default password policy in [base/01_policies.ldif.template.sh](base/01_policies.ldif.template.sh) (`pwdMinLength: 12`, `pwdFailureCountInterval: 300`, `pwdLockoutDuration: 300`, `pwdSafeModify: TRUE`).
- **Security (TLS)**: hardened TLS defaults in [etc/slapd.ldif.template.sh](etc/slapd.ldif.template.sh) (`olcTLSProtocolMin: 3.3`, `olcSecurity: tls=1`), fixed missing `S:` in `getopts`, and exposed `LDAP_TLS_VERIFY_CLIENT` (`-V`) and `LDAP_TLS_CIPHER_SUITE` (`-S`) in [entrypoint.sh](entrypoint.sh).
- **Security (ACLs)**:
  - Added `olcAccess: {290}` and updated `{300}` in [etc/lmdb.ldif.template.sh](etc/lmdb.ldif.template.sh) so `ou=applications` accounts can only read basic identity attributes (`entry`, `objectClass`, `uid`, `cn`, `sn`, `givenName`, `displayName`, `mail`, `o`, `ou`) on `ou=people` (in addition to `memberOf` via `{200}`).
  - Added `olcAccess: {390}` in [etc/lmdb.ldif.template.sh](etc/lmdb.ldif.template.sh) to prevent members of `cn=ldap_people_admin` from modifying `cn=ldap_apps_admin` (privilege escalation). Members of `cn=ldap_people_admin` retain read access.
- **Security (`entrypoint.sh`)**:
  - `LDAP_DEFAULT_ADMIN_PASSWORD` no longer defaults to `"Change Me!"`; a random password is generated if unset.
  - Removed printing `/etc/openldap/slapd.ldif` to container logs and deleted the temporary file after `slapadd`.
  - Hardened random password generation (shell-safe characters and proper quoting in `slappasswd`).

### Fixed
- Non-TTY environment support in [tests/run_test.sh](tests/run_test.sh) for CI execution.

### Migration notes (existing production instances)
Existing instances using a persistent `/etc/openldap/slapd.d` volume keep their current ACLs when upgrading the image.
To apply the `cn=ldap_apps_admin` protection on an existing production instance without risk of lockout (using the root account `cn=admin,<ROOT_DC>`), first verify that your application administrators are members of `cn=ldap_apps_admin`, then apply via `ldapmodify`:

```ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcAccess
olcAccess: {390}to dn.exact="cn=ldap_apps_admin,ou=groups,dc=example,dc=com" by group.exact="cn=ldap_apps_admin,ou=groups,dc=example,dc=com" write by group.exact="cn=ldap_people_admin,ou=groups,dc=example,dc=com" read by dn.one="ou=applications,dc=example,dc=com" read by * none
```
*(Replace `dc=example,dc=com` with your `ROOT_DC`.)*

To enable `{ARGON2}` on an existing production instance (existing `{SSHA}` passwords continue to authenticate normally and are upgraded to `{ARGON2}` on next password change):

```ldif
dn: cn=module{0},cn=config
changetype: modify
add: olcModuleLoad
olcModuleLoad: argon2.so

dn: olcDatabase={-1}frontend,cn=config
changetype: modify
add: olcPasswordHash
olcPasswordHash: {ARGON2}
```

To harden the default `ppolicy` on an existing production instance:

```ldif
dn: cn=default,ou=policies,dc=example,dc=com
changetype: modify
replace: pwdMinLength
pwdMinLength: 12
-
replace: pwdFailureCountInterval
pwdFailureCountInterval: 300
-
replace: pwdLockoutDuration
pwdLockoutDuration: 300
-
replace: pwdSafeModify
pwdSafeModify: TRUE
```

To harden TLS on an existing production instance:

```ldif
dn: cn=config
changetype: modify
replace: olcTLSProtocolMin
olcTLSProtocolMin: 3.3
-
replace: olcSecurity
olcSecurity: tls=1
```
