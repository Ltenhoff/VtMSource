# Nocturne Archive — New PY Version

This is a clean Python/PySide6 desktop build. It uses a new data directory,
`NocturneArchive.PY.Data`, so broken data from earlier prototypes is never loaded.

## Build on Windows

Extract the project, then run:

    scripts\build.cmd

The build succeeds only when this file exists:

    dist\NocturneArchive.exe

## Working systems

- Campaign creation from the sidebar text box or full Chronicle dialog
- Campaign selection, editing, deletion, cloning, import, and export
- Planner fields stored per campaign and per section
- Chronicle notes stored per campaign
- Character creation, editing, deletion, portraits, conditions, and selection
- Relationship map loading, node movement, linking, and persistence
- Asset addition and deletion
- Archive tools
- Exact bundled V20 and CoC PDF files
- Per-character PDF copies, native PDF window, import, reset, and byte-copy export
