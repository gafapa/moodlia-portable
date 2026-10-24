# Changelog

## 0.1.0 — Unreleased

- Update Electron to 44.9.3 and compatible transitive dependencies; the complete
  dependency audit reports zero vulnerabilities.

- Add an English/Spanish setup screen for Moodle version and optional plugins.
  Keep MoodlIA checked by default; offer pinned Onetopic builds on Moodle 4.5,
  5.0 and 5.1, independently of MoodlIA. Reject incompatible selections in both
  the desktop controller and backend, and preserve existing workspace choices.
- Qualify optional plugin database/disk agreement and persisted selection on
  native first installs and restarts. Keep the original course format until
  the teacher explicitly selects Onetopic in a course.

- Replace the removed Windows PHP download with PHP 8.3.36 and verify its
  publisher checksum. Pin the plugin source containing the 0.1.221 MCP fix.
- Key build caches by digest and lock-refresh caches by source URL so an
  updated source cannot accidentally reuse a previous cached runtime.

- Add an installed desktop application that opens the local Moodle home page.
- Bundle native PHP and PostgreSQL; require no Docker or developer runtime on the teacher's machine.
- Select a locked Moodle release starting at 4.5 at first launch.
- Offer the MoodlIA plugin as an optional, default-enabled first-launch choice.
- Create one teacher administrator with a random password and a local token file.
- Generate environment-backed Codex, Claude Code and OpenCode MCP examples when the plugin is installed.
- Support Core REST tokens without the plugin, persistent workspaces, native course backup exports and graceful shutdown.
