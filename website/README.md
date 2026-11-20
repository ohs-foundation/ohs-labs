# OHS Labs website

The micro-site for OHS Labs: quick AI experiments that could become future
Open Health Stack features. It lives in the `website/` folder of
[ohs-labs](https://github.com/ohs-foundation/ohs-labs), next to the
experiments themselves. Each experiment gets one markdown file in
`website/experiments/`. Netlify rebuilds the site on every push to `main` that
touches `website/`.

All paths below are relative to `website/`.

## Add an experiment

1.  Copy [`experiments/_template.md`](experiments/_template.md) to
    `experiments/<your-slug>.md`. The file name becomes the link:
    `/#/<your-slug>`.
2.  Fill in the front matter (title, stage, summary, links, ...) and write the
    body. Each `## Eyebrow | Heading` line starts a new white block.
3.  Check it locally (below), then open a pull request. Netlify posts a deploy
    preview on the PR. If the experiment's code lives in this repo too, link
    its folder from `links:`.

Files whose names start with `_` are not published.

## Stages

Set `stage:` to one of these. The cards, badges and filters follow it.

Stage         | Means
------------- | ---------------------------------------------------------------
`proposal`    | An idea we want to run. Looking for owners, data or a deployment.
`percolating` | Work in progress. A harness exists and early results are coming in.
`published`   | Results, code and write-up are public, so anyone can rerun them.
`graduated`   | It worked, and it now lives in an OHS project or pillar.

Move an experiment along by changing its `stage:` in a pull request.

## What you can put in the body

Shortcode         | Renders
----------------- | ----------------------------------------------------------
`{{kpis}}`        | Up to three headline numbers from `kpis:` in the front matter.
`{{chart:<id>}}`  | A chart from `charts:` (`grouped-bars`, `columns` or `race`).

Plain markdown works too: lists, links, tables, images (put files under
`assets/<your-slug>/` and link them as `assets/<your-slug>/file.png`).

Set `video:` to a YouTube or Vimeo link, or an `.mp4`/`.webm` under `assets/`,
to show it at the top of the overlay. Set `cover.image:` to use a picture
instead of the generated card art.

## Build and preview locally

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build.py            # writes dist/
.venv/bin/python -m http.server 8000 --directory dist
```

`python build.py --check` only validates the experiments; it fails with a list
of problems (unknown stage, missing title, a `{{chart:x}}` with no chart `x`).

## How it's built

-   `build.py` reads `experiments/*.md`, validates them, and fills
    `templates/index.html`. It writes one page, `dist/index.html`, plus a small
    share page per experiment at `dist/e/<slug>/` so links unfurl with the
    right title.
-   `assets/site.css` holds the OHS SF brand styles; `assets/site.js` runs the
    filters, the overlays and the charts.
-   `netlify.toml` tells Netlify to install `requirements.txt`, run
    `python build.py` and publish `dist/`.

## Deploy on Netlify

1.  In Netlify, **Add new site → Import an existing project**, pick GitHub and
    `ohs-foundation/ohs-labs`.
2.  Set **Base directory** to `website`. Leave the other build fields empty:
    they come from `website/netlify.toml`.
3.  Optional: add a custom domain such as `labs.ohs.foundation` under
    **Domain management**.
