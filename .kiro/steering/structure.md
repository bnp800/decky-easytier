# Project Structure

## Root Files
- `plugin.json` - Plugin metadata (name, author, flags, publish info)
- `package.json` - NPM package configuration
- `main.py` - Python backend entry point (Plugin class)
- `rollup.config.js` - Rollup bundler configuration
- `tsconfig.json` - TypeScript compiler configuration
- `decky.pyi` - Python type stubs for Decky API

## Source Directories

### `src/` - Frontend Source
- `index.tsx` - Main plugin entry point, defines UI and lifecycle
- `components/` - React components
- `hooks/` - Custom React hooks
- `types.d.ts` - TypeScript type definitions

### `backend/` - Backend Source
- `src/main.c` - C/C++ source code (optional)
- `Makefile` - Build configuration for C/C++ backend
- `Dockerfile` - Docker configuration for backend builds
- `entrypoint.sh` - Docker entrypoint script
- `out/` - Compiled binaries (created during build)

### `assets/` - Static Assets
- Images, logos, and other static resources
- Can be imported in TypeScript code

### `defaults/` - Default Configuration
- Default settings and configuration files

### `py_modules/` - Python Dependencies
- Additional Python modules for the backend

## Build Artifacts
- `dist/` - Compiled frontend code (index.js)
- `backend/out/` - Compiled backend binaries
- `out/` - Complete plugin package for distribution
- `node_modules/` - NPM dependencies

## Distribution Structure
When packaged, plugins follow this structure:
```
pluginname/
├── dist/
│   └── index.js (required)
├── bin/ (optional)
│   └── binary
├── package.json (required)
├── plugin.json (required)
├── main.py (required if using Python backend)
├── LICENSE (required)
└── README.md (optional)
```

## Key Conventions
- Frontend code must be rebuilt after any changes to `src/`
- Backend binaries must output to `backend/out/` for CI compatibility
- Python backend uses async/await patterns
- Frontend communicates with Python via callable functions from @decky/api
- Event-driven communication between frontend and backend using addEventListener/emit
