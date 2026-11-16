# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- GitHub Actions workflow ([.github/workflows/ci.yml](.github/workflows/ci.yml)): runs unit tests on push/PR and publishes monthly uncached builds to GitHub Container Registry (`ghcr.io/apycod/openldap-docker`).
- [ROADMAP.md](ROADMAP.md) tracking identified security improvements and operational fixes.
- Unit tests in [test_ldap_update_entries.py](tests/src/tests/test_ldap_update_entries.py) verifying privilege isolation between `cn=ldap_people_admin` and `cn=ldap_apps_admin`.

### Changed
- **Security (ACLs)**: added `olcAccess: {390}` in [etc/lmdb.ldif.template.sh](etc/lmdb.ldif.template.sh) to prevent members of `cn=ldap_people_admin` from modifying `cn=ldap_apps_admin` (privilege escalation). Members of `cn=ldap_people_admin` retain read access.
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
