"""
Git Quest — level checks.

Every check receives a Ctx and returns Result(ok, reason, hint).
The fork is inspected through a *bare* clone: nothing from the student's
repository is ever checked out or executed — we only read git objects.
"""
import re
import subprocess
from dataclasses import dataclass, field

WEB_EMAIL = "noreply@github.com"          # committer of every commit made on github.com
MARKER_RE = r"^(<<<<<<<|>>>>>>>)( |$)|^=======$"


@dataclass
class Result:
    ok: bool
    reason: str = ""
    hint: str = ""
    data: dict = field(default_factory=dict)


def ok(**data):
    return Result(True, data=data)


def fail(reason, hint=""):
    return Result(False, reason, hint)


class Git:
    def __init__(self, git_dir):
        self.git_dir = git_dir

    def run(self, *args, check=True):
        p = subprocess.run(["git", "--git-dir", self.git_dir, *args],
                           capture_output=True, text=True, timeout=60)
        if check and p.returncode != 0:
            raise RuntimeError(p.stderr.strip())
        return p

    def out(self, *args):
        p = self.run(*args, check=False)
        return p.stdout if p.returncode == 0 else None

    def rev(self, ref):
        o = self.out("rev-parse", "--verify", "--quiet", ref + "^{commit}")
        return o.strip() if o else None

    def show(self, ref, path):
        return self.out("show", f"{ref}:{path}")

    def blob(self, ref, path):
        o = self.out("rev-parse", "--verify", "--quiet", f"{ref}:{path}")
        return o.strip() if o else None

    def ls(self, ref, directory):
        o = self.out("ls-tree", "--name-only", ref, directory.rstrip("/") + "/")
        return [l.split("/")[-1] for l in o.splitlines()] if o else []

    def is_ancestor(self, a, b):
        return self.run("merge-base", "--is-ancestor", a, b, check=False).returncode == 0

    def commits(self, ref, *paths, merges=False):
        """[(sha, committer_name, committer_email, parents[])] newest first."""
        args = ["log", "--format=%H%x09%cn%x09%ce%x09%P"]
        if not merges:
            args.append("--no-merges")
        args.append(ref)
        if paths:
            args += ["--", *paths]
        o = self.out(*args) or ""
        res = []
        for line in o.splitlines():
            sha, cn, ce, parents = (line.split("\t") + [""])[:4]
            res.append((sha, cn, ce, parents.split()))
        return res

    def files_of(self, sha):
        o = self.out("diff-tree", "--no-commit-id", "--name-only", "-r", sha) or ""
        return [l for l in o.splitlines() if l]

    def roots(self, ref):
        o = self.out("rev-list", "--max-parents=0", ref) or ""
        return set(o.split())


class Ctx:
    """Everything a check needs to know about one student."""

    def __init__(self, login, fork, fork_git, upstream_git, upstream_ref, config, api=None,
                 upstream_repo="", event_pr=None, http_get=None):
        self.login = login
        self.fork = fork                    # "login/git-quest"
        self.g = Git(fork_git)              # bare clone of the fork
        self.up = Git(upstream_git)         # upstream repository (actions/checkout)
        self.up_ref = upstream_ref          # e.g. "origin/main" or "main"
        self.cfg = config
        self.api = api
        self.upstream_repo = upstream_repo
        self.event_pr = event_pr
        self.http_get = http_get
        self.main = config.get("default_branch", "main")
        self._agent_path = None

    # -- helpers -----------------------------------------------------------
    def agent_path(self, ref=None):
        ref = ref or self.main
        want = f"{self.login.lower()}.md"
        for name in self.g.ls(ref, "agents"):
            if name.lower() == want:
                return f"agents/{name}"
        return None

    def agent_fields(self, ref=None):
        ref = ref or self.main
        path = self.agent_path(ref)
        if not path:
            return None, {}
        text = self.g.show(ref, path) or ""
        return path, parse_fields(text)


def parse_fields(text):
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]?\s*([A-Za-z_]+)\s*:\s*(.*?)\s*$", line)
        if m and not line.strip().startswith("<!--"):
            fields.setdefault(m.group(1).lower(), m.group(2).strip("`*_ "))
    return fields


PLACEHOLDERS = {"", "tbd", "your-github-username", "your-codename", "<your codename>", "..."}


def filled(value):
    return value is not None and value.strip().lower() not in PLACEHOLDERS


# ---------------------------------------------------------------------------
# Levels
# ---------------------------------------------------------------------------

def check_identity(c: Ctx):
    path, f = c.agent_fields()
    if not path:
        for b in (c.g.out("for-each-ref", "--format=%(refname:short)", "refs/heads") or "").split():
            if b != c.main and c.agent_path(b):
                return fail(f"Your agent file exists on branch `{b}`, but not on `{c.main}`.",
                            f"Switch back with `git switch {c.main}` and redo the commit there, then `git push`.")
        return fail(f"I can't find `agents/{c.login}.md` on the `{c.main}` branch of your fork.",
                    "Created it but forgot to push? Run `git status` then `git log --oneline -3` — "
                    "if your commit is there, `git push`. The file name must be exactly your GitHub username.")
    if f.get("agent", "").lower() != c.login.lower():
        return fail(f"In `{path}`, the line `agent:` should be your username (`{c.login}`), I read `{f.get('agent', '')}`.",
                    "Edit the line, then `git add` → `git commit` → `git push`.")
    if not filled(f.get("codename")):
        return fail(f"Your `codename:` line in `{path}` is empty.",
                    "Pick a hacker codename (e.g. `codename: NightOwl`), commit and push.")
    added = c.g.commits(c.main, path)
    if added and all(ce == WEB_EMAIL for _, _, ce, _ in added):
        return fail("Your agent file was created on github.com, not from your terminal.",
                    "This level is about the *local* workflow. Edit the file locally (add a space, anything), "
                    "then `git add`, `git commit`, `git push` from your laptop.")
    return ok()


def check_ghost(c: Ctx):
    path, f = c.agent_fields()
    got = (f.get("passphrase") or "").strip()
    if not got:
        return fail(f"No `passphrase:` line in `{path}` yet.",
                    "Someone leaked a secret in the history. `git log --oneline` then `git show <hash>` on suspicious commits.")
    if got.lower() != c.cfg["passphrase"].lower():
        return fail(f"`passphrase: {got}` is not the leaked one.",
                    "Look for the commit that *removed* a file — the commit *before* it still contains the secret. "
                    "`git log --stat` shows which files each commit touched.")
    return ok()


def check_precision(c: Ctx):
    for name in ("alpha", "beta"):
        txt = c.g.show(c.main, f"vault/{name}.txt") or ""
        if "STATUS: OPEN" not in txt or "LOCKED" in txt:
            return fail(f"`vault/{name}.txt` on `{c.main}` is still not `STATUS: OPEN`.",
                        "Replace `LOCKED` with `OPEN` in both vault files.")
    single = {"vault/alpha.txt": [], "vault/beta.txt": []}
    mixed = False
    for sha, _cn, ce, _p in c.g.commits(c.main, "vault/"):
        files = c.g.files_of(sha)
        if ce == WEB_EMAIL:
            continue
        if files in (["vault/alpha.txt"], ["vault/beta.txt"]):
            single[files[0]].append(sha)
        elif "vault/alpha.txt" in files and "vault/beta.txt" in files:
            mixed = True
    if single["vault/alpha.txt"] and single["vault/beta.txt"]:
        for a in single["vault/alpha.txt"]:
            for b in single["vault/beta.txt"]:
                if c.g.is_ancestor(a, b):
                    return ok()
        return fail("You committed beta before alpha. The protocol is alpha *first*, then beta.",
                    "Add a line `opened-by: <you>` to alpha → commit it alone; then the same in beta → commit alone; push.")
    if mixed:
        return fail("Both vaults were changed in the **same** commit.",
                    "The point is to stage *one file at a time*. Recovery: add a line `opened-by: <you>` to "
                    "`vault/alpha.txt`, `git add vault/alpha.txt`, commit; then same for beta in a second commit; push.")
    return fail("I need two separate local commits: one touching only `vault/alpha.txt`, then one touching only `vault/beta.txt`.",
                "Use `git status` and `git diff --staged` before each commit to see exactly what will go in.")


def check_cloud(c: Ctx):
    text = (c.g.show(c.main, "team/roster.md") or "").lower()
    login = c.login.lower()
    twin = f"cloud-twin-of-{login}"
    has_twin = twin in text
    has_local = re.search(rf"^\s*-\s*{re.escape(login)}\s*$", text, re.M) is not None
    roster = c.g.commits(c.main, "team/roster.md")
    web = [s for s, _, ce, _ in roster if ce == WEB_EMAIL]
    local = [s for s, _, ce, _ in roster if ce != WEB_EMAIL and s not in c._upstream_commits()]
    if not has_twin or not web:
        return fail(f"I don't see the cloud edit: a line `- {twin}` committed **on github.com** in `team/roster.md`.",
                    "Open your fork on github.com → `team/roster.md` → ✏️ → add the line under *Cloud crew* → Commit changes.")
    if not has_local or not local:
        return fail(f"The web edit is there, but not your local line `- {c.login}` under *Field agents*.",
                    "Add it from your laptop, commit, `git push`. Rejected? That's the lesson: `git pull`, then push again.")
    return ok()


def check_branch(c: Ctx):
    br = "feature/gadget"
    tip = c.g.rev(br)
    if not tip:
        return fail(f"Your fork has no branch `{br}` on GitHub.",
                    f"`git switch -c {br}` → commit → `git push -u origin {br}`. "
                    "`git branch -a` shows which branches exist locally and remotely.")
    path, f = c.agent_fields(br)
    if not path or not filled(f.get("gadget")):
        return fail(f"On branch `{br}`, your agent file has no `gadget:` line.",
                    f"While on `{br}` add `gadget: <your gadget>`, commit, `git push`.")
    if not c.g.is_ancestor(tip, c.main):
        return fail(f"`{br}` is pushed ✅ but not merged into `{c.main}` yet.",
                    f"`git switch {c.main}` → `git merge {br}` → `git push`.")
    _, fm = c.agent_fields()
    if not filled(fm.get("gadget")):
        return fail(f"`{c.main}` doesn't show your gadget.", "Did you push main after the merge? `git push`")
    return ok()


def check_intel(c: Ctx):
    intel = c.up.rev(c.cfg.get("intel_ref", "origin/" + c.cfg["intel_branch"]))
    if intel and not c.g.is_ancestor(intel, c.main):
        return fail("HQ's intel isn't in your `main` yet.",
                    f"`git remote add upstream https://github.com/{c.upstream_repo}.git` → `git fetch upstream` → "
                    f"`git merge upstream/{c.cfg['intel_branch']}` → resolve → `git push`.")
    markers = c.g.out("grep", "-I", "-n", "-E", MARKER_RE, c.main, "--", ".", ":(exclude).github")
    if markers:
        first = markers.splitlines()[0].split(":", 1)[1]
        return fail(f"Conflict markers were committed: `{first}`",
                    "Open the file, delete the lines `<<<<<<<`, `=======`, `>>>>>>>`, keep the right content, "
                    "`git add`, `git commit`, `git push`.")
    brief = parse_fields(c.g.show(c.main, "mission/briefing.txt") or "")
    _, agent = c.agent_fields()
    code = brief.get("codename", "")
    if brief.get("clearance", "").upper() != "LEVEL-5":
        return fail("The line `clearance: LEVEL-5` from HQ is missing in `mission/briefing.txt`.",
                    "When resolving, keep *both*: your codename **and** HQ's clearance line.")
    if code.upper() in ("TBD", "REDACTED-BY-HQ", ""):
        return fail(f"`mission/briefing.txt` says `codename: {code}` — HQ's version won.",
                    "Resolve in *your* favour: the codename line must keep YOUR codename.")
    if code.lower() != (agent.get("codename") or "").lower():
        return fail(f"`briefing.txt` codename (`{code}`) ≠ your agent file codename (`{agent.get('codename')}`).",
                    "Use the same codename in both files.")
    return ok()


def check_machine(c: Ctx):
    for p in (".github/workflows/quest-ci.yml", ".github/quest/ci_inspect.py"):
        if c.g.blob(c.main, p) != c.up.blob(c.up_ref, p):
            return fail(f"`{p}` was modified in your fork. Nice try 😏",
                        f"Restore it: `git restore --source=upstream/main -- {p}` (after `git fetch upstream`), commit, push.")
    _, f = c.agent_fields()
    runs = c.api.workflow_runs(c.fork, "quest-ci.yml") if c.api else None
    if runs is None:
        return fail("Actions are not enabled on your fork (no runs found).",
                    "Your fork → **Actions** tab → *I understand my workflows, go ahead and enable them*. "
                    "Then *Quest CI* → **Run workflow**.")
    green = [r for r in runs if r.get("conclusion") == "success" and r.get("head_branch") == c.main]
    red = [r for r in runs if r.get("conclusion") == "failure"]
    if not green:
        if red:
            return fail(f"Quest CI ran {len(red)} time(s) and it's 🔴 red.",
                        "Open the failed run → job *inspect* → read the log: it tells you exactly what is missing. Fix, push.")
        return fail("No finished Quest CI run yet.", "Actions tab → *Quest CI* → **Run workflow** (or push a commit).")
    if not filled(f.get("motto")):
        return fail("CI is green, but your agent file has no `motto:` on main.", "Add it, commit, push.")
    return ok()


def check_report(c: Ctx):
    want = f"agents/{c.login.lower()}.md"
    prs = []
    if c.event_pr and c.event_pr["user"]["login"].lower() == c.login.lower():
        prs.append(c.event_pr)
    if c.api:
        prs += [p for p in c.api.user_prs(c.upstream_repo, c.login) if not c.event_pr or p["number"] != c.event_pr["number"]]
    if not prs:
        return fail(f"No pull request from you on `{c.upstream_repo}` yet.",
                    "Follow the steps above, then on GitHub: **Compare & pull request** (base: HQ's `main`).")
    last_reason = ""
    for pr in prs:
        files = c.api.pr_files(c.upstream_repo, pr["number"]) if c.api else []
        names = [x["filename"].lower() for x in files]
        if names == [want]:
            return ok(pr=pr["number"])
        last_reason = (f"PR #{pr['number']} changes {len(names)} file(s): "
                       + ", ".join(f"`{n}`" for n in names[:6]) + (" …" if len(names) > 6 else ""))
    return fail(last_reason + f" — it must change **only** `{want}`.",
                "Make a clean branch from HQ: `git fetch upstream` → `git switch -c report upstream/main` → "
                f"`git restore --source=main -- agents/{c.login}.md` → `git add` it → commit → `git push -u origin report` → open a new PR (close the old one).")


def check_golive(c: Ctx):
    owner = c.fork.split("/")[0].lower()
    url = f"https://{owner}.github.io/{c.fork.split('/')[1]}/"
    body = c.http_get(url) if c.http_get else None
    if body is None:
        return fail(f"Nothing deployed at {url} yet.",
                    "Fork → Settings → Pages → Source: **GitHub Actions**. Then Actions → *Deploy Agent Card* → Run workflow.")
    if f'data-agent="{c.login.lower()}"' not in body.lower():
        return fail(f"{url} is up, but it is not your agent card.", "Run the *Deploy Agent Card* workflow again.")
    return ok(url=url)


CHECKS = {
    "identity": check_identity,
    "ghost": check_ghost,
    "precision": check_precision,
    "cloud": check_cloud,
    "branch": check_branch,
    "intel": check_intel,
    "machine": check_machine,
    "report": check_report,
    "golive": check_golive,
}


def _upstream_commits(self):
    if not hasattr(self, "_up_cache"):
        o = self.up.out("rev-list", "--all") or ""
        self._up_cache = set(o.split())
    return self._up_cache


Ctx._upstream_commits = _upstream_commits
