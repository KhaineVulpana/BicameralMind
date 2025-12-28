# BicameralMind VS Code Extension

## Development
1. Set backend URL in VS Code settings:
   - `bicameralmind.backendUrl` (default: `http://localhost:8000`)
2. If you enabled auth on the backend, set:
   - `bicameralmind.authToken`
3. Build the extension:
   - `npm install`
   - `npm run build`
4. Use **Run Extension** in VS Code to launch a development host.

## Context
The **Context** tab lets you include workspace context automatically and add files/folders manually.
Context is sent with every message to the backend.

Key settings:
- `bicameralmind.contextIncludeWorkspace`
- `bicameralmind.contextIncludeOpenFiles`
- `bicameralmind.contextMaxFiles`
- `bicameralmind.contextMaxOpenFiles`
- `bicameralmind.contextMaxFileBytes`
- `bicameralmind.contextMaxTotalBytes`
- `bicameralmind.contextExcludeGlob`

## TLS Notes (LAN)
For local LAN usage with HTTPS:
- Put a reverse proxy in front of the backend (Caddy recommended).
- Generate a local CA cert and trust it on your workstation.
- Point `bicameralmind.backendUrl` to `https://<host>:<port>`.

## Release Notes
This extension is intended for private/local deployment. Package and distribute as a `.vsix`
if you do not want to publish to the VS Code marketplace.
