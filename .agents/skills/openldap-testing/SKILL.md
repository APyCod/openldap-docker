---
name: openldap-testing
description: >-
  How to run the OpenLDAP Docker integration/unit test suite and when to add
  new unit tests for LDAP ACLs, overlays, schemas, or entrypoint changes.
---

# OpenLDAP Docker Testing Guide

## Running the Test Suite

Run the full test suite from the repository root:

```bash
./tests/run_test.sh
```

What `tests/run_test.sh` does:
1. Cleans up any leftover test containers, volumes, and networks (`CI_ldap`, `CI_test_ldap`, `CI_ldap_certificat`, `net_ci_ldap`).
2. Builds the OpenLDAP Docker image from `Dockerfile`.
3. Builds the Python/pytest test runner image from `tests/Dockerfile`.
4. Generates a self-signed CA and server certificate in a temporary Docker volume (`tests/certificate/Dockerfile`).
5. Starts the `slapd` container on `ldaps://` and runs `pytest -s -vvv tests/` inside the test container.

Useful options:
- `./tests/run_test.sh -k` : keeps the LDAP container running after tests and exposes port `636` for manual inspection.
- In CI / non-TTY environments, `run_test.sh` automatically omits `-it` from `docker run`.

## When to Add Unit Tests

Always add or update unit tests in `tests/src/tests/` when making changes in any of the following areas:

1. **ACL changes (`etc/lmdb.ldif.template.sh`)**:
   - Any addition, modification, or reordering of `olcAccess` rules.
   - Verify permissions across **all** 10 roles defined in `LdapTestCase.setUpClass` (`anonymous`, `user`, `user-people-admin`, `user-apps-admin`, `user-admin`, `admin`, `app`, `app-people-admin`, `app-apps-admin`, `app-admin`) using `self.run_case(...)`.
   - Test both positive access (`assertTrue`) and negative/denied access (`assertFalse`), including attribute-level restrictions when applicable.

2. **Overlays & Password Policies (`etc/overlay_settings.ldif.template.sh`, `base/01_policies.ldif.template.sh`)**:
   - Changes to `memberof`, `refint`, or `ppolicy` settings (see `test_ldap_memberof_overlay.py` and `test_ldap_ppolicy_overlay.py`).

3. **Default Tree & Entrypoint (`base/00_organization.ldif.template.sh`, `entrypoint.sh`)**:
   - Changes to default OUs, admin groups, TLS settings, or initialization behavior (see `test_ldap_connections.py`).

## Conventions for Writing New Tests

- Inherit from `LdapTestCase` (in `tests/src/tests/features.py`).
- Use `uuid4()` for temporary DNs and register cleanup with `self.addCleanup(...)` so tests remain isolated and idempotent.
- Place tests in the matching module:
  - `test_ldap_search_entries.py` (read/search ACLs)
  - `test_ldap_create_entries.py` (add ACLs)
  - `test_ldap_update_entries.py` (modify ACLs)
  - `test_ldap_delete_entries.py` (delete ACLs)
  - `test_ldap_rename_entries.py` (moddn/rename ACLs)
  - `test_ldap_memberof_overlay.py` / `test_ldap_ppolicy_overlay.py` / `test_ldap_connections.py`
