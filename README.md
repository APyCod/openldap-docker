[![CI & GHCR Publish](https://github.com/APyCod/openldap-docker/actions/workflows/ci.yml/badge.svg)](https://github.com/APyCod/openldap-docker/actions/workflows/ci.yml)

# docker ldap

This project sets up OpenLDAP (2.6) in an Alpine Docker container (`ldaps://` on port `636`, `{ARGON2}` password hashing, `memberof`, `refint` and `ppolicy` overlays).

It provides a default ACL & directory layout and includes a pytest integration suite ([tests/src/tests](tests/src/tests)) runnable via `./tests/run_test.sh`.

It's probably easier for you to fork this repo if you don't like those settings but like how it's administered and tested.

## Quick Start

Requirements:

- DNS pointing to your LDAP server (e.g. **ldap.example.org**)
- A TLS certificate and private key for that domain (`ldap.example.org.crt` and `ldap.example.org.key`), readable by UID/GID `666` (`ldap:ldap` inside the container).

Then:

* First run only: initialize LDAP configuration (`/etc/openldap/slapd.d`) and base tree (`/var/lib/openldap/openldap-data`).
* Restart server, test, add users/groups/applications.
* Connect your services over `ldaps://` (TLS >= 1.2 enforced).

## Configuration (Environment Variables)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DOMAIN` | `example.com` | Root LDAP domain (`dc=example,dc=com`) |
| `ORGANIZATION` | `Example corporation` | Organization name (`o`) |
| `LDAP_SUB_DOMAIN` | `ldap` | Subdomain used for default cert/key paths |
| `LDAP_ROOT_PASSWORD` | Random `{ARGON2}` | Password hash for `cn=admin,<ROOT_DC>` |
| `LDAP_DEFAULT_ADMIN_UID` | `administrator` | Default admin user under `ou=people` |
| `LDAP_DEFAULT_ADMIN_PASSWORD` | Random `{ARGON2}` | Password hash for default admin user |
| `LDAP_CA_CERTIFICATE_PATH` | `false` | Optional CA certificate path |
| `LDAP_CERTIFICATE_PATH` | `/ssl/<sub_domain>.<domain>.crt` | Server TLS certificate path |
| `LDAP_CERTIFICATE_KEY_PATH` | `/ssl/<sub_domain>.<domain>.key` | Server TLS private key path |
| `LDAP_TLS_VERIFY_CLIENT` | `never` | `olcTLSVerifyClient` (`never`, `allow`, `try`, `demand`) |
| `LDAP_TLS_CIPHER_SUITE` | `DEFAULT` | `olcTLSCipherSuite` |
| `LDAP_PPOLICY_SAFE_MODIFY` | `FALSE` | Require old password on `userPassword` modify (`TRUE`/`FALSE`). Keep `FALSE` if non-root `ldap_people_admin` accounts (e.g. Authelia) reset user passwords |
| `LDAP_LOG_LEVEL` | `64` | `slapd` debug/log level |

## Default LDAP Configuration

If you configure `DOMAIN=example.com`, you get the following tree:

```text
dc=com
├── dc=example
│   ├── cn=admin                  # Root LDAP account (bypasses ACLs)
│   ├── ou=people                 # Physical users
│   │   ├── uid=administrator     # Default user administrator
│   │   ├── uid=user 1
│   │   └── uid=user n
│   ├── ou=groups                 # Group definitions
│   │   ├── cn=ldap_people_admin  # LDAP people & regular groups administrators
│   │   ├── cn=ldap_apps_admin    # LDAP applications administrators
│   │   ├── cn=group 1
│   │   └── cn=group n
│   ├── ou=applications           # Application/service accounts
│   │   ├── uid=app 1
│   │   └── uid=app n
│   ├── ou=policies               # Password policies (ppolicy)
│   │   └── cn=default
```

### Roles & Permissions

* **Anonymous**: can only authenticate (`auth` on `userPassword`); no read/search access.
* **User account** (`ou=people,dc=example,dc=com`): can read their own entry and change their own password (`userPassword` is write/auth only, not readable); cannot read or modify other users.
* **LDAP people administrator** (member of `cn=ldap_people_admin,ou=groups,dc=example,dc=com`):
  * Create, read, and update entries under `ou=people` (including resetting passwords).
  * Create and manage regular groups under `ou=groups` (cannot modify `cn=ldap_apps_admin`, preventing cross-privilege escalation).
  * Read `ou=policies` and `dc=example,dc=com`.
* **LDAP applications administrator** (member of `cn=ldap_apps_admin,ou=groups,dc=example,dc=com`):
  * Create, read, and update service accounts under `ou=applications` and manage `cn=ldap_apps_admin` membership.
* **LDAP root account** (`cn=admin,dc=example,dc=com`): full unrestricted access; intended for automated deployments and `cn=config` migrations.
* **Application accounts** (`ou=applications,dc=example,dc=com`):
  * Can read groups under `ou=groups` and `memberOf` attributes.
  * Can read only basic identity attributes (`entry`, `objectClass`, `uid`, `cn`, `sn`, `givenName`, `displayName`, `mail`, `o`, `ou`) on `ou=people` (restricted attributes such as `mobile` or `userPassword` are denied unless the app is also in `ldap_people_admin`).

### Default Password Policy (`ppolicy`)

- Minimum length: `12` characters (`pwdMinLength: 12`)
- History: `5` passwords (`pwdInHistory: 5`)
- Lockout: `5` failed attempts within `300` seconds locks the account for `300` seconds (`pwdLockout: TRUE`)
- `pwdSafeModify`: `FALSE` by default (configurable via `LDAP_PPOLICY_SAFE_MODIFY`)

## Persistent Data & Upgrades

OpenLDAP configuration (`/etc/openldap/slapd.d`) and user data (`/var/lib/openldap/openldap-data`) are stored in persistent volumes.
Existing volumes are **not** overwritten when upgrading the container image; apply `cn=config` or `ppolicy` changes manually via `ldapmodify` as documented in [CHANGELOG.md](CHANGELOG.md).

## Running Tests

```bash
./tests/run_test.sh
```

Use `./tests/run_test.sh -k` to keep the test LDAP container running on port `636` after tests complete.

## Tips

### Generate a password hash (`{ARGON2}`)

You can generate `{ARGON2}` password hashes for `LDAP_ROOT_PASSWORD`, `LDAP_DEFAULT_ADMIN_PASSWORD`, or LDIF files using `slappasswd` from this image:

```bash
docker run -it --rm --entrypoint slappasswd ghcr.io/apycod/openldap-docker \
  -o module-path=/usr/lib/openldap -o module-load=argon2.so -h "{ARGON2}" -s MySecrets
```
