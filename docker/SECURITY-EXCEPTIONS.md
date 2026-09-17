# Tenable findings: what is fixable, and what has to be excepted

Tenable matches an installed package version against an advisory's fixed
version. That produces three different kinds of finding, and only the first is
something a change in this repo can clear:

1. **Fixable** - a newer version exists and we can take it. Fix it.
2. **No fix exists** - Ubuntu has not shipped a patched package, and for several
   of these it never will. No upgrade clears the finding.
3. **Wrong match** - the vulnerable code was added after the version we pin, is
   not compiled into the Ubuntu package, or belongs to a platform or a package
   we do not run.

The scan step in `github/workflows/build-n-scan.yaml` has no flag for excluding
a finding, so everything in categories 2 and 3 has to be entered as an exception
in the Tenable console. The evidence is recorded here so whoever files it does
not have to re-derive it, and so it can be re-checked when the pins move.

Per-release triage below is Canonical's own, from the Ubuntu security tracker
(`https://ubuntu.com/security/cves/<CVE>.json`). It is worth quoting in the
exception: it is the distro maintainer stating whether their build of the
package is affected at all.

---

## 1. Fixable, and currently blocked behind one dependency

Six findings are against Python packages that do have fixed releases:

| CVE | Severity | Package | Fixed in |
| --- | --- | --- | --- |
| CVE-2025-32434 | critical 9.3 | `torch` 2.0.0+cpu | 2.6.0 |
| CVE-2024-31580 | high 8.7 | `torch` 2.0.0+cpu | 2.2.0 |
| CVE-2026-5241 | critical 9.6 | `transformers` 4.48.0 | 5.5.0 |
| CVE-2026-4372 | high 7.8 | `transformers` 4.48.0 | 5.3.0 |
| CVE-2026-1839 | high 7.8 | `transformers` 4.48.0 | 5.0.0rc3 |
| CVE-2025-6638 | high | `transformers` 4.48.0 | 4.53.0 |

They are not independent. The constraint chain is:

    sentence-transformers 2.2.2  imports cached_download  ->  huggingface_hub < 0.26
    huggingface_hub < 0.26                                ->  transformers <= 4.52
    transformers 5.x             requires                 ->  torch >= 2.4
    torch >= 2.6                 flips torch.load's weights_only default to True
    weights_only=True            breaks fairseq checkpoint loading

Each link is checkable:

* `sentence_transformers/util.py` in 2.2.2 does
  `from huggingface_hub import ... cached_download`. 2.3.0 is the first release
  that drops it, so **any** `sentence-transformers >= 2.3.0` lifts the
  `huggingface_hub` ceiling. For `transformers` 5.x specifically the floor is
  `sentence-transformers >= 5.4.0`, which is the first to widen its pin from
  `transformers <5.0.0` to `transformers <6.0.0`.
* `transformers` 5.x declares `torch>=2.4` in its `torch` extra. It cannot be
  combined with the `torch` 2.0.0 this image pins.
* fairseq's `load_checkpoint_to_cpu` calls
  `torch.load(f, map_location=torch.device("cpu"))` with no `weights_only`
  argument (`fairseq/checkpoint_utils.py`, ~line 315). Our checkpoints carry an
  `argparse.Namespace` under `state["args"]` and an omegaconf container under
  `state["cfg"]` - `_upgrade_state_dict` reads both. Under torch >= 2.6 that
  load raises `UnpicklingError` before the model is ever constructed.

So the whole group is gated on the fairseq fork, not on the pins in
`requirements.txt`. Clearing it means passing `weights_only=False` at that call
site - which is the behaviour torch 2.0.0 already has today, and is defensible
because the checkpoint is our own artifact, fetched over TLS from our own Azure
blob container or S3 bucket, not user input. That change belongs either in
`fairseqForkSepFix` or, scoped to the one call, around
`TransformerModel.from_pretrained` in `src/summ_service/summ_model.py`.

Until then these six stay open and need exceptions. `CVE-2026-5241` has an
additional, independent argument - see section 4.

Note that `CVE-2026-1839` is already unreachable for a second reason: it is a
flaw in `transformers.Trainer._load_rng_state`, and this service does no
training. It only ever calls `SentenceTransformer(<local dir>)` for inference.

---

## 2. Findings Canonical has assessed as not affecting Ubuntu 22.04

These are wrong matches against the Ubuntu build of the package. Canonical's
tracker marks them `not-affected` with a reason.

| CVE | Reported against | Canonical's status (jammy) |
| --- | --- | --- |
| CVE-2025-8941 | `libpam-*` | `not-affected` - also `not-affected` on noble |
| CVE-2025-70873 | `libsqlite3-0` | `not-affected` - "code not compiled"; the `zipfile` extension the advisory targets is not built into Ubuntu's sqlite3 |
| CVE-2026-2100 | `libp11-kit0` | `not-affected` - "code not present" |
| CVE-2026-3298 | `python3.10` | `not-affected` - "windows-specific"; matches the advisory's own "Non-Windows platforms are not affected" |

---

## 3. Findings with no fix in any supported Ubuntu release

No `apt-get upgrade` clears these, and neither does moving the base image to
Ubuntu 24.04 - the status is the same on jammy and noble. They have to be
excepted for as long as this image is Ubuntu-based.

| CVE | Reported against | Status on jammy / noble |
| --- | --- | --- |
| CVE-2025-59375 | `libexpat1` | `needed` / `needed` |
| CVE-2026-41080 | `libexpat1` | `needed` / `needed` |
| CVE-2026-66046 | `libexpat1` | `needed` / `needed` |
| CVE-2026-76957 | `libexpat1` | `needed` / `needed` |
| CVE-2026-86145 | `libpcre2-8-0` | `needs-triage` / `needs-triage` |
| CVE-2026-89157 | `libpcre2-8-0` | `needs-triage` / `needs-triage` |
| CVE-2026-76642 | `util-linux` et al | `needs-triage` / `needs-triage` |
| CVE-2026-78409 | `util-linux` et al | `needs-triage` / `needs-triage` |
| CVE-2026-78410 | `util-linux` et al | `needs-triage` / `needs-triage` |
| CVE-2026-54370 | `libacl1` | `ignored` - "backport too intrusive" - same on noble |
| CVE-2016-20013 | `libc-bin`, `libc6` | `ignored` on every release |

Several are also unreachable in this image on their own merits, which is worth
putting in the exception alongside the tracker status:

* **util-linux (all three)** need a local unprivileged user invoking SUID
  `mount(8)` against an `fstab`-authorised `X-mount.*` entry. The image has no
  `fstab` entry, runs a single non-root user, and never calls `mount`.
* **libexpat (all four)** need attacker-controlled XML. Nothing in this service
  parses XML; expat is present only because `python3` links `pyexpat`.
* **pcre2** needs an attacker-controlled regular expression or pattern
  conversion. Patterns in this service are all literals in our own source.
* **CVE-2016-20013** is `sha256crypt`/`sha512crypt` password hashing. The image
  authenticates no one.

---

## 4. Findings against code that is not in the shipped version

### CVE-2026-5241 - critical 9.6 - transformers

Reported because the advisory lists `Resolution: 5.5.0` and our pin is below it.

The advisory describes a flaw in "the LightGlue model loading path of
huggingface/transformers version 5.2.0": `LightGlueConfig` reads
`trust_remote_code` out of an untrusted `config.json` and passes it into a
nested `AutoConfig.from_pretrained()` call.

`LightGlue` did not exist in the 4.x line. The module is absent from both the
version this image used to pin and the one it pins now:

    transformers 4.30.2 - no lightglue module
    transformers 4.48.0 - no lightglue module

Verify against a built image:

    docker run --rm <image> sh -c \
      'ls /home/appuser/.local/lib/python3.10/site-packages/transformers/models/ \
       | grep -i lightglue || echo "not present"'

The vulnerable file is not shipped. This finding stays invalid for as long as
`requirements.txt` pins transformers below 5.x; if it is ever raised to a 5.x
release, re-check it rather than renewing the exception.

Both this and `CVE-2026-4372` additionally require loading a model from an
attacker-controlled repository. This service never does: `SummModel.from_pretrained`
in `src/summ_service/summ_model.py` unpacks a zip from our own Azure blob
container or S3 bucket and hands `SentenceTransformer` a local directory path.
There is no `AutoModel.from_pretrained("<hub repo id>")` call anywhere in `src/`.

### Package mis-attribution

Tenable has attributed these advisories to packages they are not about.

| CVE | Reported against | Why it does not apply |
| --- | --- | --- |
| CVE-2026-85091 | `zlib1g` | Advisory covers zlib 1.3.1.2-1.3.2. Image ships 1.2.11 - below the affected range, not behind a fix. |
| CVE-2026-40224 | `libsystemd0`, `libudev1` | Advisory covers systemd 259 before 260. Image ships 249.11. |
| CVE-2023-47039 | `perl-base` | Path-search flaw in Perl for Windows locating `cmd.exe`. |
| CVE-2026-84366 | `python3.10` | A Scrapy advisory. Scrapy is not installed in this image. |
| CVE-2026-43916 | `libpam-*` | A flaw in `pam_authnft`, a third-party PAM module that is not installed. |

The first two are checkable with `dpkg -l zlib1g libsystemd0` against the ranges
in the advisory text.

---

## 5. What a base image bump to Ubuntu 24.04 would clear

Recorded so the trade-off does not have to be re-derived. Moving
`docker/Dockerfile` from `ubuntu:22.04` to `ubuntu:24.04` clears these, and
nothing in section 3:

| CVE | Package | Noble status |
| --- | --- | --- |
| CVE-2022-4899 | `libzstd1` | `not-affected` from 1.5.4+dfsg2-4 |
| CVE-2026-9538 | `perl-base` | released in 5.38.2-3.2ubuntu0.4 |
| CVE-2026-48959 | `perl-base` | released in 5.38.2-3.2ubuntu0.4 |
| CVE-2026-48961 | `perl-base` | `not-affected` - "code not present" |
| CVE-2020-10735 | `python3.10` | `ignored` on jammy ("change too intrusive"); noble ships python3.12, which the advisory does not list |
| CVE-2018-5709 | `libkrb5-3` et al | `ignored` on jammy; not tracked for noble |
| CVE-2023-31486 | `perl-base` | `ignored` on jammy; not tracked for noble |

The cost is that noble's system Python is 3.12, so the whole stack moves
interpreter versions at the same time. `pydantic` is pinned at 1.10.9 here,
which predates 3.12 support and would have to move to 1.10.13+, and
`fairseqForkSepFix` builds Cython extensions that have not been tried on 3.12.
It is a real reduction in findings but it is not a one-line change, and it does
not touch the expat/pcre2/util-linux group that makes up most of section 3.

---

## 6. Already fixed - do not re-file these

A scan taken before commit `ce465cd` reports five findings against
`python3-pip@22.0.2`: CVE-2023-37920 (critical), CVE-2026-44432, CVE-2026-44431,
CVE-2026-21441 and CVE-2024-39689. Ubuntu 22.04's `python3-pip` is pip 22.0.2,
which vendors `certifi` 2022.x and `urllib3` under `pip/_vendor`, and no fixed
jammy package exists.

`ce465cd` dropped `python3-pip` from the runtime stage - everything the image
needs is installed in the builder stage and arrives through the `.local` copy.
These five are gone from a current build. If they appear in a report, check the
commit the image was built from before filing anything.
