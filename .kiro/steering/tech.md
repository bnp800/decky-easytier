# Technology Stack

## Frontend
- TypeScript with React (JSX)
- Rollup for bundling (via @decky/rollup)
- @decky/ui - Decky's UI component library
- @decky/api - API for plugin lifecycle and backend communication
- react-icons for icons

## Backend
- Python 3 (main backend)
- C/C++ (optional, for compiled binaries)
- Docker (required for building C/C++ backends)

## Build System
- pnpm v9 (package manager)
- Rollup (bundler)
- TypeScript compiler
- Make (for C/C++ backend)
- Decky CLI (for Docker-based backend builds)

## Common Commands

### Setup
```bash
pnpm i
```

### Build
```bash
pnpm run build
```

### Watch Mode (auto-rebuild on changes)
```bash
pnpm run watch
```

### Backend Build (C/C++)
```bash
cd backend
make
```

### Update Decky UI Library
```bash
pnpm update @decky/ui --latest
```

## Build Output
- Frontend: `dist/index.js` (bundled JavaScript)
- Backend binaries: `backend/out/` (compiled C/C++ code)
- Distribution: `out/` folder (complete plugin package)

## TypeScript Configuration
- Target: ES2020
- Module: ESNext
- JSX: react-jsx
- Strict mode enabled
- No unused locals/parameters allowed
