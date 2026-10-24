# Create a course and take it to another Moodle

## Open Moodle

Install and launch MoodlIA. On the first launch, choose your Moodle release and whether to include MoodlIA (enabled by default). Use a version compatible with the Moodle that will receive your course. The selected version and plugin choice remain fixed for that workspace.

The setup screen also offers **Onetopic**, an optional course format with tabs,
on Moodle 4.5, 5.0 and 5.1. It works with or without MoodlIA. Once installed,
choose it under **Course settings > Course format**. It is not offered for Moodle
5.2 or 5.3, and transferring a course using it requires the destination site to
have that format. See [optional plugin details](OPTIONAL-PLUGINS.md).

Open **MoodlIA → Connection files**. `credentials.txt` contains the Moodle URL, username `teacher` and generated password. Log in in the application. `token.txt` contains the API token; it has administrator access to this local site. Keep it private. Do not paste it into a chat.

## Connect an assistant with MoodlIA installed

Install your preferred assistant separately. The examples below are for **Codex CLI**, **Claude Code** and **OpenCode running on this computer**. Hosted chats cannot reach your computer's `127.0.0.1`.

The app binds to IPv4 `127.0.0.1:8787` on every launch. The generated `moodle.json`, environment scripts and MCP configuration files use this same address. Start the app before connecting the assistant. A browser-based assistant running in the cloud or a CLI inside a separate VM/container does not share this loopback address; run the assistant on the host computer for this version. The token authenticates both REST and the optional MoodlIA MCP endpoint.

Open a terminal **in the workspace folder** using the path shown by the application's Workspace folder menu. Load the token into that shell without displaying it:

PowerShell:

```powershell
. ./connection/load-token.ps1
```

Bash / Zsh:

```sh
. ./connection/load-token.sh
```

The variables are available only in this shell and child processes. Keep MoodlIA open while using the assistant.

### Codex

```sh
codex mcp add moodlia --url http://127.0.0.1:8787/local/moodlia/mcp.php --bearer-token-env-var MOODLE_REST_TOKEN
codex
```

Alternatively merge `connection/codex.toml` into your MCP configuration. It stores the variable name, not the token. See [official OpenAI MCP documentation](https://developers.openai.com/codex/mcp/).

### Claude Code

Copy or merge `connection/claude.mcp.json` into `.mcp.json` in your authoring project, then run `claude` from the shell with the token loaded. The configuration uses `${MOODLE_REST_TOKEN}` in an Authorization header. Review and trust the project configuration when prompted. See [official Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

### OpenCode

Copy or merge `connection/opencode.json` into `opencode.json` in your authoring project. Run `opencode` from the shell with the token loaded. Its remote MCP entry disables OAuth and reads `{env:MOODLE_REST_TOKEN}` in the Authorization header. See [official OpenCode MCP documentation](https://opencode.ai/docs/mcp-servers/).

### First requests

```text
Use MoodlIA to check the authenticated user and list the courses. Do not change anything yet.
```

Confirm that the account is `teacher`, then describe the course you want:

```text
Create a hidden course named Introduction to Digital Safety with four sections.
Use standard Moodle activities only. Add a page and a five-question practice quiz
to each section. Do not add students. Show me the result for review.
```

The token belongs to an administrator: review destructive actions and the assistant's proposed changes. Refresh Moodle to inspect the actual saved course.

## If you disabled the plugin

The generated token is for the standard Moodle Core REST service. Load the same environment scripts, then use a Core-compatible client. For the workspace's public Core CLI:

```sh
npm install -g moodle-core-cli
moodle-core --help
moodle-core get-courses
```

Check the CLI's documented configuration and command names before writing. No MoodlIA MCP endpoint or MCP configuration is generated in this mode. Codex, Claude Code and OpenCode can still work through shell commands with a compatible Core client. The assistant must use the Core service rather than assume MoodlIA operations exist.

## Export and restore

1. In Moodle, open the course and choose **More → Course reuse → Backup** (the exact label depends on the version).
2. Back up the course without enrolled users. Include the activities and files you need.
3. Finish the backup and download the `.mbz`. The application offers a normal save dialog, initially in the workspace's `exports` folder.
4. On the destination Moodle, use **Restore** and upload the `.mbz`, with the destination administrator's required permissions.
5. Review the restored activities, question banks, files and completion settings.

Standard activities do not require MoodlIA on the destination. A Moodle backup is not guaranteed to restore into an older release or a site missing required activity plugins. Test a small course before committing a large authoring project.

## Close and keep your work

Close MoodlIA normally; it stops the local server and database. Preserve the entire workspace for a same-platform local backup, after the app has stopped. Use course `.mbz` files to move between operating systems. Reinstalling the application does not intentionally remove your workspace.
