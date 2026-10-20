# Secret audit and history cleanup

## Local cleanup completed — 2026-10-20

The user separately authorized local history rewriting. All five local refs were
cleaned: main, the local origin/main tracking ref and three Codex refs pointing directly
to Git tree objects. The entire airflow/config/airflow.cfg path was removed from their
history/trees. main changed from b3304af9af1968f9a494fff602a91284816cf11c to
84e1fe758320d7b2eb3e98b69ddd354323c2ff57. No new working-change commit was created.

At the end of the rewrite, the sanitized current config remained on disk as an untracked
file. The subsequent authorized source commit includes it. Hash comparisons verified all 87 working files and
every unrelated index entry were preserved. Each ref's resulting tree was checked
against its original tree with only this path excluded. Remote configuration was preserved.
Old local reflog roots were expired and unreachable objects garbage-collected.
git fsck passed; Gitleaks scanned all local commits and reflogs with zero findings.

The verified encrypted recovery archive is
`.codex-build/history-cleanup-20261020T073220Z/recovery.dpapi` (ignored by Git).
It contains the original Git bundle, index, remote configuration, refs and working-file
fingerprints. Windows DPAPI CurrentUser encryption requires this Windows account/profile
to decrypt. Round-trip decryption and actual bundle restoration were verified, including
all five original ref targets and the Codex trees. Earlier encrypted safety copies also
remain in the sibling history-cleanup directories. Treat all recovery copies as sensitive.
Temporary plaintext mirrors from failed protective checks and the previous disposable
README clone's Git database were removed; its source, venvs and test evidence remain.

No push or remote mutation occurred during the local rewrite. The user subsequently
authorized committing and pushing the prepared changes. Remote main was checked against
the expected pre-cleanup tip b3304af9af1968f9a494fff602a91284816cf11c; publication uses
an explicit force-with-lease for that tip and only refs/heads/main. Verify the remote tip
after push. Rewriting does not replace rotation of used keys or remove other people's
clones/hosted cached refs. Collaborators must re-clone to avoid restoring old history.

## Original findings (before the authorized cleanup)

2026-10-20: Gitleaks 8.30.0 scanned all 10 available commits with --all and 100% redaction.
Two generic-api-key findings are real signing-secret configuration, not blank values:
airflow/config/airflow.cfg, introduction commit 1c96df2499c8dc0d34e455e6a097002be67907bb,
old lines 1395 ([api] secret_key) and 1900 ([api_auth] jwt_secret).
The first signs API/web sessions; the second signs task-execution JWTs. Neither is an
AWS API credential. Values are deliberately omitted. Later commits retain that file.
The working version now contains only safe non-secret configuration. Compose requires
locally generated AIRFLOW__API__SECRET_KEY and AIRFLOW__API_AUTH__JWT_SECRET.
See [Airflow's configuration reference](https://airflow.apache.org/docs/apache-airflow/3.3.1/configurations-ref.html).

Directory scanning after fixes found only the existing ignored `.env` Fernet key.
Empty example passwords and offline_parse_placeholder are not real credentials.
Installed package examples produce unrelated scanner matches and are excluded by path.
No scanner can prove absence of every possible secret; available refs do not include
unknown remote branches, deleted refs, other clones, forks or caches.

If historical signing keys were used, rotate both on all Airflow components together
and restart them. Existing sessions/task tokens become invalid. bootstrap.py fills
missing keys only; it does not silently rotate existing values. Replace the two local
values using fresh secrets.token_urlsafe(48) values in a private editor or local script;
never print them. For an existing persisted Airflow database, Fernet rotation requires
Airflow's supported multi-key/rotate-fernet-key procedure; do not simply replace its
key or delete the database. The local Fernet key was not found in available Git history.

During a failed native Spark test, pytest's traceback included process environment.
Rotate the affected AZDO_FEED_PAT token with its issuer. It was not found in repository
history. Subsequent test invocations use short tracebacks; avoid --showlocals and shell
tracing when the process may contain secrets.

## Reference procedure for coordinated remote cleanup — separate authorization required

The original audit excluded history rewriting and force-push. Local rewriting has now
been separately authorized and completed as documented above. The subsequent commit/push
request authorizes publication of these prepared changes; any additional remote rewrite
outside that scope requires its own authorization.
Complete rotation first. Agree on a maintenance window with all repository users.
Review and commit the intended working changes separately, preserving user changes.
In an isolated mirror clone made after that commit:

```powershell
git clone --mirror <repository-url> crypto-clean.git
Set-Location crypto-clean.git
git bundle create ../crypto-before-clean.bundle --all
# Install git-filter-repo separately; check git filter-repo --version.
git filter-repo --path airflow/config/airflow.cfg --invert-paths --force
gitleaks git . --log-opts='--all' --redact=100
```

This removes **every historical version of airflow/config/airflow.cfg**, eliminating
both offending values without ever copying them into a replacement file or terminal.
Save the sanitized current file outside the mirror before rewriting and re-add it in
a normal checkout afterwards, or intentionally rely on environment/default config.
The bundle is sensitive evidence containing old secrets: encrypt/restrict it and retain
only for the agreed recovery period. Verify every branch/tag with Gitleaks before push.
git-filter-repo may remove origin: restore the verified URL if needed. Inspect all
rewritten refs. Only after explicit separate authorization push rewritten branches/tags
to the intended remote (force is required); do not blindly use --mirror against a shared
host because that can delete unrelated refs. Coordinate protected-branch settings.
All collaborators must re-clone, not merge old history back. Ask the host administrator
to purge cached/PR refs and assess forks. Rescan a fresh remote clone. Rewriting alone
does not revoke compromised credentials or erase copies outside this repository.

Optional history hygiene may remove src/crypto_data_platform.egg-info and
terraform/terraform.tfvars, but they are not scanner-confirmed secrets. Current versions
are untracked/ignored and the tfvars local file was preserved. Do not expand the rewrite
scope without reviewing its consequences.
