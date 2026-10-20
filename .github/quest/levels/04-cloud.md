## ☁️ Level 4 — Teammate in the Cloud
*rejected push · pull*

In real life you're never alone on a repository. Let's simulate a teammate who pushes *while you're working*.

**1. Be the teammate — on github.com:** open your fork → `team/roster.md` → ✏️ *Edit* → under **Cloud crew** add:
```text
- cloud-twin-of-{login}
```
→ **Commit changes** (directly to `main`).

**2. Be yourself — on your laptop, *without pulling first*:** open `team/roster.md`, under **Field agents** add:
```text
- {login}
```
```bash
git add team/roster.md
git commit -m "team: add myself to the field agents"
git push                       # 💥 rejected! GitHub has a commit you don't have.
```
Read the error: *"Updates were rejected because the remote contains work that you do not have locally"*.

**3. Sync, then push:**
```bash
git pull                       # = git fetch (download) + git merge (combine)
git log --oneline --graph -5   # see the two lines of history joining
git push
```
Then **`/check`**.

> 💡 An editor opened asking for a merge message? That's normal — save & close it (`--no-edit` skips it).
