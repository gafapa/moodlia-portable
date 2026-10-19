# MoodlIA Portable

[![Native packages](https://github.com/gafapa/moodlia-portable/actions/workflows/native.yml/badge.svg)](https://github.com/gafapa/moodlia-portable/actions/workflows/native.yml)

A native desktop application for authoring Moodle courses without access to a school server. Install the app, choose a Moodle version starting at 4.5, and work in Moodle's home page inside the app window. PHP, PostgreSQL and the launcher are bundled. Teachers do not install Docker, PHP, a database, Python or Node.js.

The only human account is **teacher**, a Moodle site administrator. Its unique password and API token are generated on the first launch. Moodle's built-in guest record also exists; guest login and self-registration are disabled.

The **Install MoodlIA plugin** option is checked by default. With the plugin, connect Codex, Claude Code or OpenCode through Moodle's local MCP endpoint. Without it, use the generated Core REST token and a Core-compatible CLI. The application does not include or pay for an AI assistant or model.

## Application packages

- Windows x64: a per-user NSIS setup `.exe`, registered in Installed Apps, with Start menu and desktop shortcuts. The installer starts MoodlIA after installation. An optional ZIP can be built with `npm run package -- --win zip`.
- macOS Intel / Apple Silicon: `.dmg` with the `.app` to copy to Applications, and ZIP.
- Linux x64 / ARM64: `.deb` and `.rpm` with desktop-menu registration; AppImage and tarball alternatives.

This repository contains the implementation and native packaging workflow. Read [validation status](docs/VALIDATION.md) before treating a target as qualified. Unsigned local builds are not signed/notarized public releases.

## First launch

1. Install and open **MoodlIA**.
2. Select a bundled stable Moodle release. Keep **Install MoodlIA plugin** checked for MCP authoring.
3. Wait for Moodle's home page. Open **MoodlIA → Connection files** and read `credentials.txt` to log in as `teacher`.
4. Follow [the quick start](docs/QUICKSTART.md) to connect an assistant, create a course and export `.mbz`.

Installed app files and the writable workspace are separate. The workspace lives in Electron's per-user `userData/workspace` directory (typically `%APPDATA%/MoodlIA/workspace`, `~/Library/Application Support/MoodlIA/workspace`, or `~/.config/MoodlIA/workspace`). Use **Workspace folder** to locate the actual path. `MOODLIA_WORKSPACE` overrides it, including for a writable portable folder.

Close the app normally and wait for the backend to stop before copying the entire workspace or shutting down the computer. Do not copy a running PostgreSQL database. App updates and normal uninstall preserve the workspace. Back it up independently.

Before a changed runtime can bootstrap an existing site, the launcher stops PostgreSQL cleanly and creates a recovery snapshot under `data/backups/`: the stopped database cluster, site source, Moodle files, connection files and private configuration. A failed snapshot blocks startup rather than proceeding with changes. A successful REST/MCP verification commits the new runtime fingerprint. Existing credentials are retained. Database major-version and workspace-schema mismatches stop startup without attempting migration. Snapshots do not replace an independent backup and are not automatically pruned.

Each workspace has one fixed Moodle version and plugin choice. To choose again, use a **new empty workspace**; never downgrade an existing Moodle database. Automatic in-place Moodle upgrades are outside this first version.

## Build from source

Maintainers need Python 3.12+, Node.js 22+ and the native packaging tools for their OS. These are build requirements, not teacher requirements.

```sh
python -m pip install -r requirements-build.txt
npm ci
python scripts/build.py
npm run package
```

The default backend includes all locked stable releases: 4.5.15, 5.0.8, 5.1.8, 5.2.4 and 5.3.0. To build a smaller package, repeat `--moodle-version`, for example `python scripts/build.py --moodle-version 4.5.15 --moodle-version 5.3.0`.

Builds verify every downloaded archive against `sources.lock.json`. Source commits and download hashes are pinned. `scripts/lock_sources.py` is a maintainer-only refresh that establishes a new lock from the named upstreams; review the resulting changes before distributing. It is never run by the teacher's installer. Bundled Moodle and plugin code comes from committed upstream versions, not neighboring uncommitted files.

```sh
python -m unittest discover -s tests -v
build/portable/moodlia-backend --moodle-version 4.5.15 --workspace /absolute/test-workspace --check
```

On Windows use `build\portable\moodlia-backend.exe`. `--check` initializes a real isolated site, verifies the teacher identity through REST, checks the MCP tool catalogue when enabled, then stops. Repeat it to check restart persistence. `--without-plugin` tests Core mode. `--export-course ID` starts the existing workspace, exports that course to `exports/`, then stops. Desktop mode uses stdin `stop` to shut down gracefully on all platforms.

Do not overwrite a running app's runtime or delete `build/portable` without preserving any development workspace inside it. Builds refuse to overwrite an existing backend directory.

## Boundaries

The HTTP server binds only to `127.0.0.1:8787`; PostgreSQL uses a password and a separate loopback port. HTTP is intentional for this local-only desktop server. Do not expose it to the LAN or internet. Any local process with the token has administrator access. The app uses Electron renderer sandboxing, disables Node integration, denies permission requests and opens external web links in the system browser.

A loopback proxy routes MCP to a dedicated PHP worker and other Moodle requests to two additional workers. This allows the plugin's nested REST calls on Windows, where PHP's built-in server cannot handle them in a single process. PHP worker ports are selected locally at each launch and are not exposed outside loopback.

Only the MCP worker request receives a restricted HTTP policy allowing the app's own `127.0.0.1` proxy port; all other IP addresses and ports are blocked in that request. REST tool execution runs in separate requests with Moodle's ordinary HTTP security settings. The upstream MoodlIA plugin is not patched and global SSRF protections are not disabled.

Tokens are stored in `connection/token.txt` as requested, with owner-only permissions on Unix and an explicit current-user ACL on Windows. They are not embedded in agent configuration examples, sent in URLs or printed by the launcher. Keep the workspace private and out of shared Git repositories. Moodle itself does not call an AI service; the chosen assistant may transmit course content according to its provider and settings.

Native database directories are not a cross-OS exchange format. Move courses between computers and servers using `.mbz` backups. Restore compatibility depends on Moodle versions, destination permissions and installed activity plugins; use the same or a newer supported destination and standard activities. The destination does **not** need MoodlIA for native Moodle activities.

## Third-party components

Copyright (C) 2026 Pablo Gallego. MoodlIA Portable is licensed under GPL-3.0-or-later; see [LICENSE](LICENSE) for the full license text.

Moodle and the MoodlIA plugin are GPL software; their source archives and notices ship in the application payload. PHP is distributed under its included PHP license. PostgreSQL binaries are redistributed by [Zonky](https://github.com/zonkyio/embedded-postgres-binaries); PHP Unix binaries by [static-php-cli](https://github.com/crazywhalecc/static-php-cli), and Windows PHP by [PHP](https://windows.php.net/). Windows packages include Microsoft Visual C++ runtime DLLs copied app-locally by the maintainer; distribute them only under Microsoft's applicable redistribution terms. See [third-party notices](docs/THIRD-PARTY.md).
