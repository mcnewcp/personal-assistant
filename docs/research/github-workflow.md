# How GitHub Projects (v2), Releases & Automations Work for a Solo Repo

**Date:** 2026-07-27 · **Context:** resolves GitHub issue #4 ("How GitHub Projects, Releases & automations work for a solo repo"); feeds the decision session in issue #5 ("Decide this repo's GitHub workflow"). All claims cite primary sources (docs.github.com, cli.github.com, official tool repos/docs) verified on 2026-07-27. Opinion/synthesis is explicitly marked.

## TL;DR

- **Projects v2** is a user- or org-level table/board/roadmap layered *on top of* issues and PRs — issues stay in the repo; the project is just a view with extra fields. One project can hold issues, PRs, and draft items, with multiple saved views (table, board, roadmap), custom fields (text, number, date, single-select, iteration), and built-in automations. On the Free plan the meaningful caps are **1 auto-add workflow per project** and **2 saved insight charts in private projects**; item capacity (50,000 incl. archive) is a non-issue solo.
- **Releases**: a GitHub Release wraps a git tag with notes and assets. `gh release create --generate-notes` gives near-zero-ceremony releases (it even creates the tag); `.github/release.yml` categorizes auto-notes by PR label. For more automation, **release-please** (release-PR model, Conventional Commits required) and **python-semantic-release** (direct-push model, Conventional Commits required) both bump the version in `pyproject.toml`/version files and cut the tag + release + changelog.
- **Actions beyond CI**: `schedule`, `workflow_dispatch`, `issues`/`issue_comment`, and `release` triggers cover most solo automation. Two structural gotchas: (1) events created with the default `GITHUB_TOKEN` **do not trigger other workflows** (so a release created by release-please with `GITHUB_TOKEN` won't fire your `on: release` publish job — use a PAT/GitHub App to change that), and (2) `GITHUB_TOKEN` **cannot touch Projects v2 at all** — project automation from Actions needs a PAT with `project` scope.
- **Solo-fit synthesis** (opinion): milestones + labels may already be enough; if you adopt Projects, one board with Status + auto-add + auto-archive is the whole setup; Conventional Commits is the toll you pay for release automation — skip it and `gh release create --generate-notes` still gets you 80%.

---

## 1. GitHub Projects (v2) fundamentals

### 1.1 What a project is, and how it relates to issues

A project is "an adaptable table, board, and roadmap that integrates with your issues and pull requests on GitHub … at the user or organization level" ([About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects)). Key mental model for a beginner:

- **Projects live on your *account*, not in a repo.** For a solo maintainer, you create a *user-level* project (`github.com/users/mcnewcp/projects/N`) and then *link* it to one or more repositories (the `gh project link` subcommand exists for exactly this — [gh project manual](https://cli.github.com/manual/gh_project)). Linking makes the project show up in the repo's Projects tab; the project itself can span multiple repos.
- **Items** are of three kinds: issues, pull requests, and **draft issues** (quick notes that exist only in the project until you optionally convert them to real issues). Field data syncs both ways between the project and the underlying issue/PR ([About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects)).
- **The issue remains the source of truth.** The project adds metadata (Status, dates, estimates…) that lives in the project, not on the issue. Deleting a project doesn't delete issues.
- Historical note: this is "Projects v2" (GraphQL type `ProjectV2`); the older "Projects (classic)" boards no longer appear in current docs — everything below is v2.

### 1.2 Layouts: table, board, roadmap

All three are layouts *of a view*, switchable per view ([Changing the layout of a view](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/changing-the-layout-of-a-view)):

| Layout | What it's for | Notes |
|---|---|---|
| **Table** | Spreadsheet-like triage/overview; "a powerful and adaptable spreadsheet comprised of your issues, pull requests, and draft issues" | Group, sort, filter, hide/show fields |
| **Board** | Kanban flow ("what's in progress right now") | Columns can be **any single-select or iteration field**, not just Status; dragging a card updates the field |
| **Roadmap** | Time-based planning | Positions items on a timeline using **custom date fields and/or iteration fields**; drag to change start/target dates; vertical *markers* can show milestones, iterations, and other date fields |

Roadmap only earns its keep if you assign dates or iterations to items — with no date/iteration fields it has nothing to plot.

### 1.3 Views

A project holds **multiple saved views**, each with its own layout, filter, grouping, sorting, and *slicing* (a side panel that breaks items down by one field) ([About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects); [Best practices](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects)). Typical solo pattern (opinion): one board view "Now", one table view "All / triage", optionally a roadmap view if you plan by dates.

### 1.4 Fields

Built-in and custom fields, up to 50 fields per project ([About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects); [Understanding fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields)):

- **Custom:** text, number, **date** (typed or calendar), **single select** (options with color + description), **iteration** (repeating time blocks for sprint-style planning).
- **Built-in:** the **Status** single-select (the field the default automations set), plus read-only fields surfaced from the item itself — assignees, labels, milestone, repository, linked PRs, parent issue / sub-issue progress, issue type, reviewers ([Understanding fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields)).

### 1.5 Built-in workflows (project automations)

Projects ship with point-and-click automations — no Actions YAML involved ([Using the built-in automations](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations)):

- **Enabled by default:** when an issue/PR in the project is **closed → Status = Done**; when a PR is **merged → Status = Done**.
- Also available: **item added → set Status** (e.g. Todo), item reopened → set Status, code changes requested/approved → set Status, and **auto-close issue when Status is set to a chosen value** (the doc lists "close issues when project status changes").
- **Auto-add** ([Adding items automatically](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/adding-items-automatically)): watches a repo and adds matching items on create/update. Filter supports a *subset* of qualifiers: `is:` (open/closed/merged/draft/issue/pr), `label:`, `reason:`, `assignee:`, `no:`, with negation (`-label:bug`). **Pre-existing matching items are NOT back-filled** — only items created/updated after enabling. Limits per project: **GitHub Free = 1 auto-add workflow; Pro/Team = 5; Enterprise = 20.**
- **Auto-archive** ([Archiving items automatically](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/archiving-items-automatically)): filters on `is:`, `reason:`, and `updated:` (e.g. `is:closed updated:<@today-2w`). Archived items keep all field data and can be restored from the archive page. Capacity: **a project holds up to 50,000 items across active views + archive**; beyond that you must permanently delete.
- Separate from Projects: linking a PR to an issue with a closing keyword ("Fixes #12") closes the issue when the PR merges into the default branch ([Linking a PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue)) — which then cascades into the project's "closed → Done" workflow.

### 1.6 Free-plan limits relevant to a solo user

| Thing | Free-plan reality | Source |
|---|---|---|
| Number of projects | No documented cap found in current docs (see "Could not verify" below) | — |
| Auto-add workflows per project | **1** | [Adding items automatically](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/adding-items-automatically) |
| Items per project (active + archived) | 50,000 | [Archiving items automatically](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/archiving-items-automatically) |
| Fields per project | 50 | [About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) |
| Saved insight charts, **private** projects | 2 (unlimited needs Pro for users / Team for orgs) | [About insights](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/about-insights-for-projects) |
| Historical (burn-up) charts | Team / Enterprise Cloud for organizations — not on Free | [About insights](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/about-insights-for-projects) |

### 1.7 Scripting: `gh project` CLI and the GraphQL API

- The CLI has 19 subcommands: `create/list/view/edit/close/copy/delete`, `field-create/field-list/field-delete`, `item-add/item-create/item-edit/item-list/item-archive/item-delete`, `link/unlink`, `mark-template` ([gh project manual](https://cli.github.com/manual/gh_project)). **Token scope:** "The minimum required scope for the token is: `project`" — add it with `gh auth refresh -s project`.
- The GraphQL API exposes `ProjectV2` with mutations like `addProjectV2ItemById`, `addProjectV2DraftIssue`, `updateProjectV2ItemFieldValue`, `deleteProjectV2Item`; classic PATs need `project` scope (`read:project` for read-only). You cannot add and update an item in the same call ([Using the API to manage Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)).
- Bottom line: everything you can click, you can script — but always with a `project`-scoped token, never the Actions `GITHUB_TOKEN` (see §3.3).

### 1.8 Insights/charts on Free

Current charts (snapshot bar/column/etc. with filters) are available everywhere; on Free you can **save only 2 charts in private projects**; **historical** charts (burn-up over time) require Team/Enterprise Cloud for organizations ([About insights for Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/about-insights-for-projects); [Creating charts](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/creating-charts)). For a solo repo, treat insights as a nice-to-have, not a plan driver (opinion).

---

## 2. Releases for a Python project

### 2.1 Git tags vs GitHub Releases

- A **git tag** marks a commit; a **GitHub Release** is a first-class object *based on* a tag that adds release notes, up to 1,000 binary assets (2 GiB each), and auto-generated source zip/tarball; watchers can subscribe to release-only notifications ([About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)).
- **Annotated vs lightweight tags** ([Pro Git — Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)): annotated tags (`git tag -a v1.4 -m "..."`) are full objects with tagger, date, message, and optional GPG signature; lightweight tags (`git tag v1.4`) are bare pointers. Pro Git: "It's generally recommended that you create annotated tags so you can have all this information." Note that tags created *by* GitHub (release UI, `gh release create`) are created server-side from the ref you specify.

### 2.2 `gh release create` mechanics

From the [gh release create manual](https://cli.github.com/manual/gh_release_create):

- "If a matching git tag does not yet exist, one will automatically get created from the latest state of the default branch" — override the commit with `--target`, or require an existing tag with `--verify-tag`.
- `--generate-notes` auto-generates title + notes via the release-notes API; `--notes` text is *prepended* to generated notes; `--notes-start-tag` controls the changelog window; `--notes-from-tag` pulls notes from an annotated tag message.
- `--draft`, `--prerelease`, `--latest[=false]`, and asset upload (`gh release create v1.2.3 dist/* `) round out the flow.

So the minimal manual release is literally: `gh release create v0.2.0 --generate-notes`.

### 2.3 Automatically generated release notes and `.github/release.yml`

Auto-notes are built from **merged pull requests** (plus contributors and a full-changelog link) — direct commits without PRs won't be itemized ([Automatically generated release notes](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)). Customize with `.github/release.yml`:

```yaml
changelog:
  exclude:
    labels: [ignore-for-release]
  categories:
    - title: Breaking Changes
      labels: [Semver-Major]
    - title: New Features
      labels: [Semver-Minor]
    - title: Other Changes
      labels: ["*"]      # catch-all
```

`changelog.exclude` drops PRs by label or author; each category matches PRs by label, `*` catches the rest ([same page](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)). Implication for this repo (opinion): auto-notes are only as good as your PR + label discipline; if you commit straight to `main`, notes degrade to a compare link.

### 2.4 release-please

[googleapis/release-please](https://github.com/googleapis/release-please) automates the whole cycle via the **Release PR** model:

1. It parses **Conventional Commits** on your default branch (`feat:`, `fix:`, `deps:` are releasable; `chore:`/`build:` are not; `feat!:` / `BREAKING CHANGE:` footer → major bump; a `Release-As: x.y.z` footer forces a version).
2. It maintains an always-up-to-date **release PR** containing the CHANGELOG.md update and version-file bumps.
3. **When you merge that PR**, it tags the commit and creates the GitHub Release ([README](https://github.com/googleapis/release-please)).

- **Python support:** the `python` release type targets "a Python repository, with a setup.py, setup.cfg, CHANGELOG.md and optionally a pyproject.toml and a `<project>/__init__.py`" ([customizing.md](https://github.com/googleapis/release-please/blob/main/docs/customizing.md)) — i.e. it bumps the version string in `pyproject.toml`/`setup.py`/`__init__.py` where present.
- **Action:** run it from CI as [`googleapis/release-please-action@v4`](https://github.com/googleapis/release-please-action) on `push` to `main`, with `permissions: contents: write, pull-requests: write` (their example also grants `issues: write`). Config lives in `release-please-config.json` + `.release-please-manifest.json` (optional for single-package repos — you can just pass `release-type: python`).
- **Token caveat** (from the action README): with the default `GITHUB_TOKEN`, "events triggered by the `GITHUB_TOKEN` will not create a new workflow run" — so CI won't run on the release PR and the created release won't trigger `on: release` workflows; use a PAT secret if you need that ([release-please-action](https://github.com/googleapis/release-please-action); see §3.2).
- **Maintenance status:** as of 2026-07-27 both repos are active (release-please ~7.3k stars, 1,400+ commits; the action showing recent commits, v4 current). No archive/deprecation notice on either repo.

### 2.5 python-semantic-release

[python-semantic-release](https://python-semantic-release.readthedocs.io/en/latest/) (PSR, v10.x) is the direct-push alternative:

- Parses commit messages (Conventional Commits by default; other parsers available), computes the next version, stamps it into project files (`pyproject.toml` etc.), generates the changelog, **commits directly to the branch, tags, and pushes** — no release PR step ([docs](https://python-semantic-release.readthedocs.io/en/latest/); [GitHub Actions guide](https://python-semantic-release.readthedocs.io/en/latest/configuration/automatic-releases/github-actions.html)).
- Config lives in `pyproject.toml` under `[tool.semantic_release]`.
- Actions usage: `python-semantic-release/python-semantic-release@vX` with `contents: write` (+ `id-token: write` in their example); a companion `python-semantic-release/publish-action` uploads dists to the GitHub Release. If the branch is protected, `GITHUB_TOKEN` may not be able to push and you need a PAT ([GitHub Actions guide](https://python-semantic-release.readthedocs.io/en/latest/configuration/automatic-releases/github-actions.html)).
- Difference vs release-please in one line: **release-please gives you a human checkpoint (merge the release PR); PSR releases the instant you push to main.**

### 2.6 git-cliff and plain manual tagging

- [git-cliff](https://git-cliff.org/docs/) is a **changelog generator only**: it turns (conventional or regex-matched) commit history into a templated CHANGELOG via `cliff.toml`. It does not bump versions or create GitHub Releases — you'd pair it with manual tagging or other tooling.
- **Plain manual**: `git tag -a vX.Y.Z && git push --tags` or just `gh release create vX.Y.Z --generate-notes`. Zero new conventions required; version bumps in `pyproject.toml` are on you.

Trade-offs are tabulated in §4.5.

### 2.7 Publishing to PyPI (if ever): Trusted Publishing

If this project ever ships to PyPI: **Trusted Publishing** exchanges a GitHub Actions OIDC token for a 15-minute PyPI upload token — no long-lived API token secrets. Configure the publisher on PyPI (repo, workflow filename, optional environment), then use [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish) with `permissions: id-token: write`; a dedicated GitHub *environment* (e.g. `pypi`) is recommended as an extra gate ([PyPI docs: Trusted Publishers](https://docs.pypi.org/trusted-publishers/)). Note the §3.2 rule: if the release is created by a workflow using `GITHUB_TOKEN`, an `on: release` publish workflow will NOT fire — either publish in the same workflow, trigger on `push: tags`, or use a PAT/App token to create the release.

---

## 3. GitHub Actions beyond plain CI

### 3.1 Event triggers useful for repo automation

From [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows):

- **`schedule`** — POSIX cron (5 fields), shortest interval 5 minutes, optional IANA timezone. Caveats: "can be delayed during periods of high loads" (don't build anything time-critical on it); runs only against the latest commit on the **default branch**; and "in a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days."
- **`workflow_dispatch`** — manual run from UI/CLI/API with typed inputs (`choice`, `boolean`, `environment`; max 25 inputs). The solo maintainer's best friend for "run this chore now" buttons.
- **`issues`** — activity types include `opened`, `edited`, `closed`, `reopened`, `labeled`, `unlabeled`, `assigned`, `milestoned`, … (e.g. auto-label or auto-comment on new issues).
- **`issue_comment`** — fires for comments on both issues and PRs; distinguish with `github.event.issue.pull_request`.
- **`label`** — label created/edited/deleted.
- **`release`** — types `published`, `created`, `released`, `prereleased`, …; docs recommend subscribing to **`published`** to catch both stable and pre-releases.
- **`repository_dispatch`** — your own webhook: POST to the API with an `event_type` + `client_payload` to trigger from outside GitHub.

### 3.2 GITHUB_TOKEN: permissions and the recursive-trigger rule

- Every workflow gets an automatic `GITHUB_TOKEN`; scope it per-workflow/job with the `permissions:` block (available scopes include `contents`, `issues`, `pull-requests`, `actions`, `pages`, `id-token`, … — **there is no `projects` scope in the list**) ([Workflow syntax — permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax); [Automatic token authentication](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication)). Defaults come from repo/org settings ("initially set to the default setting for the enterprise, organization, or repository"); best practice is to declare an explicit least-privilege `permissions:` block per workflow.
- Why release-please needs `contents: write` (push tags/commits, create releases) and `pull-requests: write` (open/update the release PR) ([release-please-action](https://github.com/googleapis/release-please-action)).
- **The recursive-trigger prevention rule** ([GITHUB_TOKEN concepts](https://docs.github.com/en/actions/concepts/security/github_token); [Triggering a workflow from a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)): "events triggered by the `GITHUB_TOKEN` will not create a new workflow run," excepting `workflow_dispatch` and `repository_dispatch`. Consequences: a release, label, or comment created by a workflow with `GITHUB_TOKEN` will not fire other workflows listening for those events. **Workaround:** use a PAT or a GitHub App installation token stored as a secret.
- **Projects v2 blind spot:** `GITHUB_TOKEN` has no projects permission (see scope list above), and project APIs require a token with `project` scope ([Using the API to manage Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)). So *any* Actions workflow that adds/edits project items — including [`actions/add-to-project`](https://github.com/actions/add-to-project), whose README says "github-token is a personal access token with repo and project scopes" — needs a PAT (classic: `project`, plus `repo` for private repos) or a GitHub App token. For user-owned projects, prefer the built-in auto-add workflow (§1.5) before reaching for this.

### 3.3 Useful automation actions & runner facts

- [`actions/stale`](https://github.com/actions/stale) — marks then closes inactive issues/PRs (`days-before-stale: 60`, `days-before-close: 7`, exempt labels, custom messages), run on a daily cron. Active, v11 current. (Opinion: on a solo repo where every issue is yours, stale bots mostly add noise — skip unless the backlog rots.)
- [`actions/add-to-project`](https://github.com/actions/add-to-project) — adds issues/PRs to a Project v2, optionally filtered by labels with AND/OR/NOT. **Not archived/deprecated as of 2026-07-27** (checked repo + README — no maintenance notice). Requires the PAT described above; its one advantage over built-in auto-add is richer label logic and no 1-workflow Free cap.
- **`gh` is preinstalled on all GitHub-hosted runners** — authenticate steps with `env: GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` ([Using GitHub CLI in workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-github-cli)). For one-off automation, a `gh` one-liner in a workflow beats hunting for a marketplace action (opinion).

### 3.4 Costs (Free plan)

Actions on **public repos: free** (standard runners). Private repos on Free: **2,000 minutes + 500 MB artifact storage/month** (Pro: 3,000 min / 1 GB); Linux is the 1x baseline, Windows ~2x, macOS ~10x ([About billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)). For a private solo repo with light CI, 2,000 Linux minutes is generous.

---

## 4. Lightweight conventions for solo repos (options, not prescriptions)

Everything in this section is **synthesis/opinion informed by the sourced facts above**, except where a link says otherwise.

### 4.1 Do you even need Projects?

- **Issues + labels only.** You already have triage labels (see `docs/agents/triage-labels.md`). Filtered issue searches (`is:open label:X`) cover a lot. Zero new surface area.
- **+ Milestones** — the built-in lighter-weight grouping: per-repo buckets with optional due date, completion %, and drag-to-prioritize ordering ([About milestones](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones)). Good for "v0.2" or "Q3 cleanup" style batching without any new UI to maintain. Limits: one milestone per issue, no board/timeline visualization.
- **+ a Project** buys you: a kanban board (visual WIP), custom fields (priority, size, dates), draft items (jot ideas without polluting Issues), roadmap timeline, and set-and-forget automations (auto-add, closed→Done, auto-archive). Cost: one more place to look, and automations that only cover *one* auto-add filter on Free (§1.6).
- Honest trade-off: for a single-repo, single-human backlog, a project is mostly a *nicer lens* on the same issues. It becomes clearly worth it if you (a) want a board you actually glance at, (b) plan by dates/iterations, or (c) accumulate draft ideas faster than you file issues.

### 4.2 Minimal Projects setup pattern (if adopted)

1. One **user-level project**, linked to `mcnewcp/personal-assistant`; private.
2. Keep the default **Status** field (Todo / In Progress / Done); resist adding fields until a real need shows up (50-field cap is irrelevant; attention is the scarce resource).
3. Enable three built-in workflows: **auto-add** (`is:issue is:open` — your single Free-plan slot, §1.5), **closed/merged → Done** (already on by default), **auto-archive** (`is:closed updated:<@today-2w`).
4. Two views: Board (grouped by Status) + Table (all items, for triage). Add a Roadmap view only if you start setting target dates.
5. Script anything else with `gh project item-add/item-edit` after `gh auth refresh -s project` (§1.7).

### 4.3 Conventional Commits: what it buys vs the discipline cost

The [spec](https://www.conventionalcommits.org/en/v1.0.0/) (`type(scope)!: description`; `fix:`→PATCH, `feat:`→MINOR, `!`/`BREAKING CHANGE`→MAJOR) exists precisely to enable "automatically generating CHANGELOGs" and "automatically determining a semantic version bump." Both release-please and python-semantic-release depend on it (§2.4–2.5).

- **Buys:** hands-free versioning + changelog; greppable history; the spec's FAQ notes a squash-merge workflow lets you fix up messages at merge time.
- **Costs:** every commit (or at least every squash-merge) message must conform, forever; a mistyped prefix silently miscategorizes or omits a change; solo, there's no reviewer to catch it. If you won't reliably write `feat:`/`fix:`, the automation output will be wrong-ish and manual `gh release create --generate-notes` (which keys off PR titles/labels instead, §2.3) is the honest choice.

### 4.4 Branch protection / rulesets for solo

- On the **Free plan, protected branches are public-repo-only**; private repos need Pro ([GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)). Rulesets are the modern replacement for classic branch protection, with bypass lists that can include the repo admin role ([About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)).
- Solo synthesis: a "require PR + passing checks" rule with **yourself on the bypass list** gives a guardrail against accidental force-pushes while keeping the escape hatch. Merge queues, required reviewers, CODEOWNERS: overkill for one person. If the repo is private on Free, this is moot — rely on habits (`git push --force-with-lease`, PRs when you want CI gating).

### 4.5 Release strategy trade-off table

| | **Manual: `gh release create --generate-notes`** | **release-please (action v4)** | **python-semantic-release** |
|---|---|---|---|
| Ceremony per release | One command, you pick the version | Merge the auto-maintained release PR | Zero — releases on push to main |
| Conventional Commits required | No (notes come from merged PRs / compare link) | Yes | Yes (default parser) |
| Version bumped in `pyproject.toml` | You edit it (or don't) | Yes, in release PR ([python type](https://github.com/googleapis/release-please/blob/main/docs/customizing.md)) | Yes, direct commit ([docs](https://python-semantic-release.readthedocs.io/en/latest/)) |
| CHANGELOG.md in repo | No (notes live on the Release) | Yes | Yes |
| Human checkpoint before release | Yes (you run the command) | Yes (PR merge) | No — every qualifying push releases |
| Setup | `.github/release.yml` optional | Workflow + (optionally) config/manifest JSON | `[tool.semantic_release]` in pyproject + workflow |
| Failure modes | Forgetting to release; version drift | Token gotcha (§2.4); mislabeled commits | Pushes to main from CI; mislabeled commits; protected-branch token issues |
| Fits when… | Releases are rare/informal | You want tidy versioned history w/ control | You want releases fully out of mind |

(git-cliff is orthogonal: changelog file only, pairs with the manual column — [git-cliff docs](https://git-cliff.org/docs/).)

---

## Options for this repo

Four coherent bundles, no winner picked. All assume the existing issue-tracker + triage-label conventions stay.

### Option A — Minimal: issues + milestones + manual releases
Milestones for batching (due date + completion %), labels for triage, `gh release create vX.Y.Z --generate-notes` when something's worth tagging, optional `.github/release.yml` for note categories. **No Projects, no Conventional Commits, no new tokens.**
*Pros:* zero new concepts; nothing to maintain; every piece is repo-native. *Cons:* no board/timeline view; version in `pyproject.toml` is hand-edited; release notes quality depends on PR discipline.

### Option B — Single project board, manual releases
Option A + the §4.2 minimal project (one user project, Status board, auto-add + closed→Done + auto-archive built-in workflows). Releases stay manual.
*Pros:* visual WIP + draft-idea capture for ~15 minutes of setup; automations are click-configured, no PAT needed (built-in workflows, not Actions). *Cons:* one more surface; Free plan caps you at 1 auto-add filter and 2 saved private charts; project fields are invisible from plain issue lists.

### Option C — Project board + release-please
Option B + Conventional Commits + [`googleapis/release-please-action@v4`](https://github.com/googleapis/release-please-action) (`release-type: python`) on push to main. Merge the release PR when you feel like shipping; CHANGELOG.md and `pyproject.toml` stay correct automatically.
*Pros:* versioned history with a human checkpoint; changelog for free. *Cons:* commit-message discipline forever; needs `contents+pull-requests write`; if anything must run *on* the release event (e.g. future PyPI publish), you'll need a PAT/App token or same-workflow publishing (§3.2).

### Option D — Full automation: python-semantic-release (+ Trusted Publishing later)
Conventional Commits + PSR releasing directly on every qualifying push to main; add `pypa/gh-action-pypi-publish` with OIDC + a `pypi` environment if the project ever publishes. Projects optional (combine with B's board if desired).
*Pros:* releases require literally no action; version/changelog always current. *Cons:* least forgiving — a sloppy `feat:` commit ships a release; CI pushes commits to main (awkward with any future branch rules); most moving parts of the four.

**Decision levers for issue #5** (synthesis): (1) Will you actually look at a board? → B/C/D vs A. (2) Will you reliably write `feat:`/`fix:` prefixes? → C/D vs A/B. (3) Do you want a checkpoint before each release? → C over D. (4) Is this repo ever publishing artifacts? → pre-wire D's publishing story, else ignore §2.7.

---

## Recent changes & things not verified against a primary source

- **Verified current (2026-07-27):** release-please-action v4 and actions/add-to-project are active with no deprecation notices; actions/stale is at v11 (recently moved to ESM/Node 24); PSR docs at v10.6.1.
- **Could not verify:** a documented cap on the *number* of Projects per account on Free (none found in current docs — treated as effectively unlimited); the exact current default `GITHUB_TOKEN` permission set for new repos (docs only say the default comes from enterprise/org/repo settings — declare explicit `permissions:` and it doesn't matter); precise ruleset availability wording for Free-plan public repos (the plans page confirms protected branches on private repos require Pro, but the rulesets page fetched emphasized Team/Enterprise features).
- **Recent-ish behavior worth knowing:** auto-add does not back-fill pre-existing items (§1.5); project item capacity is now 50,000 including archive (§1.5); scheduled workflows auto-disable after 60 days of inactivity in public repos (§3.1).
