# x402 Identity WG use cases

Draft use cases for the x402 Identity Working Group, drawn as payment-flow swimlanes and published for comment at **https://robdhyman.github.io/x402/**.

Working material, not a specification.

## Take part

- **Comment** on any case page (GitHub login). Threads live in [Discussions](https://github.com/robdhyman/x402/discussions).
- **Raise a tension** when two needs conflict: use the button on the case page. Tensions are [issues labelled `tension`](https://github.com/robdhyman/x402/issues?q=label%3Atension). A case is done when it has no open tension except those labelled `non-blocking`.
- **Suggest an edit**: each case is one file in [`use-cases/`](use-cases). Edit it and open a pull request. The file's history is the case's version history.

## Layout

| Path | What it holds |
|---|---|
| `use-cases/<id>.json` | One use case each. `k0.json` also carries the shared spine every case overrides. `_order.json` sets the page order. |
| `boards/` | `build_family.py` draws the swimlanes; `verify_arrows.py` checks every arrow against the x402 message whitelist; `export/*.png` are the 2x images for Google Docs and link previews. |
| `evidence/quotes.json` | Every recorded meeting quote: speaker, date, time offset, text. Generated, do not edit by hand. |
| `evidence/changes.json` | The change log: who asked for what, and what changed. Generated. |
| `site/` | `build.py` writes the site to `_site/`; `config.json` holds the repo name and comment-thread numbers. |
| `tools/extract_quotes.py` | Regenerates `evidence/` from the private evidence ledger. Transcripts and the ledger stay off GitHub. |

## Build

```bash
python3 site/build.py
```

Open `_site/index.html`. Pushing to `main` publishes; so does opening, closing or relabelling a tension.

## Add a use case

1. Copy a file in `use-cases/`, give it a new `id` (`uc1-4` becomes the page `/uc/1.4/`), and add the id to `_order.json`.
2. Create a Discussion for it and add its number to `site/config.json` under `discussions`.
3. Create the label `uc:1.4`.
