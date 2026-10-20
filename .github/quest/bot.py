#!/usr/bin/env python3
"""
Git Quest — the Quest Master bot.

Runs in the UPSTREAM repository only (never in forks), triggered by:
  * issues: opened          → a student enlists ("[QUEST] ..." issue)
  * issue_comment: created  → the issue author comments "/check"
  * pull_request_target     → the final level (pull request to HQ)

Security model
  * flags = md5(QUEST_SALT : level : login)  → QUEST_SALT is a repo secret, never printed.
  * The student's fork is cloned *bare*: no checkout, no hooks, no code from it is executed.
  * Untrusted text (titles, comments) is only read from the event JSON, never interpolated in shell.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from checks import CHECKS, Ctx, Git  # noqa: E402

CFG = json.loads((HERE / "quest.json").read_text(encoding="utf-8"))
LEVELS = CFG["levels"]
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GIT_BASE = os.environ.get("QUEST_GIT_BASE", "https://github.com")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SALT = os.environ.get("QUEST_SALT", "")
FLAG_MODE = (os.environ.get("FLAG_MODE") or "per-user").strip().lower()
UPSTREAM = os.environ.get("GITHUB_REPOSITORY", "")
REPO_NAME = UPSTREAM.split("/")[-1] if UPSTREAM else "git-quest"
LAST = LEVELS[-1]["n"]
CORE_LAST = 8          # level 9 is a bonus


# ---------------------------------------------------------------------------
# GitHub REST
# ---------------------------------------------------------------------------
class Api:
    def __init__(self, token):
        self.token = token

    def req(self, method, path, body=None, ok404=False):
        url = path if path.startswith("http") else API + path
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(url, data=data, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "git-quest-bot",
        })
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                txt = resp.read().decode()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            if ok404 and e.code == 404:
                return None
            print(f"::warning::GitHub API {method} {path} → {e.code} {e.read()[:300]!r}")
            raise

    def comment(self, repo, number, body):
        return self.req("POST", f"/repos/{repo}/issues/{number}/comments", {"body": body})

    def add_labels(self, repo, number, labels):
        return self.req("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": labels})

    def react(self, repo, comment_id, content="eyes"):
        try:
            self.req("POST", f"/repos/{repo}/issues/comments/{comment_id}/reactions", {"content": content})
        except Exception:
            pass

    def quest_issue(self, repo, login):
        items = self.req("GET", f"/repos/{repo}/issues?labels=quest&state=all&creator={login}&per_page=20") or []
        items = [i for i in items if "pull_request" not in i]
        return items[-1] if items else None   # oldest first → the original quest issue

    def forks_of(self, repo, login):
        for page in range(1, 6):
            items = self.req("GET", f"/repos/{repo}/forks?per_page=100&page={page}") or []
            for f in items:
                if f["owner"]["login"].lower() == login.lower():
                    return f["full_name"]
            if len(items) < 100:
                break
        return None

    def workflow_runs(self, repo, workflow):
        r = self.req("GET", f"/repos/{repo}/actions/workflows/{workflow}/runs?per_page=30", ok404=True)
        if not r or not r.get("total_count"):
            return None
        return r.get("workflow_runs", [])

    def user_prs(self, repo, login):
        out = []
        for page in range(1, 4):
            items = self.req("GET", f"/repos/{repo}/pulls?state=all&per_page=100&page={page}") or []
            out += [p for p in items if p["user"]["login"].lower() == login.lower()]
            if len(items) < 100:
                break
        return out

    def pr_files(self, repo, number):
        return self.req("GET", f"/repos/{repo}/pulls/{number}/files?per_page=100") or []


def http_get(url):
    try:
        req = urllib.request.Request(url + "?t=" + os.urandom(4).hex(), headers={"User-Agent": "git-quest-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Flags & text
# ---------------------------------------------------------------------------
def flag(level_id, login):
    seed = f"{SALT}:{level_id}" if FLAG_MODE == "static" else f"{SALT}:{level_id}:{login.lower()}"
    return f"{CFG['flag_prefix']}{{{hashlib.md5(seed.encode()).hexdigest()}}}"


def render(text, login, fork):
    return (text.replace("{login}", login).replace("{upstream}", UPSTREAM)
                .replace("{repo}", REPO_NAME).replace("{fork}", fork or f"{login}/{REPO_NAME}"))


def mission(n, login, fork):
    f = next(HERE.joinpath("levels").glob(f"{n:02d}-*.md"))
    return render(f.read_text(encoding="utf-8"), login, fork)


def progress_bar(earned):
    cells = []
    for lv in LEVELS:
        cells.append("🟩" if lv["n"] in earned else ("⭐" if lv["n"] == LAST else "⬜"))
    core = len([n for n in earned if n <= CORE_LAST])
    return f"{''.join(cells)}  **{core}/{CORE_LAST + 1}**" + ("  + ⭐ bonus" if LAST in earned else "")


# ---------------------------------------------------------------------------
# Fork discovery (git only — no API call in the common case)
# ---------------------------------------------------------------------------
def clone_fork(api, login, workdir):
    candidates = [f"{login}/{REPO_NAME}"]
    for i, full in enumerate(candidates + [None]):
        if full is None:
            if api is None:
                break
            full = api.forks_of(UPSTREAM, login)
            if not full or full in candidates:
                break
        dest = os.path.join(workdir, f"fork{i}.git")
        p = subprocess.run(["git", "clone", "--bare", "--quiet", "--no-tags", f"{GIT_BASE}/{full}.git", dest],
                           capture_output=True, text=True, timeout=120,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        if p.returncode == 0:
            return full, dest
    return None, None


def is_real_fork(fork_git, upstream_git, ref):
    up_roots = Git(upstream_git).roots(ref)
    return bool(up_roots) and up_roots <= Git(fork_git).roots("--all")


# ---------------------------------------------------------------------------
# The quest loop
# ---------------------------------------------------------------------------
def run_quest(api, login, issue_labels, upstream_git, upstream_ref, workdir, event_pr=None):
    """Return (newly_earned:[n], failure:(n, Result)|None, earned:set, fork)."""
    earned = {int(l.split("-")[1]) for l in issue_labels if l.startswith("level-") and l.split("-")[1].isdigit()}
    new, failure = [], None

    fork, fork_git = clone_fork(api, login, workdir)
    if not fork:
        from checks import fail
        return new, (0, fail(f"I couldn't find a fork of `{UPSTREAM}` owned by **@{login}**.",
                             f"Click **Fork** on https://github.com/{UPSTREAM} (keep the name `{REPO_NAME}`), then comment `/check`.")), earned, None
    if not is_real_fork(fork_git, upstream_git, upstream_ref):
        from checks import fail
        return new, (0, fail(f"`{fork}` exists but doesn't share history with `{UPSTREAM}`.",
                             "Delete it and use the **Fork** button — don't create an empty repository by hand.")), earned, fork
    if 0 not in earned:
        new.append(0)
        earned.add(0)

    ctx = Ctx(login, fork, fork_git, upstream_git, upstream_ref, CFG, api=api,
              upstream_repo=UPSTREAM, event_pr=event_pr, http_get=http_get)
    for lv in LEVELS[1:]:
        if lv["n"] in earned:
            continue
        try:
            res = CHECKS[lv["id"]](ctx)
        except Exception as e:  # never crash on a weird fork
            print(f"::warning::check {lv['id']} crashed: {e}")
            from checks import fail
            res = fail("The checker hit an unexpected situation in your repository.",
                       "Comment `/check` again; if it persists, call an organizer 🙋.")
        if not res.ok:
            failure = (lv["n"], res)
            break
        new.append(lv["n"])
        earned.add(lv["n"])
        ctx.last_data = res.data
    return new, failure, earned, fork


def compose(login, fork, new, failure, earned):
    by_n = {lv["n"]: lv for lv in LEVELS}
    parts = []
    for n in new:
        lv = by_n[n]
        parts.append(f"### {lv['emoji']} Level {n} cleared — {lv['title']}\n"
                     f"<sub>skills: {lv['skills']}</sub>\n\n"
                     f"```\n{flag(lv['id'], login)}\n```")
    parts.append(f"\n{progress_bar(earned)}\n")
    if failure:
        n, res = failure
        lv = by_n[n]
        if new or n == 0:
            # the student just reached this level → full briefing
            if n != 0:
                parts.append("---\n" + mission(n, login, fork))
            else:
                parts.append(f"### 🔴 {res.reason}\n\n💡 {res.hint}")
        else:
            parts.append(f"### 🔴 Level {n} — {lv['title']}: not yet\n\n"
                         f"**What I see:** {res.reason}\n\n"
                         f"💡 **Hint:** {res.hint}\n\n"
                         f"<details><summary>📜 Re-read the Level {n} briefing</summary>\n\n"
                         f"{mission(n, login, fork)}\n</details>")
    else:
        parts.append(mission(99, login, fork))   # every level, bonus included → finale
    parts.append("\n<sub>🤖 Comment <code>/check</code> on this issue any time to re-run the checks.</sub>")
    return "\n\n".join(parts)


def main():
    if not SALT:
        print("::error::QUEST_SALT secret is missing — refusing to hand out flags. "
              "Settings → Secrets and variables → Actions → New repository secret.")
        sys.exit(1)
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    name = os.environ["GITHUB_EVENT_NAME"]
    api = Api(TOKEN)
    upstream_git = os.path.join(os.environ.get("GITHUB_WORKSPACE", "."), ".git")
    upstream_ref = "HEAD"
    event_pr = None

    if name == "issues":
        issue = event["issue"]
        login = issue["user"]["login"]
        dup = api.quest_issue(UPSTREAM, login)
        if dup and dup["number"] != issue["number"]:
            api.comment(UPSTREAM, issue["number"],
                        f"👋 @{login} you already have a quest running in #{dup['number']} — continue there! Closing this one.")
            api.req("PATCH", f"/repos/{UPSTREAM}/issues/{issue['number']}", {"state": "closed"})
            return
        if "quest" not in [l["name"] for l in issue.get("labels", [])]:
            api.add_labels(UPSTREAM, issue["number"], ["quest"])
    elif name == "issue_comment":
        issue = event["issue"]
        login = issue["user"]["login"]
        if event["comment"]["user"]["login"] != login or not event["comment"]["body"].strip().startswith("/check"):
            return
        api.react(UPSTREAM, event["comment"]["id"], "eyes")
    elif name == "pull_request_target":
        event_pr = event["pull_request"]
        login = event_pr["user"]["login"]
        issue = api.quest_issue(UPSTREAM, login)
        if not issue:
            api.comment(UPSTREAM, event_pr["number"],
                        f"👋 @{login}, start the quest first: open a **🚩 Start the Quest** issue in this repository.")
            return
    else:
        return

    labels = [l["name"] for l in issue.get("labels", [])]
    workdir = tempfile.mkdtemp(prefix="quest-")
    try:
        new, failure, earned, fork = run_quest(api, login, labels, upstream_git, upstream_ref, workdir, event_pr)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    if new:
        extra = [f"level-{n}" for n in new] + (["finished"] if CORE_LAST in new else [])
        api.add_labels(UPSTREAM, issue["number"], extra)

    header = f"@{login}\n\n" if name != "issue_comment" else ""
    if name == "issues":
        header += Path(HERE / "levels" / "welcome.md").read_text(encoding="utf-8").replace("{login}", login) + "\n\n"
    body = header + compose(login, fork, new, failure, earned)
    api.comment(UPSTREAM, issue["number"], body)

    if event_pr is not None:
        if 8 in new:
            api.comment(UPSTREAM, event_pr["number"],
                        f"📨 Report received, agent @{login}! Your flag is waiting in #{issue['number']}. HQ will review and merge. 🫡")
            api.add_labels(UPSTREAM, event_pr["number"], ["agent-report"])
        elif failure and failure[0] == 8:
            api.comment(UPSTREAM, event_pr["number"],
                        f"🔴 {failure[1].reason}\n\n💡 {failure[1].hint}")
        elif failure:
            api.comment(UPSTREAM, event_pr["number"],
                        f"⏳ Nice PR, but you're still on Level {failure[0]} — see #{issue['number']}.")

    print(f"login={login} fork={fork} new={new} earned={sorted(earned)} "
          f"failure={failure[0] if failure else None}")


if __name__ == "__main__":
    main()
