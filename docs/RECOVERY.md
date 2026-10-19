# Recovery and updates

Application updates replace the Electron/backend payload only. The workspace is stored in the stable `MoodlIA` user-data directory. Normal uninstall deliberately keeps it. The selected Moodle source and plugin live inside the workspace and are not replaced by application updates.

The Windows installer refuses to install, update or uninstall while `MoodlIA.exe` or `moodlia-backend.exe` is running. It never force-kills the application to replace files. Close MoodlIA normally, wait for shutdown, and run the installer again. Silent installation returns a nonzero result when the app is still active.

Before a changed backend modifies an initialized workspace, it stops PostgreSQL cleanly and makes a snapshot under `data/backups/<timestamp>-<id>/`. A complete snapshot contains `snapshot.json`, `postgres/`, `site/`, `moodledata/`, `connection/` and `config.json`. A directory ending in `.preparing` is incomplete and must not be treated as a recovery point. A failed copy blocks startup and leaves the original data in place.

Snapshots are local and unencrypted, under the private workspace data directory. Copy independent backups to protected storage. Check available disk space before updating. Restoring a snapshot is an explicit administrative operation; the application never overwrites the live database automatically.

For recovery, first stop MoodlIA and preserve the complete current workspace. Work in a **separate empty recovery workspace** on the same OS and architecture. Copy `site/` and `connection/` to its root; copy `postgres/`, `moodledata/` and `config.json` into its `data/` directory. Use the matching application/runtime and set `MOODLIA_WORKSPACE` to this new path before starting. The launcher detects the existing Moodle schema and recreates the readiness marker without reinstalling. Verify the teacher identity, courses and file access before using it. Do not merge raw PostgreSQL directories across OSes or major versions.

The bundled database major is 16 for Moodle 4.5–5.2 and 17 for Moodle 5.3. The workspace configuration and snapshot manifest record the selected engine. Application updates retain this choice.

Moodle core upgrades/downgrades are not performed by this application version. New workspaces may select a different bundled release; existing databases retain their original release. Export courses to `.mbz` for migration between Moodle versions and operating systems, then verify a test restore. Keep the old workspace until the destination is confirmed.

This design reduces update-related data loss; it cannot guarantee against disk failure, forced shutdown during writes, external deletion, unsupported manual modifications or a restore procedure that has not been tested.
