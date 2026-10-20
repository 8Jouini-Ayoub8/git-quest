## 👻 Level 2 — Ghost in the History
*log · show*

An intern leaked a secret in this repository a while ago… then deleted the file, thinking it was gone. 🙈
**Git never forgets.** Every commit is a full snapshot, forever.

```bash
git log --oneline                # the whole story, newest first
git log --stat                   # …with the files each commit touched
git show <hash>                  # what exactly changed in that commit
```

🎯 Find the leaked **passphrase** and add it to your agent file:
```text
passphrase: <the leaked passphrase>
```
Then `add` → `commit` → `push` → **`/check`**.

> 🛡️ Security lesson: deleting a secret in a new commit does **not** remove it from history.
> If you ever push a password: **rotate it immediately**.
