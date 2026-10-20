## 🌿 Level 5 — Branch Out
*branch · switch · merge · push -u*

Never experiment on `main`. A **branch** is just a movable label pointing to a commit: cheap, instant, safe.

```bash
git switch -c feature/gadget           # create the branch AND move onto it
git branch                             # * marks where you are
```
Add a line to your agent file:
```text
gadget: <your signature gadget>
```
```bash
git add agents/{login}.md
git commit -m "feat: equip gadget"
git push -u origin feature/gadget      # first push of a new branch: -u links it to GitHub
```
👀 Look at your fork on GitHub: a new branch appeared. Now bring the work back into `main`:
```bash
git switch main                        # the gadget line disappears from your file… it lives on the branch!
git merge feature/gadget               # …and comes back.
git log --oneline --graph --all -6
git push
```
Then **`/check`**.
