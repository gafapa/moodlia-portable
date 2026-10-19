# Validation status

This file records observed execution, not platform promises. The packaging definitions cover Windows x64, macOS x64/ARM64 and Linux x64/ARM64. Native runtime checks must execute on each OS/architecture before those outputs are described as qualified.

## Release gates

- Unit checks: archive extraction boundaries, token handling, workspace persistence and version/plugin selection.
- Native startup: first install and repeated startup for every included Moodle version, with and without MoodlIA.
- Integration: teacher administrator identity, REST authentication, MCP catalogue when enabled, course creation and `.mbz` export/restore.
- Desktop: home-page loading, login, safe close, persistent restart, downloads and external links.
- Installer: native system registration, menu shortcut, application update and uninstall with workspace preservation.
- Distribution: dependency review, bundled notices, clean-machine runtime dependencies, Windows signing and macOS signing/notarization.

The native workflow is provided under `.github/workflows/native.yml`; a workflow definition is not evidence of a successful hosted run. See the final execution record below when populated.

## Execution record

2026-10-20, Windows 11 x64, local synthetic fixtures:

- 11 unit/regression checks passed; `npm audit` reported zero known vulnerabilities.
- Bundled PHP 8.3.35 passed extension checks and OpenSSL RSA generation, including a child process using inherited `PHPRC` without an explicit `-c` argument.
- Moodle 4.5.15 with MoodlIA returned the `teacher` administrator through REST, listed MCP tools and executed the MCP identity tool.
- A synthetic hidden course and page retained their IDs, accented content and a changed site setting after a runtime recovery snapshot and a persisted restart. The token remained unchanged.
- Native course backup created a valid `.mbz` including the page activity.
- That backup was restored into a separate Moodle 5.3.0 / PostgreSQL 17.11 instance without MoodlIA. Its shortname and accented page content were verified through Moodle's database API.
- PostgreSQL 16.15 and 17.11 were selected separately; a major-version mismatch fails closed.
- Desktop control input was isolated from child tools after a Windows startup regression. The source backend accepted startup and shutdown commands. Cron runs with `--keep-alive=0` because the app schedules its own recurring invocations.
- The Windows NSIS installer was installed into an isolated directory and registered in Installed Apps. Desktop and Start menu shortcuts pointed to the installed executable.
- The installer refused a running backend without replacing the application. The installed app authenticated `teacher` in its native window, kept renderer sandboxing enabled and shut down gracefully.
- Reinstallation/update and uninstallation passed. Credential/configuration hashes and a marker in the default user-data workspace survived. The course and page were read, exported and checked again after uninstall, with their IDs and content preserved. See `build/installer-evidence.json` and `build/course-evidence.json`.
- Automated login waits for Moodle's asynchronous password-control rendering before entering credentials; an early test filled the element that Moodle then replaced. The corrected test verified the submitted credential match as booleans without recording secrets.
- The installer is unsigned. Local execution does not establish clean-machine compatibility or public distribution qualification.

The integration fixtures are local and fictional. They do not qualify a school's production Moodle or all possible activities/files. Local Windows coverage currently exercises Moodle 4.5.15 with MoodlIA and 5.3.0 without it; the other version/plugin combinations remain unqualified until the native matrix runs.

macOS and Linux packages have build definitions and pinned runtimes, but have not been built or executed in this Windows session. No hosted workflow, public release, Windows signature or macOS notarization has been verified. Third-party notice review and clean-machine qualification remain public-release gates.
