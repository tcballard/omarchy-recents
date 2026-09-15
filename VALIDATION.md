# Validation — 15 September 2026

Target: Omarchy Quattro `d237995b3be03df3a7bb855e4a23b6fb7204e969`.
Candidate: initial Recents commit containing this record; subsequent edits require affected checks again.

## Passed locally

- `./tests/run`: 9 model tests, 25 helper tests and manifest/path validator.
- Synthetic 100,000-file local-filesystem scan: first 0.454s, warm 0.457s, 2,000 retained rows, no partial result. This is a scratch-filesystem measurement, not a cold-disk/laptop benchmark.
- ShellCheck on both Bash entry points and tests/run: no findings.
- `python3 tests/service_qml.py`: 10 assertions against actual Service.qml, simulated process completions. Cache, overlap, success, freshness, failure, skip, removal and late-result rejection.
- Actual Panel.qml/BarWidget.qml loaded with Qt 6.11.2 and explicit host/Process stubs. Dark, light, compact 520×460 and 200% 1600×1300 fixture runs pass. Search/action keys, navigation, type/source filters, confirmation cancellation and dispatch, failed-action preservation, late-open generation protection, Escape, refresh and live popup-colour changes checked.
- Toolkit validator with security: valid, no findings, **review-required** for process execution/collected output. Advisory only; not marketplace approval.

Stub qmllint reports dynamic QObject/Loader property and unqualified-access warnings. Actual fixture loads emit no QML warnings. Full target-import lint has not been run; stub lint is not reported as clean target-platform evidence.

Action executables are mocked: tests check argv/clipboard payloads, not destination paste support. SQLite fixtures and previews are fictional. No real user files are trashed.

## Live acceptance still required

- [ ] Official validator and installed-import qmllint.
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
