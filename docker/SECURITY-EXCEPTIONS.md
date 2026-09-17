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
