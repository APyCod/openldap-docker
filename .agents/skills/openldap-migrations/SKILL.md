---
name: openldap-migrations
description: >-
  Guidelines on when to create a database migration script in migrations/ vs
  relying on stateless slapd.d config rebuilds in this OpenLDAP Docker repo.
---

# OpenLDAP Docker Migrations Guide

## Core Architecture

- **`/etc/openldap/slapd.d` (`cn=config`) is stateless by default**: it is NOT declared as a `VOLUME` in `Dockerfile` and is rebuilt from `etc/*.ldif.template.sh` on container startup whenever `/etc/openldap/slapd.d/cn=config` is absent.
- **`/var/lib/openldap` (`data.mdb`) is persistent**: user entries, groups, applications, and `ppolicy` entries (`ou=policies`) live here.
- `entrypoint.sh` tracks the deployed image version in `/var/lib/openldap/.image_version` and the last applied migration number in `/var/lib/openldap/.migration_version`.

## When a Migration Script IS Required

Create a migration script in `migrations/NNN_<description>.ldif.template.sh` whenever a change affects entries stored in **`data.mdb`** (`/var/lib/openldap/openldap-data`), including:
- Changes to `base/01_policies.ldif.template.sh` (default `ppolicy` attributes under `cn=default,ou=policies,<ROOT_DC>`).
- Changes to `base/00_organization.ldif.template.sh` (new default OUs, default groups, or structural data entries).

### Rules for Writing Migration Scripts
1. Name the file `migrations/NNN_short_description.ldif.template.sh` (zero-padded 3-digit prefix, e.g. `002_...`).
2. Make it executable (`chmod +x`) and accept `-D ROOT_LDAP_DC` via `getopts` (matching `migrations/001_harden_ppolicy.ldif.template.sh`).
3. Output valid LDIF with `changetype: modify` (executed offline via `slapmodify`).
4. Prefer `replace:` over `add:` so migrations remain idempotent even on existing production databases without `.migration_version`.
5. Also update `base/` so fresh installations start with the new state directly (fresh installations skip `migrations/` and record the latest migration number).

## When a Migration Script is NOT Required

Do **not** create a `migrations/` script for:
- ACL changes (`etc/lmdb.ldif.template.sh`)
- Module/schema/TLS changes (`etc/slapd.ldif.template.sh`)
- Overlay config changes (`etc/overlay_settings.ldif.template.sh`)

These live in `cn=config` (`/etc/openldap/slapd.d`), which is automatically rebuilt when not mounted as a volume. If you add a new `olcDbIndex` in `etc/lmdb.ldif.template.sh`, `entrypoint.sh` automatically runs `slapindex` when `data.mdb` already exists.
