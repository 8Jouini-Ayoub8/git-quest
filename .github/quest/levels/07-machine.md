## ⚙️ Level 7 — Wake the Machine
*GitHub Actions · CI*

Your fork contains a robot: `.github/workflows/quest-ci.yml`. It inspects every push to `main` —
that's **Continuous Integration**, the first step of every deployment pipeline.
For security, GitHub **disables workflows in forks** until you allow them.

1. Your fork → **Actions** tab → *I understand my workflows, go ahead and enable them*.
2. Click **🛰️ Quest CI** → **Run workflow** → `main` → Run.
3. It will go 🔴 **red**. That's expected. Click the run → job **inspect** → read the log.
   The log tells you what your agent file is missing.
4. Fix it locally → `add` → `commit` → `push`. The push itself triggers CI again → 🟢 **green**.

Then **`/check`**.

> ⚠️ Don't modify the workflow or its script to force it green — I compare them with HQ's version 😏
