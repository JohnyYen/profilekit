# Terminal portfolio — a reference consumer

This is the maintainer's own portfolio, kept in this repository as a **worked
example of consuming the profilekit output contract**.

It is deliberately **not part of the distributed package**. Installing
`profilekit` does not install this app, and nothing here is importable from
it. The package produces data; this is one of many possible things that read
that data.

So it keeps the maintainer's name, links, and styling. Parametrising those
would turn a concrete example into an abstract template, and an abstract
template teaches less. If you are adopting profilekit, you bring your own
frontend — this is here to show you what reading the contract looks like in
practice, not to be the frontend you use.

## What to look at

The interesting part is the boundary, not the UI:

| File | What it demonstrates |
|---|---|
| `app/data/*.json` | The four JSON artifacts a `filesystem` destination writes. **Generated — never edit these by hand.** |
| `app/components/tui/sections/` | Rendering each artifact shape |
| `app/api/github/route.ts` | Treating the published data as a fallback behind a live API |
| `app/commands/index.ts` | Reading `about.json` and `social.json` for a command surface |

The shapes those files consume are specified in
[`docs/data-contract.md`](../../docs/data-contract.md). Read that rather than
reverse-engineering this app — it is the contract, and it tells you which
changes are safe and which bump the version.

## How the data gets here

```
data/*.json  ──▶  profile generate  ──▶  output/
                                    └──▶  profile publish  ──▶  app/data/*.json
```

`app/data/` is written by the `portfolio-data` destination declared in the
repository root's `profile.toml`. It is a **publish** target, not a generate
target: generation only ever writes inside `output/`, and anything that
crosses into another directory goes through the publication layer.

`profile check` fails if the committed `app/data/` has drifted from the
canonical data, so the two cannot silently disagree.

## Running it

```sh
pnpm install
pnpm dev          # http://localhost:3000
pnpm build
```

Node 22 and pnpm 10. The app is built in CI by
`.github/workflows/portfolio.yml`.

## Stack

Next.js (App Router), React, TypeScript, Tailwind. Two interaction modes — a
terminal emulator and a TUI — sharing one data layer, which is the part worth
copying: the shapes drive both, and neither knows where the data came from.
