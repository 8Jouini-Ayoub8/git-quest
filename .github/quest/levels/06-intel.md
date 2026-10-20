## 📡 Level 6 — Intel from HQ
*remote · fetch · merge · conflict*

HQ published new intel on a branch of **their** repository (`{upstream}`), not yours.
Your clone only knows one remote: `origin` (your fork). Let's add HQ as a second remote called `upstream`.

**1. First, set your codename in the briefing** — in `mission/briefing.txt` change
`codename: TBD` → `codename: <the same codename as in your agent file>`, then:
```bash
git commit -am "mission: claim my codename"
```

**2. Connect to HQ and download their intel:**
```bash
git remote add upstream https://github.com/{upstream}.git
git remote -v                               # origin = your fork · upstream = HQ
git fetch upstream                          # download only — nothing in your files changes
git branch -r                               # upstream/intel-update appeared
git log --oneline main..upstream/intel-update   # what HQ has that you don't
```

**3. Merge it — and meet your first conflict 💥**
```bash
git merge upstream/intel-update
# CONFLICT (content): Merge conflict in mission/briefing.txt
git status                                  # "both modified"
```
Open `mission/briefing.txt`:
```text
<<<<<<< HEAD
codename: NightOwl            ← your version
=======
codename: REDACTED-BY-HQ      ← HQ's version
>>>>>>> upstream/intel-update
```
**Resolve:** keep **your** codename, keep HQ's new `clearance: LEVEL-5` line, delete the 3 marker lines.
```bash
git add mission/briefing.txt                # "conflict resolved"
git commit --no-edit                        # finishes the merge
git push
```
Then **`/check`**.

> 💡 `git pull upstream intel-update` would do fetch + merge in one go. Panicking? `git merge --abort` puts everything back.
