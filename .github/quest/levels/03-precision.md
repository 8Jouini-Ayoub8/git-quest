## 🎯 Level 3 — Precision Strike
*status · diff · add &lt;file&gt;*

Two vaults: `vault/alpha.txt` and `vault/beta.txt`, both `STATUS: LOCKED`.
Protocol: they must be opened in **two separate commits — alpha first, then beta**.
This is what the **staging area** is for: *you choose exactly what goes in each commit*.

1. Edit **both** files: `LOCKED` → `OPEN`.
2. Inspect before committing:
```bash
git status                  # 2 modified files
git diff                    # the exact lines you changed (not staged yet)
git add vault/alpha.txt     # stage ONLY alpha
git status                  # alpha: green (staged) · beta: red (not staged)
git diff --staged           # what the next commit will contain
git commit -m "vault: open alpha"
git add vault/beta.txt
git commit -m "vault: open beta"
git log --oneline -3
git push
```
Then **`/check`**.

> 💡 Staged the wrong file? `git restore --staged <file>` takes it back out of the staging area (your edit is kept).
