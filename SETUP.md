# GitHub Profile & Portfolio — Setup

This repository powers two views of the same public engineering work:

- **GitHub profile README:** https://github.com/maharshi-coding
- **Interactive portfolio explorer:** https://maharshi-coding.github.io/maharshi-coding/

The README is deliberately simple and scannable. The website offers project search, category filters, a light/dark theme toggle, a project details dialog, and merged/open PR filters. Both are backed by the same public GitHub metadata.

## Repository structure

| File | Purpose |
| :-- | :-- |
| `README.md` | Developer profile, selected original projects, upstream PR history, background |
| `assets/profile-header.svg` | Professional animated header with reduced-motion support |
| `docs/index.html` | Accessible HTML portfolio layout |
| `docs/assets/styles.css` | Responsive light/dark theme |
| `docs/assets/app.js` | Search, filters, dialog, status tabs, theme preferences, and GitHub data rendering |
| `docs/data/profile.json` | Public GitHub API snapshot powering the website |
| `scripts/generate_profile.py` | Generates the README sections and the JSON data |
| `.github/workflows/profile-sync.yml` | Refreshes GitHub data every 8 hours, on relevant pushes, or manually |
| `.github/workflows/site-check.yml` | Validates source, JSON, generator, markers, and JavaScript |

No Node build step, paid hosting, external UI framework, or JavaScript libraries are required. Python 3.10+ is needed to refresh the data locally.

## Activate GitHub Pages

**Manual step (if it is not already enabled):**

1. Open https://github.com/maharshi-coding/maharshi-coding/settings/pages
2. Under **Build and deployment**, set **Source** to `Deploy from a branch`.
3. Choose branch `main` and folder `/docs`, then save.
4. Verify that the **pages build and deployment** workflow passes at https://github.com/maharshi-coding/maharshi-coding/actions.
5. Visit https://maharshi-coding.github.io/maharshi-coding/.

The Pages site may show a 404 until a first successful deployment. The profile README is independent of Pages activation.

## Enable automatic GitHub data refresh

The workflow uses `contents: write` to update README sections and the JSON snapshot.

**Manual step (if repository policy prevents writing):** Open **Settings → Actions → General** and enable **Read and write permissions** for workflows. Some branch protection rules may prevent bot commits; adjust those rules for this repository if necessary.

Then open **Actions → Refresh GitHub portfolio data → Run workflow**. Scheduled refreshes occur every 8 hours, and relevant source changes also trigger a refresh. The workflow retries on concurrent pushes, regenerating from the latest `main` to avoid overwriting manual changes.

### Optional access token

Ordinary publicly searchable repositories and PRs can be retrieved using the default GitHub Actions `GITHUB_TOKEN`. If GitHub rate limits or denies GraphQL metadata, optionally create a **fine-grained personal access token** granting only the read access needed, then add it at:

**Settings → Secrets and variables → Actions → New repository secret**  
Name: `GH_DATA_TOKEN`

Never publish or commit the token. A token does **not** authorize this public portfolio to expose private repository information; the generator explicitly excludes private records.

## Preview locally

```bash
git clone https://github.com/maharshi-coding/maharshi-coding.git
cd maharshi-coding

# Preview GitHub metadata without writing:
python3 scripts/generate_profile.py --dry-run

# Update README and website JSON using public GitHub API records:
python3 scripts/generate_profile.py

# Start a local static server:
python3 -m http.server 8000 --directory docs
# Open http://localhost:8000/
```

The website will not load its JSON correctly if you open `docs/index.html` directly from the filesystem with a `file://` URL. Use the local HTTP server.

## Customize without breaking sync

Edit **outside** these generated README markers:

```text
<!--START_SECTION:projects-->
<!--END_SECTION:projects-->
<!--START_SECTION:prs-->
<!--END_SECTION:prs-->
<!--START_SECTION:hud-->
<!--END_SECTION:hud-->
```

The generator replaces only the text between each pair. All static prose and layout outside these markers are kept.

- `FEATURED` and `TAGLINES` in `scripts/generate_profile.py` control what shows first.
- The website categorization is in `docs/assets/app.js`. Updates to the featured list in Python should be mirrored in `FEATURED_ORDER` in JavaScript.
- `docs/assets/styles.css` defines both light and dark themes.
- `docs/index.html` controls page structure and narrative copy.

### Data integrity

- **Original work vs forks:** forks are distinct from original projects.
- **PR status:** merged and open are queried independently. Closed without merging is never counted as merged.
- **Upstream vs own:** PRs to external owners are labeled upstream; PRs in this account's own namespace appear separately.
- **Projects:** only publicly visible repository entries are published. A private project is not linked as though it were public.
- **Stars:** counts come from GitHub, not fabricated review ratings.
- **Demo links:** displayed only for a suitably verified public homepage or a verified project demo URL.
- **Pinned repos and annual contribution count:** these depend on GitHub GraphQL. Missing fields are shown as unavailable, not estimated.
- **Snapshot recency:** the website reads a generated JSON snapshot, not live GitHub API calls from each visitor.

## Troubleshooting

- **Pages 404:** inspect Settings → Pages and the latest Pages workflow.
- **Missing public project:** verify that it is public and has been refreshed through the GitHub workflow.
- **GitHub data not loading on the website:** check whether `docs/data/profile.json` is published in the Pages build.
- **Status tab seems outdated:** run the data refresh workflow manually and inspect any API errors.
- **A workflow fails:** open its logs. The quality checks validate JavaScript with `node --check` and verify the JSON and README markers.

The previous game-console theme, RPG banner, cartridge artwork and snake animation are intentionally no longer part of the active portfolio.
