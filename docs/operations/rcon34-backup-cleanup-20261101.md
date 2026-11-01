# RCON3/4 backup cleanup — November 1, 2026

Completed on the shared host `87.106.112.21` at **14:05 Europe/Berlin**.
This was a storage-maintenance operation; no application rollout occurred.

## Removed and retained

Removed **58 explicitly inventoried historical backup files**:

| Payload | Files |
| --- | ---: |
| PostgreSQL dumps | 39 |
| Redis snapshots | 8 |
| Archived application images | 11 |

The files occupied **85,852,766,208 bytes (79.96 GiB)**, accounting for two
hard-linked dump pairs only once. The new verified backup occupies
**4,434,332,576 bytes**, making the cleanup's net storage reduction approximately
**81.4 GB (75.83 GiB)** after retaining the new backup.

Actual free-space increase across the deletion step was 85,852,749,824 bytes,
consistent with the inventory. The host had approximately **440.2 GB free**
after final verification. Changes in host-wide free space before the deletion
step are not attributed to this cleanup.

Kept unchanged:

- All backups dated October 18 onward, including those before the 0.9.3 pilot,
  playtime repairs, and recent report/AI hotfixes.
- The complete backup set from the v0.9.2 deployment.
- 23 protected database, Redis and image archives in the inspected main backup
  roots, verified against their original file metadata.
- Active Compose files, bind-mounted data and configuration; historical
  configuration archives and deployment metadata were also retained.
- Shared Discord-service backups, unclear archives, old installation/database
  copies, other hosted applications and test databases.

Only listed regular files were unlinked. There was no recursive directory
deletion, Docker image/volume pruning, live-database deletion or service restart.
Every path was checked against Docker mount and Compose references, resolved
paths, age, original size/inode/mtime and known archive signatures. Each affected
directory contains a `BACKUP-CLEANUP-20261101.txt` note pointing to the manifest.

## Current backup and recovery verification

Private host directory:
`/root/hll_rcon_tool/.deploy-state/backup-cleanup-20261101`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `configuration.tar.gz` | 55,411 | `40cd162ed7a315dec5659ae30dc35ccc6a37cb44565e3873ed7e1e49b6dfd9b7` |
| `postgres-globals.sql` | 381 | `51da166a1d03cbef9d1771e14fd20f8b0b3804474cf4070680e9bc9a0876762a` |
| `rcon.dump` | 3,638,367,257 | `03c3a5712f0dd4758a856715dae711548df1a6598f9fe123dd5d37d10e4715f1` |
| `postgres.dump` | 1,037 | `2998fb640a96ecd018f529cf18158ac9469449627be4821beea9147bbd33865e` |
| `redis.rdb` | 113,815,434 | `73a7f1a7afbbe7e8c50d06eedf1dc23471db88629b18e9770c546cb63c6e1a51` |
| `current-images.tar` | 682,093,056 | `65c4ebe46ba9792e3f7d7bd70a642bbd449a564a42611138c99c9dd476217173` |

Validation completed **before** deletion:

- Both PostgreSQL archives passed table-of-contents checks and full decoding.
- Both databases were restored with roles, ownership and permissions into an
  isolated PostgreSQL container using the production database image, with no
  network or production mounts and a 2-CPU/2-GiB resource limit.
- The restored application database contained all 73 public tables, occupied
  20,884,939,631 bytes, and passed queries against configuration, users and
  incidents. The restored `postgres` database contained no public tables.
- Redis passed `redis-check-rdb`; configuration archive entries matched source
  hashes; the image archive was fully read and contained both current images.
- All backup hashes were rechecked. The temporary restore container and its
  newly created anonymous volume were removed and verified absent.

The private `state.json` contains the exact plan, retained-file fingerprints,
runtime snapshot references and checks. `removed-files.jsonl` records each
deleted file. Configuration and runtime inspection data containing credentials
remain restricted on the host and are not included in this document.

Eight legacy Compose paths referenced by existing container labels were already
missing before this work. Their absence is recorded in the private state; all
existing configuration files and the exact runtime definitions were backed up.
No configuration file was removed by this operation.

## Final checks

All original RCON container IDs, image IDs, running states and start times were
unchanged. Configuration hashes and retained-backup fingerprints matched.
RCON3 and RCON4 backends were healthy, and both `/api/get_version` endpoints
returned HTTP 200 with `failed: false` and version `v0.9.3-rc.1`.

Deleted historical archives are no longer available. The fresh verified backup
and retained recent rollback sets provide the remaining recovery points.
