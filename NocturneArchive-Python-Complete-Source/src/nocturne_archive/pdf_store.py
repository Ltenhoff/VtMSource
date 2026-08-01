from __future__ import annotations

import base64
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

VAMPIRE_MASTER = "V20_4-Page_Elder_Floral_Interactive.pdf"
CTHULHU_MASTER = "CoC7 PC Sheet - Auto-Fill - 1930s Pulp - Standard - Color.pdf"

EXPECTED_SHA256 = {
    VAMPIRE_MASTER: "6f1a2c9f79d1913862f9b35aa61456209fbfcabd9163920ecebf1165973e1309",
    CTHULHU_MASTER: "e7073a1ce22970ec9bad5caed0df0a6a072c9fdb44d896383dcbca8271173bfa",
}

@dataclass(frozen=True)
class CharacterSheet:
    character_id: str
    path: Path

class PdfStore:
    """Byte-preserving PDF storage. PDFs are never regenerated or flattened."""
    def __init__(self, data_root: Path, asset_root: Path) -> None:
        self.data_root = data_root
        self.asset_root = asset_root
        self.sheet_root = data_root / "CharacterSheets"
        self.sheet_root.mkdir(parents=True, exist_ok=True)

    def master_for_ruleset(self, ruleset: str) -> Path:
        name = CTHULHU_MASTER if ruleset.lower().startswith(("coc", "cthulhu", "pulp")) else VAMPIRE_MASTER
        master = self.asset_root / "reference-pdfs" / name
        if not master.is_file():
            raise FileNotFoundError(f"Missing master PDF: {master}")
        expected = EXPECTED_SHA256[name]
        actual = hashlib.sha256(master.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Master PDF checksum mismatch for {name}: {actual}")
        return master

    def character_path(self, character_id: str) -> Path:
        safe = "".join(ch for ch in character_id if ch.isalnum() or ch in "-_") or "character"
        folder = self.sheet_root / safe
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "sheet.pdf"

    def ensure_character_sheet(self, character_id: str, ruleset: str) -> CharacterSheet:
        target = self.character_path(character_id)
        if not target.exists():
            shutil.copyfile(self.master_for_ruleset(ruleset), target)
        return CharacterSheet(character_id, target)

    def import_pdf(self, character_id: str, source: Path) -> CharacterSheet:
        if not source.is_file() or source.suffix.lower() != ".pdf":
            raise ValueError("The selected file is not a PDF.")
        target = self.character_path(character_id)
        temp = target.with_suffix(".pdf.tmp")
        shutil.copyfile(source, temp)
        temp.replace(target)
        return CharacterSheet(character_id, target)

    def save_bytes(self, character_id: str, pdf_bytes: bytes) -> CharacterSheet:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError("The supplied bytes are not a PDF.")
        target = self.character_path(character_id)
        temp = target.with_suffix(".pdf.tmp")
        temp.write_bytes(pdf_bytes)
        temp.replace(target)
        return CharacterSheet(character_id, target)

    def save_base64(self, character_id: str, encoded: str) -> CharacterSheet:
        return self.save_bytes(character_id, base64.b64decode(encoded, validate=True))

    def export_pdf(self, character_id: str, destination: Path) -> Path:
        source = self.character_path(character_id)
        if not source.is_file():
            raise FileNotFoundError("This character does not have a stored PDF.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return destination

    def reset_pdf(self, character_id: str, ruleset: str) -> CharacterSheet:
        target = self.character_path(character_id)
        temp = target.with_suffix(".pdf.tmp")
        shutil.copyfile(self.master_for_ruleset(ruleset), temp)
        temp.replace(target)
        return CharacterSheet(character_id, target)
