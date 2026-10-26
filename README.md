# gitleaks and OpenAI keys followed by `&`, `)` or `,`

A small, reproducible test: does gitleaks v8.30.1 find synthetic OpenAI API keys depending on the character that follows the key? All keys here are random and synthetic; no real secret was used.

## Result

With its default config, gitleaks v8.30.1 finds **0 of 1,000** keys of each of the 2 shapes its `openai-api-key` rule describes when the key is followed by `&` (a URL query), `)` (a markdown link) or `,`. With a space, a quote or the end of the line after the key, the same keys are found, except 22 of 1,000 `sk-proj-` keys (see below).

| shape \ what follows the key | end of line | `"` (JSON) | space (table) | `&` (query) | `)` (markdown link) | `,` |
|---|---|---|---|---|---|---|
| `sk-proj-` + 74 + `T3BlbkFJ` + 74 | 22 missed | 22 | 22 | **1000** | **1000** | **1000** |
| `sk-` + 20 + `T3BlbkFJ` + 20 | 0 | 0 | 0 | **1000** | **1000** | **1000** |
| `sk-proj-` + 40, no `T3BlbkFJ` (control) | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 |

Misses out of 1,000 per file. The control row has no `T3BlbkFJ` marker, so the rule does not apply to it by design.

The reason is the end of the `openai-api-key` rule, which is the shared suffix group `(?:[\x60'"\s;]|\\[nr]|$)` ([config/gitleaks.toml:2706 at v8.30.1](https://github.com/gitleaks/gitleaks/blob/v8.30.1/config/gitleaks.toml#L2706)). `&`, `)` and `,` are not in it.

The 22 misses in the `sk-proj-` row:
- 20 are keys whose last character is `-`, so the `\b` after the key does not match.
- 2 are keys that span a fragment cut (see the next section).

The 3 files are 169,000 to 175,000 bytes long and have no blank line, so gitleaks cuts each of them at bytes 125,000 and 153,672. The keys across those cuts are lines 740 and 910 in the end-of-line file, 719 and 884 in the JSON file, and 715 and 879 in the table file. Each of them is found when it is the only line in a file. In a reviewer's test (glitchfox), a line added in front of the file moved the miss to whichever key then sat on a cut, and a blank line after every 50 keys gave 0 such misses.

## Keys missed at fragment cuts in large files

Same synthetic keys and default config as above. With `gitleaks dir` and `gitleaks stdin`, v8.30.1 reads a file in fragments. `fileFragments` ([sources/file.go](https://github.com/gitleaks/gitleaks/blob/v8.30.1/sources/file.go)) reads 100,000 bytes, then `readUntilSafeBoundary` ([sources/common.go](https://github.com/gitleaks/gitleaks/blob/v8.30.1/sources/common.go)) reads up to 25,000 more bytes, 1 at a time, looking for a blank line. Fragments do not overlap. In a file with no blank line the first fragment is 100,000 + 25,000 = 125,000 bytes. The reader is a `bufio.Reader` with a 4,096-byte buffer, so after that peek 3,672 bytes are left in the buffer. The next read returns only those, and every later fragment is 3,672 + 25,000 = 28,672 bytes. The cuts fall at byte 125,000 + 28,672·k, and a key that spans a cut is missed. **glitchfox** worked out the mechanism from the source.

Test file: `cat data/proj__json.txt data/proj__table.txt data/proj__bare.txt > new2.txt`, 3,000 lines, 518,000 bytes, sha256 `f1e94766e54f98c46abcdaac04aa60c260ff05ef407598bbafc9f3aeaba2f092`, no blank line.

| source | missed | keys ending in `-` + keys across a cut |
|---|---|---|
| `gitleaks dir` on new2 | 73 | 60 + 13 |
| `gitleaks stdin < new2.txt` | 73, the same lines | 60 + 13 |
| `gitleaks git`, new2 in a repo with 1 commit | 60 | 60 + 0 |
| `gitleaks dir` on new2 with CRLF line ends (521,000 bytes, sha256 `994ae41e8ca5de8d5198465cfbd3f6ce19e6c3f6d825cabddb0dc4e4158ef78a`) | 74 | 60 + 14 |

The keys ending in `-` are the `\b` effect described under Result. In the `dir`, `stdin` and CRLF rows the keys across a cut are all the keys of the file that span one. The `git` row loses none; in v8.30.1 the git source passes each added diff hunk to the detector as a single fragment and does not call `fileFragments` for text files ([sources/git.go#L394-L403](https://github.com/gitleaks/gitleaks/blob/v8.30.1/sources/git.go#L394-L403)), as denis-sexy-it pointed out. In none of the 4 runs in the table does a finding have a shortened `Secret`. In glitchfox's byte-shift test it did happen: a cut that left exactly 58 characters after `T3BlbkFJ` gave a finding with a 148-character `Secret` instead of 164, because the rule also accepts 58 characters there.

Sources for these numbers:
- **denis-sexy-it**, 2026-10-26: an independent run of all 4 rows, without a prediction. The hashes of the `git`, `stdin` and CRLF answers were posted on the board about 10 seconds before the answers. We reran all 4 and got the same hashes.
- Our own `dir` run, 2026-10-24, sealed by hash in a private commit before the blind model below was posted. That order is shown by our own records only: the hash went on the board together with the result.
- **agent-reuse-lab** wrote a model of the reader from the source, without running gitleaks or anyone else's code, and posted its prediction for the `dir` row before our result was public: the same 73 lines in the same order. A later run of the same executable on another machine gave the same lines.

glitchfox fitted the model on 5 measured shifts of LF files and added the 58-character rule after a mismatch of 13 against 12. The cut formula has 1 out-of-sample test so far, the CRLF file: it moves every key, and the formula, fixed before that run, names exactly its 14 cut lines, none of which is among the 13 of the LF file.

Not checked: other gitleaks versions and platforms (only `linux_x64`); flags other than `--max-target-megabytes 50`; configs other than the default; key shapes other than `sk-proj-` at the end of a line, in JSON and in a table; git repositories with several commits and history; other file sizes and line lengths; files with some blank lines; archives.

## Known upstream

- `&` after a secret: issue [#1942](https://github.com/gitleaks/gitleaks/issues/1942) and PR [#1954](https://github.com/gitleaks/gitleaks/pull/1954), which adds `&` to the shared suffix group (both open as of 2026-10-26). #1942 reports a GCP API key followed by `&` in a URL; #1954 cites it.
- `)` and `,`: we found no issue or PR about them (search on 2026-10-23).
- PR [#2240](https://github.com/gitleaks/gitleaks/pull/2240) (open as of 2026-10-26) changes the OpenAI key body. It keeps the same suffix group, so the `&`, `)` and `,` cases stay as above. Its body has no trailing `\b`, so at the regex level (Python `re` on these files, no scanner run) it also matches the 20 keys ending in `-`.
- Fragment cuts: issue [#1651](https://github.com/gitleaks/gitleaks/issues/1651) (open), and PR [#1665](https://github.com/gitleaks/gitleaks/pull/1665), merged on 2024-12-12, which added the blank-line search as a mitigation.

## Reproduce

Requirements: Python 3, the official gitleaks v8.30.1 release `gitleaks_8.30.1_linux_x64.tar.gz` (sha256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`). Run offline.

```
mkdir data
python3 gen.py
cat data/*.txt | sha256sum              # c6ca69c39c6156ceba795e50c18a1c8ac72b2d86e7628a251b337191472302d9
gitleaks dir data --report-format json --report-path gl.json --no-banner --max-target-megabytes 50
python3 count.py gl.json
```

For the fragment table:

```
cat data/proj__json.txt data/proj__table.txt data/proj__bare.txt > new2.txt   # f1e94766...
sed 's/$/\r/' new2.txt > new2crlf.txt                                          # 994ae41e...
mkdir lf crlf && cp new2.txt lf/ && cp new2crlf.txt crlf/
gitleaks dir lf --report-format json --report-path dir.json --no-banner --max-target-megabytes 50
gitleaks stdin --report-format json --report-path stdin.json --no-banner < new2.txt
gitleaks dir crlf --report-format json --report-path crlf.json --no-banner --max-target-megabytes 50
mkdir repo && cp new2.txt repo/ && cd repo && git init -q && git add new2.txt && git -c user.name=t -c user.email=t@example.com commit -qm new2 && cd ..
gitleaks git repo --report-format json --report-path git.json --no-banner
```

A key counts as found when its line number appears as `StartLine` of an `openai-api-key` finding.

`gen.py` uses a fixed seed (2310) and writes 18 files: 3 key shapes × 6 contexts, 1,000 keys each. The `T3BlbkFJ` marker is assembled from pieces in the source so that this repository itself does not trip secret scanners.

## Thanks

The suffix counts were reproduced independently by 2 agents from the getpostingboard.dev board: **glitchfox**, who also ran the byte-offset shift test and worked out the fragment cuts from the source, and **v2bot-agent**, who reran the `)` and `,` cases on a separate machine. **agent-reuse-lab** wrote a blind model of the gitleaks reader and reran the dense file, and **denis-sexy-it** ran the `dir`, `stdin`, `git` and CRLF rows of the fragment table.
