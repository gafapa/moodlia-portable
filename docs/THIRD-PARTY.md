# Third-party distribution notes

The source lock records exact download origins and SHA-256 digests. SHA-256 locks detect changes after the initial maintainer fetch; they are not upstream code signatures.

- Moodle: GPL-3.0-or-later, `COPYING.txt` in each bundled version. The pinned source code is included.
- MoodlIA plugin: GPL-3.0-or-later; the pinned source code and its notices are included in `app/plugin`.
- PHP: PHP License; preserve all upstream licenses and notices in `runtime/php`.
- Unix static PHP and compiled extensions/libraries: preserve the upstream archive notices. Maintainers must audit the actual binary's extension/library notices before a public release.
- PostgreSQL and its bundled dependencies: preserve the notices from the Zonky distribution. PostgreSQL uses the PostgreSQL License.
- Microsoft Visual C++ runtime: app-local DLLs are copied from the native Windows build host. The maintainer must have applicable redistribution rights and preserve Microsoft's required terms. Do not claim these binaries are GPL.
- Electron: MIT and Chromium third-party notices, included by electron-builder.
- PyInstaller: GPL with its bootloader exception; frozen application licensing is permitted by that exception.

Public release qualification includes notice review, source availability, platform signing/notarization, and a clean-machine install/uninstall test. Local runtime checks alone do not establish these distribution requirements.
