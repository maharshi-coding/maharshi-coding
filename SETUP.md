# MAHARSHI.EXE — Operator's Manual

This repository powers both the [GitHub profile](https://github.com/maharshi-coding) and the RPG console at **https://maharshi-coding.github.io/maharshi-coding/**.

The README is a Markdown-compatible console interface. The genuinely interactive game is in `docs/index.html`. Live data is represented by `docs/data/profile.json`, which is generated from GitHub. No paid hosting, Node build, database, or frontend dependencies are needed.

## What has already been committed

- `README.md` — character sheet, RPG map, raid log, game shelf, achievements, skill tree, snake
- `assets/rpg-boot.svg` — animated CRT boot sequence; reduced-motion fallback
- `assets/covers/*.svg` — original artwork for the eight public flagship cartridges
- `docs/index.html` — interactive mobile-ready terminal, keyboard history, command autocomplete, public project and PR explorer
- `docs/data/profile.json` — an initial snapshot of verified **public** GitHub metadata
- `scripts/generate_profile.py` — GitHub API generator for README sections + Pages data
- `.github/workflows/profile-rpg-sync.yml` — public metadata refresh every eight hours, on relevant pushes, and manually
- `.github/workflows/snake-rpg.yml` — contribution snake daily and manually; output branch
- `.github/workflows/rpg-check.yml` — static data and Python syntax checks

The old `sync-contributions.yml` workflow is retired because its markers don't match the new README.

## Manual step 1 — enable GitHub Actions write access (REQUIRED)

1. Open **Settings → Actions → General** in `maharshi-coding/maharshi-coding`.
2. Make sure the necessary GitHub Actions are allowed. If your policy requires specific actions, permit `actions/checkout`, `actions/setup-python`, `Platane/snk`, and `crazy-max/ghaction-github-pages`.
3. Under **Workflow permissions**, select **Read and write permissions**, then Save. The workflows explicitly request `contents: write`.
4. If your account or organization disables Actions by default, enable them for this repository.

The profile updater commits the README and JSON snapshot back to `main`. The snake job publishes an `output` branch. A branch protection or ruleset disallowing bot pushes may require an adjustment.

## Manual step 2 — enable GitHub Pages (REQUIRED for playable console)

1. Open **Settings → Pages** for this repository.
2. Under **Build and deployment**, set **Source: Deploy from a branch**.
3. Choose **Branch: main**, **Folder: /docs**, and Save.
4. Open **https://maharshi-coding.github.io/maharshi-coding/** after GitHub Pages reports a successful deployment.

A public repository is required for publicly accessible Pages on supported plans. The README's LAUNCH FULL CONSOLE link is already pointed to this address, but it does **not** imply Pages has been enabled yet.

## Manual step 3 — initialize scheduled data and snake (RECOMMENDED)

In the repository **Actions** tab, locate:

1. **Sync RPG profile data** → **Run workflow** (branch `main`). This updates the HUD, public projects, open/merged PRs, pinned loadout (when GraphQL is available), and the JSON file used by Pages. The schedule is every **8 hours**.
2. **Snake.exe — contribution mini-game** → **Run workflow**. This creates the `output` branch and the SVG that appears in the README. The schedule is daily.
3. Check the **RPG console quality gate** runs for syntax and snapshot checks.

All GitHub-generated indicators can change. GitHub Pages deployment and scheduled GitHub Actions may take some time to appear in GitHub's UI; inspect the workflow logs rather than assuming success.

## Optional PAT / token secret (NOT required for public REST data)

The workflow first checks **`GH_DATA_TOKEN`**, then **`GH_TOKEN`**, then the built-in **`GITHUB_TOKEN`**.

The built-in `GITHUB_TOKEN` should be sufficient for publicly accessible REST API repository/PR searches, but its permission scope and rate limits can vary. GraphQL pinned projects / contribution counts can also be permission-dependent.

If requests fail due to rate limiting or authorization, create a **fine-grained GitHub personal access token** with the minimum necessary *read* access to the relevant profile/public repository metadata and GraphQL information. Add it via **Settings → Secrets and variables → Actions → New repository secret**:

**Name:** `GH_DATA_TOKEN`  
**Value:** your token (never paste the token into a README, issue, terminal transcript, or code file).

For public REST-only use, a PAT is optional. If external PRs are not returned by the default token, an authenticated token may help. The generator is intentionally **public-only even with a more privileged token**: it rejects private repositories and PRs. Never add private data to a public GitHub profile.

## Run the generator locally

Prerequisite: Python **3.10 or newer**. No pip dependencies.

```bash
git clone https://github.com/maharshi-coding/maharshi-coding.git
cd maharshi-coding

# Inspect what will be queried, without writing files
python3 scripts/generate_profile.py --dry-run

# Generate README dynamic sections and Pages snapshot
python3 scripts/generate_profile.py

# Preview the playable website locally:
python3 -m http.server 8000 --directory docs
# Open http://localhost:8000
```

If you hit unauthenticated rate limits, supply a token through the environment:

```bash
export GH_DATA_TOKEN="YOUR_TOKEN_HERE"
python3 scripts/generate_profile.py
unset GH_DATA_TOKEN
```

Do not commit an API token. The script uses GitHub REST endpoints for public repos, authored public PR searches, profile creation date and project metadata. It attempts GitHub GraphQL for pinned repositories and total contributions over the trailing 365 days. If those GraphQL fields can't be retrieved, they remain explicitly **unavailable** rather than being fabricated.

## Customize the game without breaking auto-updates

- **Player identity and current quest:** edit the narrative copy in `README.md` and `docs/index.html`.
- **Flagship cartridges:** edit `FEATURED`, `TAGLINES`, and `EMOJI` in `scripts/generate_profile.py`. A featured repository must actually be public and must not be a fork.
- **Static cartridge artwork:** add or replace an `assets/covers/REPO_NAME.svg`. Cover names are case-sensitive.
- **Skill badges / game HUD frame:** change the static README design; generator only replaces content within the three marker pairs.
- **Interactive commands:** edit the JavaScript in `docs/index.html`. Project and PR data comes from the generated snapshot.

**Do not manually edit the text between these markers**, because the scheduled generator replaces it:

```text
<!--START_SECTION:prs-->
<!--END_SECTION:prs-->
<!--START_SECTION:projects-->
<!--END_SECTION:projects-->
<!--START_SECTION:hud-->
<!--END_SECTION:hud-->
```

## Data and source-of-truth rules

- Only public repos returned by GitHub API become public game cartridges. A fork is labeled and filed in the fork archive, not credited as an original product.
- A **PLAY** link is shown only for a suitable repository homepage or a separately verified live demo documented in the project's README (currently OSS-Agent). A GitHub/source URL is not automatically a playable app.
- GitHub **stars** are displayed as popularity signals, not invented review ratings.
- Merged and open PRs come from separate GitHub Search queries. A closed-without-merge PR is not a cleared bounty.
- The PR search is across publicly searchable repositories, not just the profile owner's repo. Private PRs are *not* published.
- The API snapshot is not a minute-by-minute live API request from each visitor: the Action refreshes every eight hours.
- Language inventory in the README counts primary-language labels among public, nonfork repositories. The third-party top-language image uses its own computation.
- `RamayanaGPT` is included as previously reported project lore, without a fabricated public CODE or PLAY link.
- `Software Developer @ Meeka` is shown because it was explicitly supplied as the current quest; it was not independently verified from GitHub metadata.
- Third-party typing/stats/trophy/streak/graph services can go down; core content and project source links remain readable.

## Troubleshooting

**Pages gives 404:** confirm Settings → Pages → Deploy from a branch → main /docs, then review the Pages deployment under Actions.

**Snake graphic is empty / 404:** run the snake workflow once and confirm that its `output` branch has `github-contribution-grid-snake.svg`. Ensure Actions can write to contents.

**PR generator fails with 403 or 422:** inspect API/rate-limit error in Actions logs. Retry with an authenticated `GH_DATA_TOKEN`. The generator never silently invents PR status.

**A project is missing:** it may be private, forked, archived, or absent from GitHub's API. Make it public intentionally before expecting it in the library; never publish private repositories accidentally.

**Pinned / annual contributions unavailable:** these depend on authenticated GitHub GraphQL. The README correctly shows an unavailable state until GraphQL provides values.

**Stats widgets do not render:** their external hosted service may be rate-limited; this does not mean README or GitHub data is broken.

**Local file opened directly as file:// fails:** serve `docs/` over http://localhost:8000 as shown above so that browser fetch can read `data/profile.json`.
