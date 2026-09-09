# GIT_HISTORY_DATASET_PURGE.md

Analysis of whether a destructive Git history rewrite is needed to remove deprecated dataset
material from this repository.

**No history rewrite has been performed.** This document is analysis and procedure only, as
instructed. Executing anything in §6 requires an explicit later instruction.

**Date:** 2026-09-09 · **Audited at HEAD `2c4500c`** (pre-reset)

---

## 1. Conclusion first

> **No purge is required.** No dataset audio, model, checkpoint or feature file was ever
> committed to this repository. The entire `.git` directory is **1.4 MB**.

The only deprecated-dataset material that entered history is **2.67 MB of text** — a checksum
list and a JSON manifest. No remote has ever existed, so nothing was published.

A rewrite would be a high-risk operation to reclaim ~2.6 MB from a 1.4 MB compressed
repository. **The cost/benefit does not justify it.** The recommendation is to do nothing.

## 2. What historical dataset objects exist

| Object | Introduced in | Size | Type |
|---|---|---:|---|
| `dataset_manifest/CHECKSUMS.sha256` | `2c4500c` | 2,668,642 B | text — 21,285 SHA-256 digests |
| `dataset_manifest/manifest.json` | `2c4500c` | ~3,300 B | text — counts, splits, root hash |

Both were removed from the working tree by the reset commit. Their blobs remain reachable from
commit `2c4500c` — which is normal, expected Git behaviour and not a leak.

### What is NOT in history — verified, not assumed

```bash
git rev-list --objects --all | awk '{print $2}' \
  | grep -E '\.(wav|npz|npy|tflite|keras|h5|ckpt|pb|zip)$'
# -> no output
```

No `.wav`, `.npz`, `.npy`, `.tflite`, `.keras`, `.h5`, `.ckpt`, `.pb` or `.zip` blob exists in
any commit, on any branch. The 21,267 audio files lived only in the git-ignored `data/`
directory and were never staged.

### Largest blobs in the whole repository history

```
2668642  dataset_manifest/CHECKSUMS.sha256      <- largest object in the repo
  18720  STORAGE_AUDIT.md
  14107  CURRENT_HANDOFF.md
  13545  DECISIONS.md
  12975  BUILD_LOG.md
```

## 3. Git LFS

**Not involved.**

| Check | Result |
|---|---|
| git-lfs installed | yes, 3.7.1 |
| LFS filter entries in `.gitattributes` | **none** |
| `git lfs ls-files` | **empty** |
| LFS pointer files in history | none |

No LFS object store exists, so there is nothing to prune from one and no remote LFS storage to
clean.

## 4. Where the deprecated material exists now

| Location | Contains | Action taken |
|---|---|---|
| Working tree | nothing — removed by the reset commit | done |
| Current commit (post-reset) | nothing | done |
| Historical commit `2c4500c` | 2.67 MB of checksum/manifest **text** | left in place |
| Git LFS | nothing | n/a |
| Remote | **no remote has ever been configured; nothing was ever pushed** | n/a |
| Disk, outside Git | `data/` — quarantined 674 MB, git-ignored throughout | user's call |

## 5. Risks of rewriting history

Relevant if a purge is ever ordered:

1. **Every commit hash after the rewrite point changes.** `2c4500c`, `7914cee`, `39a0dbe`,
   `845be0b` all become different objects. Every reference to a hash in `BUILD_LOG.md`,
   `DECISIONS.md`, `DATASET.md`, this file, and any external note becomes **wrong**. The
   project deliberately cites hashes for provenance, so this cost is real.
2. **Force-push required** if a remote ever exists. Any clone or fork keeps the old objects and
   will re-introduce them on the next push.
3. **Recovery of removed files is lost.** The reset relies on `git show 2c4500c:<path>` to
   retrieve the removed tooling. A purge that rewrites `2c4500c` breaks that path.
4. **`git-filter-repo` removes the origin remote by design**, and refuses to run on a
   non-fresh clone without `--force`.
5. **Irreversible without a backup.** Once the reflog expires and objects are GC'd, the
   original history is gone.
6. **Benefit is ~2.6 MB.** The repository is 1.4 MB compressed.

## 6. Procedure, if a purge is ever explicitly ordered

**Do not run any of this without an explicit instruction.**

```bash
# 0. BACK UP FIRST - a full mirror, kept somewhere else
git clone --mirror . ../sih2026-backup.git

# 1. Install the recommended tool (filter-branch is deprecated and slow)
pip install git-filter-repo

# 2. From a FRESH clone, drop the paths from all history
git clone . ../sih2026-purge && cd ../sih2026-purge
git filter-repo --path dataset_manifest --invert-paths

# 3. Verify the blobs are gone
git rev-list --objects --all | grep -i dataset_manifest    # expect no output

# 4. Expire reflog and garbage-collect
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Confirm the size change
du -sh .git
```

If a remote exists by then, add — **with the consequences of step 5 in §5 understood**:

```bash
git push origin --force --all
git push origin --force --tags
```

Every collaborator must then re-clone. Rebasing existing clones onto rewritten history
reliably reintroduces the purged objects.

### Cheaper alternative that avoids a rewrite entirely

If the goal is only "the deprecated corpus must not be reachable from the current project",
that is **already true** — the files are gone from the working tree and from HEAD. Starting a
fresh repository with the reset state as its first commit also achieves it, at the cost of
losing the audit trail that documents *why* the project is in this state. Given how much of
this project's value is in its recorded reasoning, that trade is not recommended.

## 7. Recommendation

**Take no action.** The purge would remove 2.6 MB of text from a 1.4 MB repository, invalidate
every commit hash the documentation cites, and break the retrieval path for the tooling the
reset deliberately preserved. Nothing was ever pushed, and no audio, model or feature file was
ever committed.

Revisit only if the checksum list is later considered sensitive in itself — it is not; it
contains hashes and relative filenames, no audio and no personal data.
