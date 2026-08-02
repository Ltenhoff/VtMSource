# Nocturne Archive — New PY Version

This is the clean Python/PySide6 source repository for Nocturne Archive.

It begins with no campaigns or characters. User-created campaigns, characters, portraits,
PDF sheets, maps, clues, touchstones, history entries, and assets are stored locally in:

```text
NocturneArchive.PY.Data
```

## Included application systems

- Gothic Nocturne Archive interface
- Campaign creation, editing, selection, cloning, deletion, import, and export
- Full Campaign Planner with persistent section data
- Chronicle notes
- Character creation, editing, cloning, portraits, conditions, and search
- Embedded persistent character PDF on the Character page
- Exact bundled interactive V20 and Call of Cthulhu master PDFs
- Per-character PDF import, reset, direct export, and Windows-viewer opening
- Private character relationship maps
- Campaign relationship maps with imported private-map groups
- Portrait nodes, drag/drop, directional arrows, labels, and saved positions
- Clue Board
- Touchstones
- Investigator History
- Managed campaign assets
- Full ZIP archive backup and restore
- JSON-only import and export
- Embedded Windows V icon
- Single-file Windows EXE build

## Build locally on Windows

Double-click:

```text
scripts\build.cmd
```

The executable is created at:

```text
dist\NocturneArchive.exe
```

The build script only reports success after confirming that the EXE exists.

## Run from source

Double-click:

```text
scripts\run-source.cmd
```

## Build with GitHub Actions

Push the repository to GitHub. Open **Actions**, select **Build Windows EXE**, and run the workflow.
The completed run provides an artifact named:

```text
NocturneArchive-Windows
```

## Replacing an existing repository checkout

Keep the existing hidden `.git` folder. Delete everything else in the repository directory.
Paste all contents of this package into that directory, then commit and push.
