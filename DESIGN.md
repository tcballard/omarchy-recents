# Recents v0.1.0 decisions

- ID `io.github.tcballard.recents`; kinds `bar-widget`, `service`. Widget exposes open/close/opened and hosts Panel.qml. Singleton service owns scanning and shared index. No daemon/second shell.
- Verified against omacom/omarchy Quattro `d237995b3be03df3a7bb855e4a23b6fb7204e969` on 15 September 2026: BarWidget/KeyboardPanel, clock, shell injection and capture commands. Screenshots default to Pictures; recordings to Videos, both with environment overrides.
- Bash entry points use Python's standard library for safe XML, SQLite, URI and JSON parsing. Explicit deviation from all-Bash helpers, avoiding fragile parsing without third-party modules or compilation.
- Config/state outside checkout as requested. Private atomic state writes and private browser snapshots. No network or machine privilege. Actions use argv, never shell interpolation.
- Index cap 2,000; cached JSON 16 MB; XBEL 16 MB; browser database 256 MB and 24 profiles. Incremental find parsing, per-root deadlines, aggregate filesystem budget and outer process watchdog. Browser snapshots use SQLite backup for WAL consistency instead of plain cp.
- Bounded intermediate candidate pruning can lose an earlier-source tag if an evicted path is rediscovered later with a newer timestamp. Ranking and canonical-path dedup remain correct; this is a v1 memory tradeoff.
- Service serialises refreshes and rejects post-teardown results. Panel owns focus/selection/confirmation and associates async checks with an open generation. Successful user actions may finish after close, but cannot close a subsequently reopened panel.
- Letter shortcuts apply in list mode. Copy URI/image are separate. Auto-repeat cannot confirm Trash. Fontconfig coverage determines glyph/plain display.
- MIT selected for empty repository. Thumbnails deferred per v1 scope despite milestone 4 mentioning them. Real desktop acceptance precedes formal release/marketplace submission.
