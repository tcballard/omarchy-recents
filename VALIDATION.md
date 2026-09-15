# Validation — 15 September 2026

## Plugin Builder review fixes

Source: base `b778b9f765504926fa9fe3ddac1bcaf9e530b22c` plus the review-fix
commit containing this record. Bundle: `26ee1e7fc57e4089daea57ff0c51e6a10659e401`.
Host source: Omarchy `4ee6d4eeea176b0bf4014ce8b82a148a9433efff`, Qt 6.11.2,
Python 3.14. Unrelated local clock/weather/test changes were not used as evidence.

Passed for this patch:

- `./tests/run`: 9 model tests, 41 helper tests, repository manifest validator,
  ShellCheck on `tests/run`, three QtTest cases (plus setup/cleanup), and a real
  Quickshell child-environment probe. The service case includes 11 assertions.
- Regression coverage: total source failure preserves index bytes; successful
  empty scans remain empty; partial sources retain usable results; bounded
  metadata reads reject concurrent growth and FIFOs; WAL downloads remain
  readable and WAL pages count toward size limits; private state rejects unsafe
  permissions/symlinks and retains the validated directory during replacement;
  helper entry points ignore Python/PATH shims; external QML text stays literal.
- Plugin Builder `validate_plugin.py --json --security .`: valid, no findings,
  review-required capabilities only. `omarchy plugin validate "$PWD"`: exit 0.
- `qmllint HelperProcess.qml`: exit 0. Full installed-import lint was also run
  with a temporary `qs` import mapping to the host shell; dynamic QObject/Loader,
  unqualified-access and Quickshell exit-status metadata warnings remain. This
  is not a clean full-plugin lint result.
- `git diff --check`: exit 0.

Filesystem trust tests ran outside the agent sandbox because it remaps root
ownership to UID 65534. Test data stayed in disposable directories. Two existing
SQLite fixture connection ResourceWarnings remain; the production reader now
closes connections explicitly.

The PySide6 download was cancelled because of transfer speed. The existing
PySide6 render/keyboard fixtures were not rerun locally for this patch; CI runs
them. Native QtTest verified the changed rendering sinks and service behavior.
The native process probe is a disposable headless configuration, not plugin
installation or desktop lifecycle evidence. No user files were opened or trashed.

Target of initial evidence: Omarchy Quattro `d237995b3be03df3a7bb855e4a23b6fb7204e969`.
Candidate: initial Recents commit containing this record; subsequent edits require affected checks again.

## Initial candidate evidence (historical)

- `./tests/run`: 9 model tests, 25 helper tests and manifest/path validator.
- Synthetic 100,000-file local-filesystem scan: first 0.454s, warm 0.457s, 2,000 retained rows, no partial result. This is a scratch-filesystem measurement, not a cold-disk/laptop benchmark.
- ShellCheck on both Bash entry points and tests/run: no findings.
- `python3 tests/service_qml.py`: 10 assertions against actual Service.qml, simulated process completions. Cache, overlap, success, freshness, failure, skip, removal and late-result rejection.
- Actual Panel.qml/BarWidget.qml loaded with Qt 6.11.2 and explicit host/Process stubs. Dark, light, compact 520×460 and 200% 1600×1300 fixture runs pass. Search/action keys, navigation, type/source filters, confirmation cancellation and dispatch, failed-action preservation, late-open generation protection, Escape, refresh and live popup-colour changes checked.
- Toolkit validator with security: valid, no findings, **review-required** for process execution/collected output. Advisory only; not marketplace approval.

Stub qmllint reports dynamic QObject/Loader property and unqualified-access warnings. Actual fixture loads emit no QML warnings. Full target-import lint has not been run; stub lint is not reported as clean target-platform evidence.

Action executables are mocked: tests check argv/clipboard payloads, not destination paste support. SQLite fixtures and previews are fictional. No real user files are trashed.

## Live acceptance still required

- [x] Official validator on the review-fix host.
- [ ] Resolve remaining installed-import lint warnings.
- [ ] Enable/disable/re-enable, restart, update, remove.
- [ ] Click, summon/hide/repeated summon, Escape, outside click, panel switching, multi-monitor focus.
- [ ] Horizontal/vertical bar and theme/font changes while open.
- [ ] Touch Documents file and observe edited; GTK dialog open and observe opened; delete visible file and observe disappearance on reopen.
- [ ] Disposable-file Trash confirmation: single/held d, selection change, timeout, Escape, close/reopen, deliberate double d and restore.
- [ ] Open/reveal odd filenames and openWith; clipboard into Files/mail/browser/image editor, recording destination support.
- [ ] Running browser profiles, unsupported schemas, disabled source, empty history and permissions.
- [ ] Low battery, charging, suspend/resume and clock changes.
- [ ] Real laptop ~100k files: warm <2s / cold <8s, unavailable/mounted roots, partial results and depth fallback.

No formal release, tag or marketplace listing is implied by these results.
