# Nocturne Archive — Python desktop source

This is a GitHub-ready Python/PySide6 desktop project built around the current Nocturne Archive HTML application. It packages into a single Windows `NocturneArchive.exe` with the black-circle **V** icon compiled into the executable.

## Repository contents

- `web/index.html` — complete current HTML/CSS/JavaScript planner source.
- `src/nocturne_archive/` — Python desktop host.
- `assets/reference-pdfs/` — supplied V20 and Pulp Cthulhu PDFs.
- `assets/NocturneArchive-V.ico` — multi-resolution Windows icon used by PyInstaller.
- `NocturneArchive.spec` — repeatable single-file Windows build definition.
- `scripts/` — source-run, clean-data, ordinary build, and compiler-bootstrap build commands.
- `.github/workflows/build-windows.yml` — GitHub Actions Windows build.

## Build without installing Visual Studio

Double-click:

```text
scripts\bootstrap-and-build.cmd
```

The first run downloads the official Python 3.12 compiler/runtime into `.tools`, installs the pinned build dependencies into `.venv`, and runs PyInstaller. Later builds reuse those local tools.

The executable is created at:

```text
dist\NocturneArchive.exe
```

If Python is already installed, use:

```text
scripts\build.cmd
```

## Run from source

Build/install dependencies once, then double-click:

```text
scripts\run-source.cmd
```

## Persistent data

The EXE is immutable. Campaigns, IndexedDB, localStorage, imported PDFs, and browser-profile data are stored beside it in:

```text
NocturneArchive.Data\
```

Keep that directory to retain work, copy it with the EXE to migrate the archive, or run `scripts\clean-data.cmd` for a genuinely clean profile.

## GitHub

Copy the contents of this folder into a repository root, commit, and push. The included Actions workflow can produce the Windows EXE under the run's **Artifacts** section.

## PDF behavior

Qt WebEngine supplies its Chromium PDF viewer when PDFs are opened in the application. The planner's own PDF controls and persistence logic are preserved in `web/index.html`. Exact Acrobat Pro feature parity requires Adobe Acrobat itself or a licensed professional PDF SDK; this source does not redistribute Adobe software.
