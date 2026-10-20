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

The integration fixtures are local and fictional. They do not qualify a school's production Moodle or all possible activities/files. Local Windows coverage exercises Moodle 4.5.15 with MoodlIA and 5.3.0 without it. Hosted checks expand that version coverage as recorded below.

## Hosted GitHub Actions

The source repository is public at [gafapa/moodlia-portable](https://github.com/gafapa/moodlia-portable). Native qualification installs a real Moodle, authenticates the `teacher` administrator through REST, executes the MCP identity tool when enabled, and restarts the same workspace while comparing token and password. The complete version set is 4.5.15, 5.0.8, 5.1.8, 5.2.4 and 5.3.0, each with and without MoodlIA.

Observed on 2026-10-20:

| Target | Native version/plugin combinations | Packaging | Evidence |
| --- | --- | --- | --- |
| Linux x64 | All 10 passed | deb, rpm, AppImage and tarball passed | [Native job](https://github.com/gafapa/moodlia-portable/actions/runs/39342630985/job/118367591662) |
| Linux ARM64 | All 10 passed | deb, rpm, AppImage and tarball passed | [Native job](https://github.com/gafapa/moodlia-portable/actions/runs/39342630985/job/118367591792) |
| macOS ARM64 | All 10 passed | dmg and ZIP passed | [Native job](https://github.com/gafapa/moodlia-portable/actions/runs/39342630985/job/118367591971) |
| Windows x64 | All 10 passed | NSIS executable and installer lifecycle passed | [All versions](https://github.com/gafapa/moodlia-portable/actions/runs/39343387793/job/118370088018), [Installer lifecycle](https://github.com/gafapa/moodlia-portable/actions/runs/39346307504/job/118379633146) |
| macOS Intel | All 10 passed | dmg and ZIP passed | [Native job](https://github.com/gafapa/moodlia-portable/actions/runs/39342630985/job/118367591709) |

All 50 native version/plugin/target combinations passed. The Windows all-version job subsequently failed in the test harness because an empty Windows user profile has no per-user Uninstall registry key. The corrected harness treats that state as an empty list. The separate installer lifecycle run passed using Moodle 4.5.15, with all five versions still bundled in its package.

The hosted Windows lifecycle test creates a course and page before installation, records their identities, and compares them after installation, reinstallation/update and uninstall. It also verifies an active-backend update refusal, Installed Apps registration, login inside the installed Electron application, renderer sandboxing, graceful database shutdown, unchanged configuration/credential hashes, a marker in the default user-data workspace and another native course export after uninstall. The course/page identity and accented content survived. These are synthetic fixtures, not production teacher data.

The native workflow defaults to all targets and bundled versions. Maintainers can use `workflow_dispatch` inputs `matrix` (an include-array JSON value) and `versions` (comma-separated versions) for targeted reruns. Targeted qualification summaries list only the versions actually executed; they do not replace the all-version evidence above.

Native restart checks caught and corrected Unix port reuse after connections enter TIME_WAIT. Windows CI also caught protected child ACLs created by Python in elevated sessions: the launcher now grants the current user access explicitly on each managed private directory, allowing PostgreSQL's restricted process to create its log. A separate [Windows Server 2022 runtime run](https://github.com/gafapa/moodlia-portable/actions/runs/39343388433) passed first launch and restart of Moodle 4.5.15 in both plugin modes.

Package artifacts contain application payloads and sanitized qualification summaries. Workspaces, database clusters, credentials and tokens are excluded. macOS/Linux native backend checks and package builds do not establish interactive desktop qualification or clean-machine compatibility. Windows signatures, macOS notarization, third-party notice review and clean-machine qualification remain public-release gates. No GitHub Release has been published.
