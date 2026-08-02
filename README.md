# Nocturne Archive — Full Python Application

Blank first launch. No sample campaigns, characters, portraits, maps, notes, or user data are bundled.

## Windows build

Run:

    scripts\build.cmd

Output:

    dist\NocturneArchive.exe

## Implemented systems

- Campaign create, edit, delete, select, clone, JSON import/export
- Full ZIP backup and restore including PDFs, portraits, maps, and assets
- Full sectioned campaign planner with autosave and manual save
- Chronicle notes: campaign notes, game plot, session journal, storyteller scratchpad
- Character create, edit, clone, delete, search, portraits, conditions, rulesets
- Exact bundled four-page V20 interactive PDF and bundled CoC PDF
- Per-character PDF copies created when the character is created
- PDF window, import any PDF, reset, byte-for-byte export, default-viewer opening
- Private character maps, campaign map groups, portrait nodes, drag/drop, arrows, labels, propagation
- Clue board with add/edit/delete
- Touchstone manager with add/edit/delete
- Investigator history with add/edit/delete
- Assets copied into managed storage, opened, and deleted
- Persistent user-owned storage in NocturneArchive.PY.Data


## Character-page and relationship UX corrections

- Single-clicking a character in the left pane selects it and opens the Character tab
- Double-clicking a character also opens the Character tab, never the PDF window
- The character's actual persistent PDF is embedded directly below the identity card
- Imported and reset PDFs immediately reload in the embedded viewer
- Removed redundant separate Open PDF Window control
- Default-viewer opening remains available
- Relationship edits redraw lines without resetting user-dragged node positions
- New nodes avoid overlap on spawn
- Dragging another character into a private map requires confirmation
- Relationship-map interactions never change the selected character in the left pane
