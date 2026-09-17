# Scanner findings that do not apply to this image

Tenable matches a package version against an advisory's fixed version. When the
vulnerable code was *added* after the version we pin, or the flaw is confined to
a platform we do not run, the match is wrong and no upgrade can clear it.

The scan step in `github/workflows/build-n-scan.yaml` has no flag for excluding a
finding, so each entry below has to be entered as an exception in the Tenable
console. The evidence is recorded here so whoever files it does not have to
re-derive it, and so it can be re-checked when the pins move.

## CVE-2026-5241 - critical 9.6 - transformers

Reported against `transformers` because the advisory lists `Resolution: 5.5.0`
and our pin is below it.

The advisory describes a flaw in "the LightGlue model loading path of
huggingface/transformers version 5.2.0": `LightGlueConfig` reads
`trust_remote_code` out of an untrusted `config.json` and passes it into a nested
`AutoConfig.from_pretrained()` call.

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

## High-severity findings in the same category

Listed for the same reason. These do not gate the build today, but they are the
same class of mismatch.

| CVE | Reported against | Why it does not apply |
| --- | --- | --- |
| CVE-2026-85091 | `zlib1g` | Advisory covers zlib 1.3.1.2-1.3.2. Image ships 1.2.11 - below the affected range, not behind a fix. |
| CVE-2026-40224 | `libsystemd0`, `libudev1` | Advisory covers systemd 259 before 260. Image ships 249.11. |
| CVE-2026-3298 | `python3.10` | `asyncio.ProactorEventLoop` is Windows-only; the advisory states "Non-Windows platforms are not affected". |
| CVE-2023-47039 | `perl-base` | Path-search flaw in Perl for Windows locating `cmd.exe`. |
| CVE-2026-84366 | `python3.10` | A Scrapy advisory. Scrapy is not installed in this image. |
| CVE-2026-43916 | `libpam-*` | A flaw in `pam_authnft`, a third-party PAM module that is not installed. |

The first two are checkable with `dpkg -l zlib1g libsystemd0` against the ranges
in the advisory text.

# Findings that are real but blocked behind the torch upgrade

These are not exceptions. They are genuine, they are marked `Resolvable: Yes`,
and they cannot be fixed while `requirements.txt` pins `torch==2.0.0`. Recorded
here so the next person does not spend the afternoon rediscovering the ceiling.

## The measurement

`torch.compiler` was introduced in torch 2.1. transformers began using it in
4.50.0. Behaviour against torch 2.0.0, measured by building a small BERT,
saving it, reloading it through `SentenceTransformer` and calling `encode()`:

| transformers | result on torch 2.0.0 |
| --- | --- |
| 4.48.0 (current pin) | works - encode returns embeddings |
| 4.49.0 | works |
| 4.50.0 - 4.51.3 | `import transformers` succeeds, but importing `transformers.models.bert.modeling_bert` raises `AttributeError: module 'torch' has no attribute 'compiler'` |
| 4.52.4 and later | as above, and additionally logs `Disabling PyTorch because PyTorch >= 2.1 is required but found 2.0.0`; `is_torch_available()` returns False, so the breakage is silent rather than loud |
| 5.x | `import transformers` itself fails: `NameError: name 'nn' is not defined` |

4.49.0 is therefore the highest usable version, and every outstanding
transformers CVE needs 4.50.0 or later:

| CVE | Severity | Needs |
| --- | --- | --- |
| CVE-2025-2099 | High | 4.50.0 |
| CVE-2025-6638 | High | 4.53.0 |
| CVE-2025-6921 | High | 4.53.0 |
| CVE-2026-1839 | High | 5.0.0rc3 |
| CVE-2026-4372 | High | 5.3.0 |
| CVE-2026-5241 | Critical | 5.5.0 (invalid anyway - see above) |

An earlier revision of the comment in `requirements.txt` blamed the
`sentence-transformers==2.2.2` pin for this ceiling. That was wrong.
`sentence-transformers` 2.3.1 and later dropped the `cached_download` import
that tied us to `huggingface_hub` 0.25.2, so the hub constraint is gone - but
lifting it only exposes torch as the binding constraint underneath. Note that
`sentence-transformers` 3.0 and later import `transformers.trainer`, which also
needs torch 2.1+, so 2.7.0 is the ceiling on that package for the same reason.

## What the torch upgrade would clear

`torch==2.0.0` -> `2.6.0` resolves CVE-2025-32434 (critical, 9.3),
CVE-2024-31580 (high) and CVE-2024-31583 (high) directly, and unblocks all six
transformers findings above. It is the single highest-value change left, and it
belongs in its own pull request with its own inference-output comparison.

# Separately: torchvision is installed broken

Not a scanner finding, but it falls out of the same investigation and affects
any attempt to move transformers.

`sentence-transformers==2.2.2` depends on a bare `torchvision`, so
`pip install -r requirements.txt` resolves the newest one, and the later
`pip install torch==2.0.0+cpu` step does not correct it. The result:

    $ pip check
    torchvision 0.29.0 has requirement torch==2.14.0, but you have torch 2.0.0.

Because transformers imports torchvision for its image utilities, loading any
model through it fails with `ModuleNotFoundError: No module named
'torch._custom_ops'`. This is present on `main` today - it reproduces with an
unmodified `requirements.txt` in the same install order the Dockerfile uses - so
the `GENERAL_SUMMARY` code path cannot currently construct a
`SentenceTransformer`. The default `GENERAL_SUMMARY=0` leaves
`sentence_understanding` set to `None`, which is why the fairseq summarisation
path is unaffected and the failure has gone unnoticed.

It also explains the image size: the unpinned resolution pulls the CUDA build of
torch plus its `nvidia-*` wheels, roughly 3 GB, which the CPU pin then orphans.

Fix, when someone takes it: install the pinned trio before `requirements.txt`,
so the resolver never sees an unconstrained `torchvision`.

    pip install torch==2.0.0+cpu torchvision==0.15.1+cpu torchaudio==2.0.1 \
        --extra-index-url https://download.pytorch.org/whl/cpu

`torchvision 0.15.1` is the release that requires exactly `torch==2.0.0`.
