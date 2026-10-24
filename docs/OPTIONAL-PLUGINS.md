# Optional first-launch plugins

The setup screen selects a Moodle version, MoodlIA (enabled by default), and
optional plugins. Onetopic is unchecked by default and does not require MoodlIA.
Moodle can also be installed without either plugin.

| Component | Purpose | Bundled Moodle branches |
| --- | --- | --- |
| `local_moodlia` | REST/MCP tools and optional WebMCP | 4.5, 5.0, 5.1, 5.2, 5.3 |
| `format_onetopic` | Course topics displayed in tabs | 4.5, 5.0, 5.1 |

Onetopic is developed by David Herney and contributors and distributed under
GPL v3 or later. Its source and license remain in each bundled plugin copy.
See the [upstream repository](https://github.com/davidherney/moodle-format_onetopic)
and [Marketplace versions](https://marketplace.moodle.com/plugins/172/versions?show=all).
Moodle 5.2 and 5.3 are not offered an unqualified Onetopic release.

`plugins.json` declares names, components, installation paths and compatible
branches. `sources.lock.json` records exact upstream commits, archive URLs and
SHA-256 values. `scripts/lock_sources.py` owns lock refreshes. Packaging extracts
the matching code into `app/plugins/<component>/<branch>`; first launch copies
only selected plugins into the staged Moodle tree before database installation.
No runtime download or arbitrary plugin URL is accepted by the setup UI.

The desktop IPC controller validates input against bundled versions and plugin
compatibility. Only the local setup document in the main frame can call it;
Moodle pages receive no setup API and handlers are removed before Moodle opens.
The backend validates compatibility again, checks destination containment and
rejects changes to an existing workspace's selection. Old configurations without
`optional_plugins` mean an empty selection.

CLI example:

```sh
moodlia-backend --moodle-version 4.5.15 --plugin format_onetopic
```

Add `--without-plugin` to omit MoodlIA while retaining Onetopic. The term
`--without-plugin` retains its historical meaning: it disables `local_moodlia`.

Installation makes the format available; it does not convert existing courses.
In Moodle, choose **Course settings > Course format > Onetopic** for each course
that should use tabs. A destination Moodle needs the same course-format plugin
before restoring a course using it.

Native qualification selects Onetopic for compatible plugin-enabled test
workspaces, checks installed component versions on disk and in the Moodle
database, and verifies that the saved selection, password and token survive a
restart. Core-only workspaces continue to exercise an empty optional selection.
