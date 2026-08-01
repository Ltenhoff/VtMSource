# PDF handling

The application bundles the exact source PDFs. It never reconstructs or redraws them.

* Vampire master: `assets/reference-pdfs/V20_Vampire35thAnniversary_4-Page_Interactive.pdf`
* Each new Vampire character receives a byte-for-byte copy in `NocturneArchive.Data/CharacterSheets/<id>/sheet.pdf`.
* The character page loads that stored file directly in Chromium's native PDF viewer.
* Imported PDFs replace only the active character copy.
* Save/download operations use the native PDF viewer and preserve the actual PDF bytes.
* Reset copies the untouched bundled master again.
