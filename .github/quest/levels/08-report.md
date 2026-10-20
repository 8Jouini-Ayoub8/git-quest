## 📨 Level 8 — Report to HQ
*pull request*

Time to send your agent file to HQ. You can't push to `{upstream}` — you're not a member.
That's exactly what a **Pull Request** is for: *"here are my commits, please pull them into your repo"*.

Your `main` contains lots of training changes (vaults, roster…). HQ only wants **your agent file**.
So build a clean branch starting from HQ's `main`:
```bash
git fetch upstream
git switch -c report upstream/main               # new branch, starting from HQ's main
git restore --source=main -- agents/{login}.md   # grab just your file from your main
git add agents/{login}.md
git status                                       # exactly 1 new file, staged
git commit -m "agent: {login} reporting for duty"
git push -u origin report
```
On GitHub, click **Compare & pull request**:
- **base repository:** `{upstream}` · **base:** `main`
- **head repository:** `{fork}` · **compare:** `report`
- **title:** `🕵️ Agent {login} reporting`

Open the PR — I'll review it automatically (and also answer here).
