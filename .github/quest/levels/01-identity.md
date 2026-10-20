## 🆔 Level 1 — Identity
*clone · config · status · add · commit · push*

Your fork lives on GitHub. Bring a copy to your laptop and sign your first commit.

**1. Tell Git who you are** (once per computer):
```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"     # use your GitHub email
git config --global init.defaultBranch main
git config --global pull.rebase false                 # pull = fetch + merge (we'll see why)
git config --global core.editor "code --wait"         # or "nano" — avoid getting stuck in vim 😅
```

**2. Clone your fork** (not HQ's!):
```bash
git clone https://github.com/{fork}.git
cd {repo}
git status            # 👀 "nothing to commit, working tree clean"
```

**3. Create your agent file** — copy the template to **`agents/{login}.md`** (the name must be *exactly* your username):
```bash
cp agents/TEMPLATE.md agents/{login}.md
```
Open it and fill it:
```text
agent: {login}
codename: <pick a hacker codename>
```

**4. Save it in history and send it to GitHub:**
```bash
git status                       # your file is "untracked" (red)
git add agents/{login}.md
git status                       # now "to be committed" (green) → it's in the staging area
git commit -m "feat: enlist agent {login}"
git log --oneline -3             # your commit is on top
git push                         # local → GitHub
```

✅ Then comment **`/check`**.
