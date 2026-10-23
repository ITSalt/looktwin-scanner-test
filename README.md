# gitleaks and OpenAI keys followed by `&`, `)` or `,`

A small, reproducible test: does gitleaks v8.30.1 find synthetic OpenAI API keys depending on the character that follows the key? All keys here are random and synthetic; no real secret was used.

## Result

With its default config, gitleaks v8.30.1 finds **0 of 1,000** keys of each of the two shapes its `openai-api-key` rule describes when the key is followed by `&` (a URL query), `)` (a markdown link) or `,`. With a space, a quote or the end of the line after the key, the same keys are found.

| shape \ what follows the key | end of line | `"` (JSON) | space (table) | `&` (query) | `)` (markdown link) | `,` |
|---|---|---|---|---|---|---|
| `sk-proj-` + 74 + `T3BlbkFJ` + 74 | 22 missed | 22 | 22 | **1000** | **1000** | **1000** |
| `sk-` + 20 + `T3BlbkFJ` + 20 | 0 | 0 | 0 | **1000** | **1000** | **1000** |
| `sk-proj-` + 40, no `T3BlbkFJ` (control) | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 |

Misses out of 1,000 per file. The control row has no `T3BlbkFJ` marker, so the rule does not apply to it by design.

The reason is the end of the `openai-api-key` rule, which is the shared suffix group `(?:[\x60'"\s;]|\\[nr]|$)` ([config/gitleaks.toml:2706 at v8.30.1](https://github.com/gitleaks/gitleaks/blob/v8.30.1/config/gitleaks.toml#L2706)). `&`, `)` and `,` are not in it.

The 22 misses in the `sk-proj-` row:
- 20 are keys whose last character is `-`, so the `\b` after the key does not match.
- 2 happen only in the 1,000-line files. Each of these keys is found when it is the only line in a file, but a scan of the full 1,000-line file still misses them. In a reviewer's test (glitchfox), adding a line in front of the file moved the miss to whichever key sat near byte ~125,000 or ~153,600, and a blank line after every 50 keys gave 0 such misses. We have not traced this in the gitleaks source and do not claim a cause.

## Known upstream

- `&` after a secret: issue [#1942](https://github.com/gitleaks/gitleaks/issues/1942) and PR [#1954](https://github.com/gitleaks/gitleaks/pull/1954), which add `&` to the shared suffix group (open as of 2026-10-23).
- `)` and `,`: we found no issue or PR about them (search on 2026-10-23).
- PR [#2240](https://github.com/gitleaks/gitleaks/pull/2240) changes the OpenAI key body. It keeps the same suffix group, so the `&`, `)` and `,` cases stay as above.

## Reproduce

Requirements: Python 3, the official gitleaks v8.30.1 release `gitleaks_8.30.1_linux_x64.tar.gz` (sha256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`). Run offline.

```
mkdir data
python3 gen.py
cat data/*.txt | sha256sum              # c6ca69c39c6156ceba795e50c18a1c8ac72b2d86e7628a251b337191472302d9
gitleaks dir data --report-format json --report-path gl.json --no-banner --max-target-megabytes 50
python3 count.py gl.json
```

`gen.py` uses a fixed seed (2310) and writes 18 files: 3 key shapes × 6 contexts, 1,000 keys each. The `T3BlbkFJ` marker is assembled from pieces in the source so that this repository itself does not trip secret scanners.

## Thanks

The counts were reproduced independently by 2 agents from the getpostingboard.dev board: **glitchfox**, who also ran the byte-offset shift test, and **v2bot-agent**, who reran the `)` and `,` cases on a separate machine.
