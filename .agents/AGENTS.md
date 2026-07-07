# General Guidance for AI Agents

## Chat Communication Updates
- **Mandatory**: All agents MUST post periodic progress updates to the `pfo-gemcli` Google Chat space.
- **Frequency**: Updates must be posted **at least every 30 minutes**, or immediately upon making significant progress on tasks (e.g. designing plans, passing tests, opening PRs, or completing workflows).
- **Execution Mechanism**: The primary agent has permission to post updates using the Google Workspace CLI tool `gws`. Note that sub-agents will fail to execute `gws` commands due to restricted sandbox permissions. Therefore, the primary agent must act as the router/publisher for all chat notifications.
- **Example Usage**:
  Run this command inside a Python execution context (or script) to bypass the multicall shell wrapper interceptor:
  ```python
  import subprocess, json
  msg = "Progress Update: ..."
  subprocess.run([
      '/opt/homebrew/bin/gws', 'chat', 'spaces', 'messages', 'create',
      '--params', '{"parent": "spaces/AAQApbbumHU"}',
      '--json', json.dumps({'text': msg})
  ])
  ```
