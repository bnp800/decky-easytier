# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Decky plugin template repository for creating Steam Deck plugins using TypeScript and React for the frontend, with optional Python or native backend support. Decky plugins extend the Steam Deck's gaming mode interface.

## Development Commands

### Core Development
- `pnpm install` - Install dependencies (requires Node.js v16.14+ and pnpm v9)
- `pnpm run build` - Build the plugin frontend
- `pnpm run watch` - Build and watch for changes during development

### VSCode Tasks
The repository includes comprehensive VSCode tasks for streamlined development:

- `setup` - Complete setup (dependencies, pnpm install, update frontend library)
- `build` - Full build pipeline (setup → settings check → CLI build)
- `deploy` - Deploy plugin to Steam Deck via SSH
- `builddeploy` - Build and deploy in one command
- `restartdecky` - Restart Decky loader on Steam Deck

### Updating Dependencies
- `pnpm update @decky/ui --latest` - Update Decky Frontend Library to latest version

## Architecture

### Frontend (TypeScript/React)
- **Entry Point**: `src/index.tsx` - Defines the plugin structure and UI
- **Build Tool**: Rollup with `@decky/rollup` plugin
- **UI Library**: `@decky/ui` (React components for Steam Deck interface)
- **API**: `@decky/api` (communication with backend and Steam Deck)

The frontend uses a plugin definition pattern:
```typescript
export default definePlugin(() => {
  // Initialization logic
  return {
    name: "Plugin Name",
    titleView: <div>Title element</div>,
    content: <Component />,  // Main UI
    icon: <IconComponent />,
    onDismount() { /* cleanup */ }
  };
});
```

### Backend Options

1. **Python Backend** (`main.py`):
   - Decky loader's built-in Python server
   - Accessible via `callable()` from frontend
   - Event system via `decky.emit()` and `addEventListener()`
   - Plugin lifecycle: `_migration()` → `_main()` → `_unload()` → `_uninstall()`

2. **Native Backend** (`backend/`):
   - Place source in `backend/src/`
   - Build outputs must go to `backend/out/` for CI
   - Example Makefile shows proper output directory structure
   - Docker support via `backend/Dockerfile` for cross-compilation

### Plugin Configuration
- `plugin.json` - Plugin metadata (name, author, flags, publish info)
- `package.json` - Node.js dependencies and scripts
- Frontend build output goes to `dist/` directory

### Steam Deck Deployment
The VSCode tasks support direct deployment to Steam Deck:
- Configure connection in `.vscode/settings.json` (created from `defsettings.json`)
- Uses SSH with configurable IP, port, user, and password/key
- Default settings configured for typical Steam Deck setup

## Key Development Patterns

### Frontend-Backend Communication
- **Frontend calls backend**: Use `callable<Args, Return>("function_name")`
- **Backend events**: Emit with `decky.emit("event_name", ...data)`
- **Frontend listens**: Use `addEventListener<Args>("event_name", callback)`

### Plugin Lifecycle
1. `_migration()` - Data migration when plugin version changes
2. `_main()` - Plugin initialization (async tasks recommended)
3. `_unload()` - Plugin disabled but files remain
4. `_uninstall()` - Complete removal, cleanup files

### UI Components
Use `@decky/ui` components for consistent Steam Deck interface:
- `PanelSection`, `PanelSectionRow` - Layout containers
- `ButtonItem`, `ToggleField`, `SliderField` - Interactive elements
- `staticClasses` - Steam Deck styling classes
- `toaster` - Toast notifications

## Testing and Distribution

### Local Testing
- Build with `pnpm run build`
- If using VSCode: Use `build` and `deploy` tasks
- Manual installation requires copying files to Steam Deck

### Plugin Structure for Distribution
```
pluginname.zip
└── pluginname/
    ├── dist/
    │   └── index.js         # Frontend bundle (required)
    ├── bin/                 # Native binaries (optional)
    │   └── binary
    ├── package.json         # Required
    ├── plugin.json          # Required
    ├── main.py              # Python backend (optional)
    ├── README.md            # Recommended
    └── LICENSE              # Required for plugin store
```

### Plugin Store Submission
- Submit to [decky-plugin-database](https://github.com/SteamDeckHomebrew/decky-plugin-database)
- Must include appropriate LICENSE file
- Follow naming conventions: `decky-` prefix usually required
- Documentation should be in README.md and/or wiki

## Important Constraints

### Frontend Constraints
- Builds for Steam Deck hardware limitations
- React 19+ with specific JSX settings
- No direct DOM access - use Decky components
- Limited npm packages (peer dependencies on React handled by Decky)

### Backend Constraints
- Python 3.x with asyncio
- Limited system access based on Decky permissions
- Sandboxed execution environment
- Binary backends must be compiled for Steam Deck architecture (x86_64 Linux)

### Build Constraints
- Rollup bundler with specific Decky configuration
- TypeScript with strict mode enabled
- ES2020 target for frontend code
- Frontend bundle must remain compact for Steam Deck
