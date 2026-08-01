
from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
import zipfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, QUrl, QPointF, QRectF, QMimeData, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QBrush, QPixmap, QPainterPath, QPolygonF, QDrag, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QFrame, QFormLayout, QDialog, QDialogButtonBox,
    QFileDialog, QMessageBox, QSplitter, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QGraphicsObject, QGraphicsItem, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar, QGroupBox, QAbstractItemView
)
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineSettings, QWebEngineDownloadRequest, QWebEnginePage
)
from PySide6.QtWebEngineWidgets import QWebEngineView

APP_NAME = "Nocturne Archive"
DATA_DIR = "NocturneArchive.PY.Data"
SCHEMA_VERSION = 2
VTM_PDF = "V20_Vampire35thAnniversary_4-Page_Interactive.pdf"
COC_PDF = "CoC7_Pulp_Default_Interactive.pdf"

STYLE = """
QWidget { background:#0c110f; color:#e6dfce; font-family: Georgia, 'Times New Roman', serif; font-size:14px; }
QMainWindow { background:#0b100e; }
QFrame#TopBar { background:#111713; border-bottom:1px solid #455047; }
QLabel#Brand { font-size:22px; letter-spacing:2px; color:#eee9dc; font-weight:600; }
QPushButton { background:#15201b; color:#f2ead8; border:1px solid #536158; padding:8px 13px; }
QPushButton:hover { background:#24352c; border-color:#8b9b90; }
QPushButton:pressed { background:#31453a; }
QPushButton#Primary { background:#526d5e; border-color:#8ca093; font-weight:600; }
QPushButton#Danger { background:#2b1719; border-color:#76464b; color:#efc7c7; }
QPushButton#Nav { border:none; border-bottom:2px solid transparent; background:transparent; padding:16px 14px; font-size:16px; color:#b9bdb5; }
QPushButton#Nav:hover { color:#fff; }
QPushButton#Nav[active="true"] { color:#fff; border-bottom-color:#a5b5aa; }
QLineEdit, QTextEdit, QComboBox { background:#0a0f0d; border:1px solid #46534b; color:#eee6d5; padding:8px; selection-background-color:#556b5e; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color:#93a398; }
QListWidget { background:#0a0f0d; border:1px solid #3f4c44; }
QListWidget::item { padding:9px; border-bottom:1px solid #29332d; }
QListWidget::item:selected { background:#1e2c25; color:white; }
QScrollArea { border:none; }
QFrame#Card { background:#101713; border:1px solid #46534b; border-radius:12px; }
QFrame#Banner { background:#211313; border:1px solid #5d4b45; border-radius:16px; }
QLabel#Eyebrow { color:#c58b53; font-size:13px; letter-spacing:2px; font-weight:600; }
QLabel#PageTitle { color:#f1e6cf; font-size:25px; font-weight:700; }
QLabel#SectionTitle { color:#e6c79b; font-size:19px; font-weight:700; }
QLabel#Hint { color:#c5aa79; font-size:12px; }
QGroupBox { border:1px solid #3f4d45; margin-top:12px; padding-top:16px; }
QGroupBox::title { color:#ddb982; left:12px; padding:0 6px; }
QTableWidget { background:#0a0f0d; gridline-color:#354139; border:1px solid #46534b; }
QHeaderView::section { background:#17211c; color:#e4d8c0; padding:7px; border:1px solid #3d4b43; }
QToolBar { background:#101713; border-bottom:1px solid #4c594f; spacing:5px; }
"""

def bundle_root() -> Path:
    return Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]

def app_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]

def data_root() -> Path:
    p = app_root() / DATA_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p

@dataclass
class Chronicle:
    id: str
    name: str
    ruleset: str = "Gothic d10"
    game: str = "Vampire"
    era: str = ""
    location: str = ""
    status: str = "Active"
    premise: str = ""
    themes: str = ""
    mood: str = ""
    summary: str = ""
    keeper_notes: str = ""
    planner: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=lambda: {
        "campaign_notes":"", "game_plot":"", "session_journal":"", "storyteller_sketchpad":""
    })

@dataclass
class Character:
    id: str
    chronicle_id: str
    name: str
    ruleset: str = "Vampire"
    role: str = "PC"
    player: str = ""
    concept: str = ""
    clan: str = ""
    condition: str = "Active"
    portrait: str = ""

def clean_dataclass(cls, row: dict[str, Any]):
    allowed = {f.name for f in fields(cls)}
    data = {k: v for k, v in row.items() if k in allowed}
    return cls(**data)

class Store:
    def __init__(self):
        self.root = data_root()
        self.db_file = self.root / "database.json"
        self.sheets = self.root / "CharacterSheets"
        self.portraits = self.root / "Portraits"
        self.asset_files = self.root / "Assets"
        self.sheets.mkdir(parents=True, exist_ok=True)
        self.portraits.mkdir(parents=True, exist_ok=True)
        self.asset_files.mkdir(parents=True, exist_ok=True)
        self.db = self.blank()
        self.load()

    @staticmethod
    def blank():
        return {
            "schema_version": SCHEMA_VERSION,
            "chronicles": [], "characters": [], "maps": {},
            "clues": [], "touchstones": [], "history": [], "assets": [],
            "last_chronicle": ""
        }

    def load(self):
        if not self.db_file.exists():
            self.save()
            return
        try:
            loaded = json.loads(self.db_file.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("Database root is not an object")
            # Load only recognized collections; malformed old records cannot break the UI.
            fresh = self.blank()
            for key in fresh:
                if key in loaded:
                    fresh[key] = loaded[key]
            if not isinstance(fresh["chronicles"], list): fresh["chronicles"] = []
            if not isinstance(fresh["characters"], list): fresh["characters"] = []
            if not isinstance(fresh["maps"], dict): fresh["maps"] = {}
            self.db = fresh
            self.save()
        except Exception:
            backup = self.db_file.with_name("database.unreadable.json")
            try: shutil.copy2(self.db_file, backup)
            except Exception: pass
            self.db = self.blank()
            self.save()

    def save(self):
        tmp = self.db_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.db, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.db_file)

    def chronicles(self):
        result = []
        for row in self.db["chronicles"]:
            try: result.append(clean_dataclass(Chronicle, row))
            except Exception: continue
        return result

    def characters(self, cid=None):
        result = []
        for row in self.db["characters"]:
            try: result.append(clean_dataclass(Character, row))
            except Exception: continue
        return [x for x in result if x.chronicle_id == cid] if cid else result

    def put_chronicle(self, c):
        rows = self.db["chronicles"]
        for i, row in enumerate(rows):
            if row.get("id") == c.id:
                rows[i] = asdict(c)
                break
        else:
            rows.append(asdict(c))
        self.db["last_chronicle"] = c.id
        self.save()

    def put_character(self, c):
        rows = self.db["characters"]
        for i, row in enumerate(rows):
            if row.get("id") == c.id:
                rows[i] = asdict(c)
                break
        else:
            rows.append(asdict(c))
        self.save()

    def delete_chronicle(self, cid):
        char_ids = {x.get("id") for x in self.db["characters"] if x.get("chronicle_id") == cid}
        self.db["chronicles"] = [x for x in self.db["chronicles"] if x.get("id") != cid]
        self.db["characters"] = [x for x in self.db["characters"] if x.get("chronicle_id") != cid]
        self.db["maps"].pop(cid, None)
        for key in ("clues", "touchstones", "history", "assets"):
            self.db[key] = [x for x in self.db[key] if x.get("chronicle_id") != cid]
        for char_id in char_ids:
            if char_id: shutil.rmtree(self.sheets / char_id, ignore_errors=True)
        self.save()

    def delete_character(self, cid):
        self.db["characters"] = [x for x in self.db["characters"] if x.get("id") != cid]
        shutil.rmtree(self.sheets / cid, ignore_errors=True)
        for portrait in self.portraits.glob(f"{cid}.*"):
            portrait.unlink(missing_ok=True)
        # Remove character from every relationship map in every chronicle.
        serialized = json.dumps(self.db.get("maps", {}))
        maps = self.db.get("maps", {})
        for chronicle_maps in maps.values():
            if not isinstance(chronicle_maps, dict):
                continue
            for map_data in chronicle_maps.values():
                if not isinstance(map_data, dict):
                    continue
                map_data.get("nodes", {}).pop(cid, None)
                map_data["edges"] = [
                    e for e in map_data.get("edges", [])
                    if e.get("source") != cid and e.get("target") != cid
                ]
                for group in map_data.get("groups", {}).values():
                    group.get("nodes", {}).pop(cid, None)
        self.save()

    def copy_portrait(self, source: str, character_id: str) -> str:
        if not source:
            return ""
        path = Path(source)
        if not path.is_file():
            return ""
        suffix = path.suffix.lower() if path.suffix else ".png"
        target = self.portraits / f"{character_id}{suffix}"
        shutil.copy2(path, target)
        return str(target)

    def copy_asset(self, source: str, asset_id: str) -> str:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(source)
        target = self.asset_files / f"{asset_id}{path.suffix}"
        shutil.copy2(path, target)
        return str(target)

    def clone_character_files(self, source_id: str, target_id: str) -> None:
        source_folder = self.sheets / source_id
        target_folder = self.sheets / target_id
        if source_folder.exists():
            shutil.copytree(source_folder, target_folder, dirs_exist_ok=True)
        for portrait in self.portraits.glob(f"{source_id}.*"):
            target = self.portraits / f"{target_id}{portrait.suffix}"
            shutil.copy2(portrait, target)

    def full_backup(self, destination: Path) -> None:
        self.save()
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in self.root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(self.root))

    def restore_backup(self, source: Path) -> None:
        temp = self.root.with_name(self.root.name + ".restore")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source, "r") as archive:
            archive.extractall(temp)
        database = temp / "database.json"
        if not database.is_file():
            shutil.rmtree(temp, ignore_errors=True)
            raise ValueError("Backup does not contain database.json")
        for child in list(self.root.iterdir()):
            if child == temp:
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        for child in temp.iterdir():
            target = self.root / child.name
            if child.is_dir():
                shutil.copytree(child, target, dirs_exist_ok=True)
            else:
                shutil.copy2(child, target)
        shutil.rmtree(temp, ignore_errors=True)
        self.sheets.mkdir(parents=True, exist_ok=True)
        self.portraits.mkdir(parents=True, exist_ok=True)
        self.asset_files.mkdir(parents=True, exist_ok=True)
        self.db = self.blank()
        self.load()

    def master_pdf(self, ruleset):
        name = COC_PDF if "cthulhu" in ruleset.lower() or "coc" in ruleset.lower() else VTM_PDF
        path = bundle_root() / "assets" / name
        if not path.is_file():
            raise FileNotFoundError(f"Bundled PDF missing: {path}")
        return path

    def char_pdf(self, char):
        folder = self.sheets / char.id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "sheet.pdf"
        if not path.exists():
            shutil.copy2(self.master_pdf(char.ruleset), path)
        return path

    def replace_pdf(self, char, source):
        source = Path(source)
        if not source.is_file() or source.suffix.lower() != ".pdf":
            raise ValueError("Selected file is not a PDF")
        target = self.char_pdf(char)
        temp = target.with_suffix(".pdf.tmp")
        shutil.copy2(source, temp)
        temp.replace(target)
        return target

    def reset_pdf(self, char):
        return self.replace_pdf(char, self.master_pdf(char.ruleset))

class ChronicleDialog(QDialog):
    def __init__(self, parent=None, c=None):
        super().__init__(parent)
        self.setWindowTitle("Chronicle")
        self.setModal(True)
        self.resize(700, 650)
        self.fields = {}
        form = QFormLayout(self)
        specs = [
            ("name","Name","line"),("ruleset","Ruleset","combo"),("game","Game / Product","line"),
            ("era","Era","line"),("location","Primary Location","line"),("status","Status","status"),
            ("premise","Premise","text"),("themes","Themes","line"),("mood","Mood","line"),
            ("summary","Chronicle Summary","text"),("keeper_notes","Keeper Notes","text")
        ]
        for key, label, kind in specs:
            value = getattr(c, key, "") if c else ""
            if kind == "text":
                widget = QTextEdit(); widget.setFixedHeight(80); widget.setPlainText(value)
            elif kind == "combo":
                widget = QComboBox(); widget.addItems(["Gothic d10", "Call of Cthulhu"]); widget.setCurrentText(value or "Gothic d10")
            elif kind == "status":
                widget = QComboBox(); widget.addItems(["Active", "Paused", "Complete"]); widget.setCurrentText(value or "Active")
            else:
                widget = QLineEdit(value)
            self.fields[key] = widget
            form.addRow(label, widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def validate(self):
        if not self.value("name").strip():
            QMessageBox.information(self, APP_NAME, "Enter a chronicle name.")
            return
        self.accept()

    def value(self, key):
        widget = self.fields[key]
        if isinstance(widget, QTextEdit): return widget.toPlainText()
        if isinstance(widget, QComboBox): return widget.currentText()
        return widget.text()

class CharacterDialog(QDialog):
    def __init__(self, parent=None, c=None):
        super().__init__(parent)
        self.setWindowTitle("Character")
        self.setModal(True)
        self.fields = {}
        form = QFormLayout(self)
        for key, label in [("name","Name"),("player","Player"),("concept","Concept"),("clan","Clan / Occupation"),("portrait","Portrait path")]:
            widget = QLineEdit(getattr(c, key, "") if c else "")
            self.fields[key] = widget
            form.addRow(label, widget)
        self.ruleset = QComboBox(); self.ruleset.addItems(["Vampire", "Call of Cthulhu"]); self.ruleset.setCurrentText(c.ruleset if c else "Vampire")
        self.role = QComboBox(); self.role.addItems(["PC", "NPC"]); self.role.setCurrentText(c.role if c else "PC")
        self.condition = QComboBox()
        self.condition.addItems(["Active","Incapacitated","Torpor","Dead","Unconscious","Maimed","Mortal Wound","Insane","Temporary Insanity","Permanent Insanity"])
        self.condition.setCurrentText(c.condition if c else "Active")
        form.addRow("Ruleset", self.ruleset); form.addRow("Role", self.role); form.addRow("Condition", self.condition)
        browse = QPushButton("Choose Portrait"); browse.clicked.connect(self.pick); form.addRow(browse)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate); buttons.rejected.connect(self.reject); form.addRow(buttons)

    def validate(self):
        if not self.fields["name"].text().strip():
            QMessageBox.information(self, APP_NAME, "Enter a character name.")
            return
        self.accept()

    def pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Portrait", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path: self.fields["portrait"].setText(path)

class PdfWindow(QMainWindow):
    def __init__(self, store, char, parent=None):
        super().__init__(parent)
        self.store = store
        self.char = char
        self.setWindowTitle(f"{char.name} — Native PDF Sheet")
        self.resize(1250, 900)
        self.profile = QWebEngineProfile(f"sheet-{char.id}", self)
        self.profile.setPersistentStoragePath(str(data_root() / "PdfProfiles" / char.id))
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.profile.downloadRequested.connect(self.download)
        self.view = QWebEngineView()
        self.view.setPage(QWebEnginePage(self.profile, self.view))
        self.setCentralWidget(self.view)
        toolbar = QToolBar("PDF")
        for title, callback in [
            ("Reload Actual PDF", self.reload), ("Import Any PDF", self.import_pdf), ("Reset to Default", self.reset),
            ("Export Stored PDF", self.export_stored), ("Open in Default Viewer", self.external)
        ]:
            action = QAction(title, self); action.triggered.connect(callback); toolbar.addAction(action)
        self.addToolBar(toolbar)
        self.reload()

    def reload(self):
        self.view.load(QUrl.fromLocalFile(str(self.store.char_pdf(self.char))))

    def import_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import PDF", "", "PDF (*.pdf)")
        if path:
            self.store.replace_pdf(self.char, path)
            self.reload()

    def reset(self):
        if QMessageBox.question(self, APP_NAME, "Restore the untouched default PDF?") == QMessageBox.Yes:
            self.store.reset_pdf(self.char)
            self.reload()

    def export_stored(self):
        source = self.store.char_pdf(self.char)
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", f"{self.char.name}.pdf", "PDF (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"): path += ".pdf"
            shutil.copy2(source, path)

    def external(self):
        os.startfile(str(self.store.char_pdf(self.char)))

    def download(self, item):
        name = item.downloadFileName() or f"{self.char.name}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", name, "PDF (*.pdf)")
        if not path:
            item.cancel(); return
        target = Path(path if path.lower().endswith(".pdf") else path + ".pdf")
        item.setDownloadDirectory(str(target.parent))
        item.setDownloadFileName(target.name)
        def done(state):
            if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted and target.exists():
                self.store.replace_pdf(self.char, target)
                self.reload()
        item.stateChanged.connect(done)
        item.accept()



class CharacterListWidget(QListWidget):
    MIME = "application/x-nocturne-character"

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        char_id = item.data(Qt.UserRole)
        if not char_id:
            return
        mime = QMimeData()
        mime.setData(self.MIME, str(char_id).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class PortraitNode(QGraphicsObject):
    moved = Signal()

    def __init__(self, char: Character, x: float, y: float, group_id: str = ""):
        super().__init__()
        self.char = char
        self.group_id = group_id
        self.radius = 44.0
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self._portrait = QPixmap(char.portrait) if char.portrait and Path(char.portrait).is_file() else QPixmap()

    def boundingRect(self):
        return QRectF(-54, -54, 108, 132)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        circle = QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        painter.setPen(QPen(QColor("#d6b26f") if self.isSelected() else QColor("#83745b"), 3))
        painter.setBrush(QColor("#111813"))
        painter.drawEllipse(circle)

        if not self._portrait.isNull():
            clip = QPainterPath()
            clip.addEllipse(circle.adjusted(4, 4, -4, -4))
            painter.save()
            painter.setClipPath(clip)
            pix = self._portrait.scaled(
                int(circle.width()-8), int(circle.height()-8),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            target = circle.adjusted(4,4,-4,-4)
            source = QRectF(
                max(0, (pix.width()-target.width())/2),
                max(0, (pix.height()-target.height())/2),
                target.width(), target.height()
            )
            painter.drawPixmap(target, pix, source)
            painter.restore()
        else:
            painter.setPen(QColor("#a99b82"))
            painter.setFont(QFont("Georgia", 22, QFont.Bold))
            initials = "".join(part[0] for part in self.char.name.split()[:2]).upper() or "?"
            painter.drawText(circle, Qt.AlignCenter, initials)

        painter.setPen(QColor("#f1e7d0"))
        painter.setFont(QFont("Georgia", 10, QFont.Bold))
        painter.drawText(QRectF(-52, 50, 104, 30), Qt.AlignHCenter | Qt.TextWordWrap, self.char.name)

        condition = self.char.condition.lower()
        if condition in {"incapacitated", "dead"}:
            painter.setPen(QPen(QColor("#d62f2f"), 4))
            painter.drawLine(QPointF(-30,-30), QPointF(30,30))
            painter.drawLine(QPointF(30,-30), QPointF(-30,30))
        elif condition == "maimed":
            painter.setPen(QPen(QColor("#d62f2f"), 4))
            painter.drawLine(QPointF(-30,30), QPointF(30,-30))
        elif condition == "mortal wound":
            painter.setPen(QPen(QColor("#d62f2f"), 4))
            painter.drawLine(QPointF(-34,24), QPointF(24,-34))
            painter.drawLine(QPointF(-24,34), QPointF(34,-24))
        elif "insan" in condition:
            count = 3 if "permanent" in condition else 2 if "temporary" in condition else 1
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Georgia", 26, QFont.Bold))
            painter.drawText(circle, Qt.AlignCenter, "?" * count)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.moved.emit()
        return result

    def mouseDoubleClickEvent(self, event):
        scene = self.scene()
        if scene and hasattr(scene, "edit_node_relationship"):
            scene.edit_node_relationship(self.char.id)
        event.accept()


class GroupFrame(QGraphicsObject):
    moved = Signal()

    def __init__(self, group_id: str, title: str, x: float, y: float, width: float = 380, height: float = 260):
        super().__init__()
        self.group_id = group_id
        self.title = title
        self.width = width
        self.height = height
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(-20)

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#0d1411"))
        painter.setPen(QPen(QColor("#726c5f") if not self.isSelected() else QColor("#d6b26f"), 2))
        painter.drawRoundedRect(self.boundingRect(), 8, 8)
        painter.setBrush(QColor("#20241f"))
        painter.drawRect(QRectF(0,0,self.width,30))
        painter.setPen(QColor("#e7ddca"))
        painter.setFont(QFont("Georgia", 11, QFont.Bold))
        painter.drawText(QRectF(10,0,self.width-20,30), Qt.AlignVCenter, self.title)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.moved.emit()
        return result


class RelationshipEdge(QGraphicsObject):
    def __init__(self, source_item, target_item, data: dict):
        super().__init__()
        self.source_item = source_item
        self.target_item = target_item
        self.data = data
        self.setZValue(-10)
        if hasattr(source_item, "moved"):
            source_item.moved.connect(self.update)
        if hasattr(target_item, "moved"):
            target_item.moved.connect(self.update)

    def _anchor(self, item):
        if isinstance(item, GroupFrame):
            rect = item.boundingRect()
            return item.scenePos() + QPointF(rect.width()/2, rect.height()/2)
        return item.scenePos()

    def boundingRect(self):
        a = self.mapFromScene(self._anchor(self.source_item))
        b = self.mapFromScene(self._anchor(self.target_item))
        return QRectF(a, b).normalized().adjusted(-80,-50,80,50)

    def paint(self, painter, option, widget=None):
        a = self.mapFromScene(self._anchor(self.source_item))
        b = self.mapFromScene(self._anchor(self.target_item))
        vector = b - a
        length = max(1.0, (vector.x()**2 + vector.y()**2) ** 0.5)
        ux, uy = vector.x()/length, vector.y()/length

        start = a
        end = b
        if isinstance(self.source_item, PortraitNode):
            start = QPointF(a.x()+ux*48, a.y()+uy*48)
        if isinstance(self.target_item, PortraitNode):
            end = QPointF(b.x()-ux*48, b.y()-uy*48)

        painter.setPen(QPen(QColor("#c18b55"), 3))
        painter.drawLine(start, end)

        arrow = self.data.get("type", "Mutual")
        if arrow in ("One-way", "Mutual"):
            self._arrow(painter, end, ux, uy)
        if arrow == "Mutual":
            self._arrow(painter, start, -ux, -uy)

        note = self.data.get("note", "")
        if note:
            mid = QPointF((start.x()+end.x())/2, (start.y()+end.y())/2)
            normal = QPointF(-uy, ux)
            pos = QPointF(mid.x()+normal.x()*16, mid.y()+normal.y()*16)
            rect = QRectF(pos.x()-75, pos.y()-12, 150, 24)
            painter.setBrush(QColor("#0c110f"))
            painter.setPen(QPen(QColor("#a66142") if self.data.get("side","A")=="A" else QColor("#c59a4f"), 1))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor("#f1e7d0"))
            painter.setFont(QFont("Georgia", 9))
            painter.drawText(rect, Qt.AlignCenter, note[:20])

    def _arrow(self, painter, point, ux, uy):
        normal = QPointF(-uy, ux)
        back = QPointF(point.x()-ux*14, point.y()-uy*14)
        p1 = QPointF(back.x()+normal.x()*7, back.y()+normal.y()*7)
        p2 = QPointF(back.x()-normal.x()*7, back.y()-normal.y()*7)
        painter.setBrush(QColor("#c18b55"))
        painter.drawPolygon(QPolygonF([point,p1,p2]))


class RelationshipDialog(QDialog):
    def __init__(self, source: Character, candidates: list[Character], existing=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Relationship — {source.name}")
        self.setModal(True)
        self.target = QComboBox()
        for char in candidates:
            self.target.addItem(char.name, char.id)
        self.arrow = QComboBox()
        self.arrow.addItems(["None", "One-way", "Mutual"])
        self.note = QLineEdit()
        self.note.setMaxLength(20)

        if existing:
            idx = self.target.findData(existing.get("target"))
            if idx >= 0:
                self.target.setCurrentIndex(idx)
            self.arrow.setCurrentText(existing.get("type","Mutual"))
            self.note.setText(existing.get("note",""))

        form = QFormLayout(self)
        form.addRow("Target", self.target)
        form.addRow("Arrow type", self.arrow)
        form.addRow("Note (20 characters)", self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class RelationshipMapWidget(QWidget):
    """
    Legacy Nocturne Archive relationship-map behavior rebuilt in Python:
    - private map per character
    - campaign map per chronicle
    - private-map imports into campaign map as movable groups
    - drag-in from character list
    - relationship propagation across both characters' private maps
    - dialog-driven None / One-way / Mutual links with notes
    - deleting from map removes both ends from related private maps
    """
    def __init__(self, store: Store, chronicle_provider, characters_provider, parent=None):
        super().__init__(parent)
        self.store = store
        self.chronicle_provider = chronicle_provider
        self.characters_provider = characters_provider
        self.mode = "Private"
        self.private_character_id = ""
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-1800,-1200,3600,2400)
        self.scene.edit_node_relationship = self.edit_node_relationship
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.view.setAcceptDrops(True)
        self.view.viewport().setAcceptDrops(True)
        self.view.viewport().installEventFilter(self)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Private Character Map","Campaign Map"])
        self.mode_combo.currentTextChanged.connect(self.change_mode)

        self.private_combo = QComboBox()
        self.private_combo.currentIndexChanged.connect(self.change_private)

        self.import_group_btn = QPushButton("Import Character Map")
        self.import_group_btn.clicked.connect(self.import_private_group)
        self.link_btn = QPushButton("Link Individuals or Groups")
        self.link_btn.clicked.connect(self.link_selected)
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.save_btn = QPushButton("Save Map")
        self.save_btn.clicked.connect(self.save_current)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Map"))
        bar.addWidget(self.mode_combo)
        bar.addWidget(self.private_combo)
        bar.addWidget(self.import_group_btn)
        bar.addWidget(self.link_btn)
        bar.addWidget(self.remove_btn)
        bar.addWidget(self.save_btn)
        bar.addStretch()

        self.help = QLabel(
            "Private maps belong to one character. Drag same-chronicle characters from the left list. "
            "Double-click a portrait to edit its relationship. Campaign maps import private maps as groups. "
            "Positions, links, labels, and imported groups are saved."
        )
        self.help.setWordWrap(True)
        self.help.setObjectName("Hint")

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.help)
        layout.addWidget(self.view,1)

        self.import_group_btn.setVisible(False)
        self.refresh_private_combo()

    def change_mode(self, text):
        self.save_current()
        self.mode = "Campaign" if text.startswith("Campaign") else "Private"
        self.private_combo.setVisible(self.mode == "Private")
        self.import_group_btn.setVisible(self.mode == "Campaign")
        self.refresh_private_combo()
        self.load_current()

    def refresh_private_combo(self):
        current = self.private_character_id
        self.private_combo.blockSignals(True)
        self.private_combo.clear()
        for char in self.characters_provider():
            self.private_combo.addItem(char.name, char.id)
        idx = self.private_combo.findData(current)
        if idx >= 0:
            self.private_combo.setCurrentIndex(idx)
        elif self.private_combo.count():
            self.private_combo.setCurrentIndex(0)
            self.private_character_id = self.private_combo.currentData()
        else:
            self.private_character_id = ""
        self.private_combo.blockSignals(False)

    def change_private(self, index):
        self.save_current()
        self.private_character_id = self.private_combo.itemData(index) or ""
        if self.mode == "Private":
            self.load_current()

    def _chronicle_maps(self):
        cid = self.chronicle_provider()
        return self.store.db.setdefault("maps", {}).setdefault(cid, {}) if cid else {}

    def _private_key(self, char_id):
        return f"private:{char_id}"

    def _campaign_key(self):
        return f"campaign:{self.chronicle_provider()}"

    def current_key(self):
        return self._campaign_key() if self.mode == "Campaign" else self._private_key(self.private_character_id)

    def current_data(self):
        maps = self._chronicle_maps()
        key = self.current_key()
        return maps.setdefault(key, {"nodes":{}, "edges":[], "groups":{}}) if key else {"nodes":{}, "edges":[], "groups":{}}

    def eventFilter(self, watched, event):
        if watched is self.view.viewport():
            if event.type() == event.Type.DragEnter and event.mimeData().hasFormat(CharacterListWidget.MIME):
                event.acceptProposedAction()
                return True
            if event.type() == event.Type.DragMove and event.mimeData().hasFormat(CharacterListWidget.MIME):
                event.acceptProposedAction()
                return True
            if event.type() == event.Type.Drop and event.mimeData().hasFormat(CharacterListWidget.MIME):
                char_id = bytes(event.mimeData().data(CharacterListWidget.MIME)).decode("utf-8")
                pos = self.view.mapToScene(event.position().toPoint())
                self.add_character(char_id, pos)
                event.acceptProposedAction()
                return True
        return super().eventFilter(watched, event)

    def add_character(self, char_id, pos):
        chars = {c.id:c for c in self.characters_provider()}
        char = chars.get(char_id)
        if not char:
            return
        data = self.current_data()
        data["nodes"][char_id] = {"x":pos.x(),"y":pos.y()}
        self.store.save()
        self.load_current()

    def load_current(self):
        self.scene.clear()
        self.refresh_private_combo()
        if not self.chronicle_provider():
            return

        chars = {c.id:c for c in self.characters_provider()}
        data = self.current_data()

        if self.mode == "Private" and self.private_character_id in chars:
            data["nodes"].setdefault(self.private_character_id, {"x":0,"y":0})

        if self.mode == "Campaign":
            # Import groups first.
            for group_id, group in data.get("groups", {}).items():
                frame = GroupFrame(
                    group_id,
                    group.get("title","Private Map"),
                    group.get("x",0), group.get("y",0),
                    group.get("width",380), group.get("height",260)
                )
                self.scene.addItem(frame)

                # Nodes inside groups use absolute scene positions derived from the frame.
                for char_id, relpos in group.get("nodes", {}).items():
                    char = chars.get(char_id)
                    if not char:
                        continue
                    node = PortraitNode(
                        char,
                        frame.x()+relpos.get("x",80),
                        frame.y()+relpos.get("y",80),
                        group_id=group_id
                    )
                    self.scene.addItem(node)

            # Loose campaign nodes.
            for char_id, pos in data.get("nodes", {}).items():
                char = chars.get(char_id)
                if char:
                    self.scene.addItem(PortraitNode(char,pos.get("x",0),pos.get("y",0)))
        else:
            for char_id, pos in data.get("nodes", {}).items():
                char = chars.get(char_id)
                if char:
                    self.scene.addItem(PortraitNode(char,pos.get("x",0),pos.get("y",0)))

        self.draw_edges()

    def node_items(self):
        return {item.char.id:item for item in self.scene.items() if isinstance(item,PortraitNode)}

    def group_items(self):
        return {item.group_id:item for item in self.scene.items() if isinstance(item,GroupFrame)}

    def draw_edges(self):
        for item in list(self.scene.items()):
            if isinstance(item,RelationshipEdge):
                self.scene.removeItem(item)

        nodes = self.node_items()
        groups = self.group_items()
        for edge in self.current_data().get("edges", []):
            src = groups.get(edge.get("source")) or nodes.get(edge.get("source"))
            dst = groups.get(edge.get("target")) or nodes.get(edge.get("target"))
            if src and dst and edge.get("type") != "None":
                self.scene.addItem(RelationshipEdge(src,dst,edge))

    def selected_nodes_or_groups(self):
        return [i for i in self.scene.selectedItems() if isinstance(i,(PortraitNode,GroupFrame))]

    def link_selected(self):
        selected = self.selected_nodes_or_groups()
        if len(selected) != 2:
            QMessageBox.information(self, APP_NAME, "Select exactly two portraits or groups.")
            return

        def ident(item):
            return item.group_id if isinstance(item,GroupFrame) else item.char.id

        src_id, dst_id = ident(selected[0]), ident(selected[1])
        arrow, ok = QInputDialog.getItem(self, "Arrow Type", "Relationship", ["None","One-way","Mutual"], 2, False)
        if not ok:
            return
        note, ok = QInputDialog.getText(self, "Relationship Note", "Note (20 characters)")
        if not ok:
            return

        data = self.current_data()
        data["edges"] = [
            e for e in data.get("edges",[])
            if not (e.get("source")==src_id and e.get("target")==dst_id)
        ]
        if arrow != "None":
            data["edges"].append({"source":src_id,"target":dst_id,"type":arrow,"note":note[:20]})
        self.save_current()

    def edit_node_relationship(self, source_id):
        nodes = self.node_items()
        source = nodes.get(source_id)
        if not source:
            return
        candidates = [n.char for cid,n in nodes.items() if cid != source_id]
        if not candidates:
            QMessageBox.information(self, APP_NAME, "Add another character to this map first.")
            return

        existing = next(
            (e for e in self.current_data().get("edges",[]) if e.get("source")==source_id),
            None
        )
        dialog = RelationshipDialog(source.char,candidates,existing,self)
        if dialog.exec():
            target_id = dialog.target.currentData()
            arrow = dialog.arrow.currentText()
            note = dialog.note.text().strip()

            if self.mode == "Private":
                self._store_private_pair(source_id,target_id,arrow,note)
            else:
                data = self.current_data()
                data["edges"] = [
                    e for e in data.get("edges",[])
                    if not (e.get("source")==source_id and e.get("target")==target_id)
                ]
                if arrow != "None":
                    data["edges"].append({"source":source_id,"target":target_id,"type":arrow,"note":note[:20]})
                self.save_current()

    def _store_private_pair(self, source_id, target_id, arrow, note):
        """
        Store on both private maps so relationship changes propagate.
        One-way source->target becomes a mirrored record on target's map that still
        points back to source, preserving both characters' view of the same relation.
        """
        maps = self._chronicle_maps()

        src_map = maps.setdefault(self._private_key(source_id), {"nodes":{}, "edges":[], "groups":{}})
        dst_map = maps.setdefault(self._private_key(target_id), {"nodes":{}, "edges":[], "groups":{}})
        src_map["nodes"].setdefault(source_id,{"x":0,"y":0})
        src_map["nodes"].setdefault(target_id,{"x":180,"y":0})
        dst_map["nodes"].setdefault(target_id,{"x":0,"y":0})
        dst_map["nodes"].setdefault(source_id,{"x":180,"y":0})

        src_map["edges"] = [e for e in src_map.get("edges",[]) if not ({e.get("source"),e.get("target")}=={source_id,target_id})]
        dst_map["edges"] = [e for e in dst_map.get("edges",[]) if not ({e.get("source"),e.get("target")}=={source_id,target_id})]

        if arrow != "None":
            src_map["edges"].append({"source":source_id,"target":target_id,"type":arrow,"note":note[:20],"side":"A"})
            mirrored = "Mutual" if arrow=="Mutual" else "One-way"
            dst_map["edges"].append({"source":source_id,"target":target_id,"type":mirrored,"note":note[:20],"side":"B"})

        self.store.save()
        self.load_current()

    def import_private_group(self):
        if self.mode != "Campaign":
            return
        chars = self.characters_provider()
        if not chars:
            QMessageBox.information(self, APP_NAME, "There are no characters to import.")
            return

        names = [c.name for c in chars]
        name, ok = QInputDialog.getItem(self, "Import Character Map", "Character map", names, 0, False)
        if not ok:
            return
        char = chars[names.index(name)]
        maps = self._chronicle_maps()
        source = maps.setdefault(self._private_key(char.id), {"nodes":{char.id:{"x":0,"y":0}},"edges":[],"groups":{}})
        data = self.current_data()

        group_id = f"group:{char.id}"
        if group_id in data["groups"]:
            QMessageBox.information(self, APP_NAME, "That private map is already imported.")
            return

        # Normalize private node coordinates into the group.
        xs = [p.get("x",0) for p in source.get("nodes",{}).values()] or [0]
        ys = [p.get("y",0) for p in source.get("nodes",{}).values()] or [0]
        min_x, min_y = min(xs), min(ys)
        group_nodes = {
            cid: {"x":p.get("x",0)-min_x+70, "y":p.get("y",0)-min_y+70}
            for cid,p in source.get("nodes",{}).items()
        }

        data["groups"][group_id] = {
            "title": f"{char.name} — Private Map",
            "x": 100 + len(data["groups"])*40,
            "y": 100 + len(data["groups"])*40,
            "width": max(380, max((p["x"] for p in group_nodes.values()), default=250)+90),
            "height": max(260, max((p["y"] for p in group_nodes.values()), default=150)+90),
            "nodes": group_nodes,
            "source_character": char.id,
            "source_edges": list(source.get("edges",[]))
        }

        # Import the private map's internal relations into the campaign scene.
        for edge in source.get("edges",[]):
            data["edges"].append(dict(edge))

        self.store.save()
        self.load_current()

    def remove_selected(self):
        selected = self.selected_nodes_or_groups()
        if not selected:
            QMessageBox.information(self, APP_NAME, "Select one or more portraits or groups.")
            return

        data = self.current_data()
        remove_ids = set()
        for item in selected:
            if isinstance(item,GroupFrame):
                remove_ids.add(item.group_id)
                data.get("groups",{}).pop(item.group_id,None)
            else:
                remove_ids.add(item.char.id)
                data.get("nodes",{}).pop(item.char.id,None)

        data["edges"] = [
            e for e in data.get("edges",[])
            if e.get("source") not in remove_ids and e.get("target") not in remove_ids
        ]

        # Private-map deletion also removes the corresponding relationship from both ends.
        if self.mode == "Private":
            maps = self._chronicle_maps()
            owner = self.private_character_id
            for removed in list(remove_ids):
                if removed == owner:
                    continue
                for key in (self._private_key(owner), self._private_key(removed)):
                    m = maps.setdefault(key,{"nodes":{},"edges":[],"groups":{}})
                    m["edges"] = [
                        e for e in m.get("edges",[])
                        if not ({e.get("source"),e.get("target")}=={owner,removed})
                    ]
                    if key == self._private_key(owner):
                        m["nodes"].pop(removed,None)

        self.store.save()
        self.load_current()

    def save_current(self):
        if not self.chronicle_provider():
            return

        data = self.current_data()

        # Save loose nodes.
        loose_nodes = {}
        for char_id,node in self.node_items().items():
            if not node.group_id:
                loose_nodes[char_id] = {"x":node.x(),"y":node.y()}
        data["nodes"] = loose_nodes

        # Save group positions and member positions relative to group.
        groups = self.group_items()
        for group_id,frame in groups.items():
            group_data = data.get("groups",{}).setdefault(group_id,{})
            group_data["x"] = frame.x()
            group_data["y"] = frame.y()
            group_data["width"] = frame.width
            group_data["height"] = frame.height
            member_positions = {}
            for char_id,node in self.node_items().items():
                if node.group_id == group_id:
                    member_positions[char_id] = {
                        "x":node.x()-frame.x(),
                        "y":node.y()-frame.y()
                    }
            group_data["nodes"] = member_positions

        self.store.save()
        self.load_current()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = Store()
        self.cid = ""
        self.charid = ""
        self.pdfwins = []
        self.current_planner_section = "Campaign Identity"
        self.loading = False
        self.setWindowTitle(APP_NAME)
        self.resize(1500, 950)
        self.setMinimumSize(1100, 720)
        self.setWindowIcon(QIcon(str(bundle_root() / "assets" / "NocturneArchive-V.ico")))
        self.setStyleSheet(STYLE)
        self.autosave = QTimer(self)
        self.autosave.setInterval(500)
        self.autosave.setSingleShot(True)
        self.autosave.timeout.connect(self.persist_current)

        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        outer.addWidget(self.topbar())
        body = QSplitter()
        body.addWidget(self.sidebar())
        self.pages = QStackedWidget()
        body.addWidget(self.pages)
        body.setStretchFactor(1, 1)
        outer.addWidget(body, 1)
        self.build_pages()
        self.refresh_chronicles()
        self.switch_page(0)

    def topbar(self):
        frame = QFrame(); frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame); layout.setContentsMargins(12,0,12,0)
        brand = QLabel("NOCTURNE ARCHIVE"); brand.setObjectName("Brand"); layout.addWidget(brand); layout.addSpacing(20)
        self.nav = []
        for index, text in enumerate(["Campaign Planner","Chronicle","Relationship Map","Character","Clue Board","Touchstones","Investigator History","Assets","Tools"]):
            button = QPushButton(text); button.setObjectName("Nav"); button.setProperty("active", False)
            button.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            layout.addWidget(button); self.nav.append(button)
        layout.addStretch()
        save = QPushButton("Save"); save.clicked.connect(self.manual_save); layout.addWidget(save)
        return frame

    def sidebar(self):
        frame = QFrame(); frame.setFixedWidth(305)
        layout = QVBoxLayout(frame); layout.setContentsMargins(12,18,12,12)
        brand = QLabel("NOCTURNE ARCHIVE"); brand.setObjectName("Brand"); layout.addWidget(brand)

        campaign = QGroupBox("CAMPAIGN")
        box = QVBoxLayout(campaign)
        self.chronicles = QComboBox()
        self.chronicles.currentIndexChanged.connect(self.choose_chronicle)
        box.addWidget(self.chronicles)
        row = QHBoxLayout()
        self.new_campaign = QLineEdit(); self.new_campaign.setPlaceholderText("New campaign name")
        self.new_campaign.returnPressed.connect(self.quick_create)
        row.addWidget(self.new_campaign)
        create = QPushButton("Create"); create.setObjectName("Primary"); create.clicked.connect(self.quick_create)
        row.addWidget(create); box.addLayout(row)
        actions = QHBoxLayout()
        for title, callback in [("Edit",self.edit_chronicle),("Export",self.export_data),("Import",self.import_data)]:
            button = QPushButton(title); button.clicked.connect(callback); actions.addWidget(button)
        box.addLayout(actions); layout.addWidget(campaign)

        trans = QGroupBox("TRANSMOGRIFIER")
        trans_row = QHBoxLayout(trans)
        self.clone_source = QComboBox(); trans_row.addWidget(self.clone_source)
        clone = QPushButton("Clone"); clone.clicked.connect(self.clone_chronicle); trans_row.addWidget(clone)
        layout.addWidget(trans)

        layout.addWidget(QLabel("CHARACTER SEARCH"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Search selected directory")
        self.search.textChanged.connect(self.refresh_characters); layout.addWidget(self.search)
        char_row = QHBoxLayout()
        add = QPushButton("New Character"); add.setObjectName("Primary"); add.clicked.connect(self.add_character)
        show = QPushButton("Show All"); show.clicked.connect(lambda: self.search.clear())
        char_row.addWidget(add); char_row.addWidget(show); layout.addLayout(char_row)
        char_actions = QHBoxLayout()
        clone_char = QPushButton("Clone Character"); clone_char.clicked.connect(self.clone_character)
        sheet_char = QPushButton("Open Sheet"); sheet_char.clicked.connect(self.open_sheet)
        char_actions.addWidget(clone_char); char_actions.addWidget(sheet_char); layout.addLayout(char_actions)
        self.charlist = CharacterListWidget()
        self.charlist.setDragEnabled(True)
        self.charlist.currentItemChanged.connect(self.choose_character)
        self.charlist.itemDoubleClicked.connect(lambda _: self.open_sheet())
        layout.addWidget(self.charlist, 1)
        layout.addWidget(QLabel("Chronicles and uploaded images are stored persistently on this device."))
        return frame

    def build_pages(self):
        self.pages.addWidget(self.planner_page())
        self.pages.addWidget(self.chronicle_page())
        self.pages.addWidget(self.map_page())
        self.pages.addWidget(self.character_page())
        self.pages.addWidget(self.clue_page())
        self.pages.addWidget(self.touchstone_page())
        self.pages.addWidget(self.history_page())
        self.pages.addWidget(self.assets_page())
        self.pages.addWidget(self.tools_page())

    def wrap(self, inner):
        area = QScrollArea(); area.setWidgetResizable(True); area.setWidget(inner); return area

    def banner(self, eyebrow, title, description):
        frame = QFrame(); frame.setObjectName("Banner")
        layout = QGridLayout(frame)
        eye = QLabel(eyebrow.upper()); eye.setObjectName("Eyebrow")
        page_title = QLabel(title); page_title.setObjectName("PageTitle")
        desc = QLabel(description); desc.setWordWrap(True)
        layout.addWidget(eye,0,0); layout.addWidget(page_title,1,0); layout.addWidget(desc,2,0)
        frame.page_title = page_title
        return frame

    def planner_page(self):
        inner = QWidget(); layout = QVBoxLayout(inner)
        self.plan_banner = self.banner("Campaign Planning Core","No campaign selected","The living design document for premise, conflict, structure, clues, sessions, characters, factions, locations, consequences, and completion.")
        layout.addWidget(self.plan_banner)
        card = QFrame(); card.setObjectName("Card"); grid = QGridLayout(card)
        sections = list(self.all_planner_specs().keys())
        for i, section in enumerate(sections):
            button = QPushButton(section)
            button.clicked.connect(lambda checked=False, name=section: self.show_planner_section(name))
            grid.addWidget(button, i//4, i%4)
        layout.addWidget(card)
        self.section_title = QLabel("Campaign Identity"); self.section_title.setObjectName("SectionTitle"); layout.addWidget(self.section_title)
        self.plan_fields = {}
        self.plan_form = QGridLayout(); layout.addLayout(self.plan_form)
        layout.addStretch()
        self.show_planner_section("Campaign Identity")
        return self.wrap(inner)

    def all_planner_specs(self):
        return {
            "Campaign Identity":[("subtitle","Subtitle","line"),("edition","Edition","line"),("genre","Genre","line"),("tone","Tone","line"),("intended_length","Intended Length","line"),("session_frequency","Session Frequency","line"),("current_date","Current In-Game Date","line"),("current_arc","Current Story Arc","line"),("inspirations","Inspirations and Touchstones","text"),("promise","What experience are you promising the players?","text")],
            "Premise & Overview":[("premise_long","Campaign Premise","text"),("central_question","Central Dramatic Question","text"),("opening_situation","Opening Situation","text"),("end_state","Possible End State","text")],
            "Core Conflict & Stakes":[("main_conflict","Main Conflict","text"),("stakes","Stakes","text"),("failure","Consequences of Failure","text"),("success","Consequences of Success","text")],
            "Story Structure & Expected Stages":[("act1","Opening Stage","text"),("act2","Escalation Stage","text"),("act3","Crisis Stage","text"),("act4","Resolution Stage","text")],
            "Timeline, Clocks & Pacing":[("timeline","Timeline","text"),("clocks","Clocks and Countdown Tracks","text"),("pace","Pacing Notes","text")],
            "Setting & Atmosphere":[("locations","Key Locations","text"),("atmosphere","Atmosphere","text"),("sensory","Sensory Details","text")],
            "Mystery, Clues & Revelations":[("mystery","Central Mystery","text"),("clues","Clues","text"),("reveals","Revelations","text"),("red_herrings","Red Herrings","text")],
            "Session Planning":[("next_session","Next Session","text"),("scenes","Planned Scenes","text"),("contingencies","Contingencies","text")],
            "Player Characters & Character Arcs":[("pc_arcs","Character Arcs","text"),("personal_stakes","Personal Stakes","text"),("spotlight","Spotlight Balance","text")],
            "Themes, Horror & Safety":[("themes_long","Themes","text"),("horror","Horror Palette","text"),("safety","Safety Tools and Boundaries","text")],
            "Factions, Politics & Power":[("factions","Factions","text"),("politics","Political Tensions","text"),("power","Power Structures","text")],
            "Rewards, Advancement & Consequences":[("rewards","Rewards","text"),("advancement","Advancement","text"),("consequences","Consequences","text")],
            "Campaign Operations":[("schedule","Schedule","text"),("house_rules","House Rules","text"),("logistics","Logistics","text")],
            "Completion, Loose Ends & Future Ideas":[("loose_ends","Loose Ends","text"),("future","Future Ideas","text"),("epilogue","Epilogue Notes","text")]
        }

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def show_planner_section(self, name):
        self.save_visible_planner_fields()
        self.current_planner_section = name
        self.section_title.setText(name)
        self.clear_layout(self.plan_form)
        self.plan_fields = {}
        for i, (key,label,kind) in enumerate(self.all_planner_specs()[name]):
            label_widget = QLabel(label); label_widget.setObjectName("Hint")
            editor = QTextEdit() if kind == "text" else QLineEdit()
            if isinstance(editor, QTextEdit): editor.setMinimumHeight(95)
            editor.textChanged.connect(self.queue_autosave)
            self.plan_form.addWidget(label_widget,(i//2)*2,i%2)
            self.plan_form.addWidget(editor,(i//2)*2+1,i%2)
            self.plan_fields[key] = editor
        self.load_planner_fields()

    def chronicle_page(self):
        inner = QWidget(); layout = QVBoxLayout(inner)
        self.chron_banner = self.banner("Chronicle","No campaign selected","Campaign overview and working notes.")
        layout.addWidget(self.chron_banner)
        self.note_fields = {}
        for key,title in [("campaign_notes","Campaign Notes"),("game_plot","Game Plot"),("session_journal","Session Journal"),("storyteller_sketchpad","Storyteller Scratchpad")]:
            card = QFrame(); card.setObjectName("Card"); card_layout = QVBoxLayout(card)
            label = QLabel(title); label.setObjectName("SectionTitle"); card_layout.addWidget(label)
            editor = QTextEdit(); editor.setMinimumHeight(150); editor.textChanged.connect(self.queue_autosave)
            card_layout.addWidget(editor); layout.addWidget(card); self.note_fields[key] = editor
        return self.wrap(inner)

    def map_page(self):
        self.relationship_map = RelationshipMapWidget(
            self.store,
            lambda: self.cid,
            lambda: self.store.characters(self.cid)
        )
        return self.relationship_map

    def character_page(self):
        inner = QWidget()
        layout = QVBoxLayout(inner)
        self.char_banner = self.banner(
            "Character", "No character selected",
            "Identity, portrait, condition, and the character's actual stored PDF."
        )
        layout.addWidget(self.char_banner)

        card = QFrame(); card.setObjectName("Card")
        grid = QGridLayout(card)
        self.portrait = QLabel()
        self.portrait.setFixedSize(420, 520)
        self.portrait.setScaledContents(True)
        grid.addWidget(self.portrait, 0, 0, 8, 1)

        self.charinfo = QTextEdit()
        self.charinfo.setReadOnly(True)
        grid.addWidget(self.charinfo, 0, 1)

        self.pdf_status = QLabel("No character sheet selected.")
        self.pdf_status.setWordWrap(True)
        self.pdf_status.setObjectName("Hint")
        grid.addWidget(self.pdf_status, 1, 1)

        actions = [
            ("Edit Identity", self.edit_character),
            ("Open PDF Window", self.open_sheet),
            ("Open PDF in Default Viewer", self.open_char_pdf_external),
            ("Import Any PDF", self.import_char_pdf),
            ("Export Stored PDF", self.export_char_pdf),
            ("Reset to Ruleset Default", self.reset_char_pdf),
            ("Clone Character", self.clone_character),
            ("Delete Character", self.delete_character),
        ]
        for row, (title, callback) in enumerate(actions, 2):
            button = QPushButton(title)
            if title == "Delete Character":
                button.setObjectName("Danger")
            button.clicked.connect(callback)
            grid.addWidget(button, row, 1)

        layout.addWidget(card)
        layout.addStretch()
        return self.wrap(inner)

    def manager_page(self, title, description, columns):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.banner(title, title, description))
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(table)
        return page, layout, table

    def clue_page(self):
        page, layout, self.clue_table = self.manager_page(
            "Clue Board",
            "Create persistent clues with a title, notes, and the character who found them.",
            ["Title", "Notes", "Found By"]
        )
        row = QHBoxLayout()
        add = QPushButton("Add Clue"); add.clicked.connect(self.add_clue)
        edit = QPushButton("Edit Selected"); edit.clicked.connect(self.edit_clue)
        delete = QPushButton("Delete Selected"); delete.clicked.connect(self.delete_clue)
        row.addWidget(add); row.addWidget(edit); row.addWidget(delete); row.addStretch()
        layout.addLayout(row)
        return page

    def touchstone_page(self):
        page, layout, self.touchstone_table = self.manager_page(
            "Touchstones",
            "Track touchstones, linked characters, connection details, and notes.",
            ["Name", "Character", "Connection", "Notes"]
        )
        row = QHBoxLayout()
        add = QPushButton("Add Touchstone"); add.clicked.connect(self.add_touchstone)
        edit = QPushButton("Edit Selected"); edit.clicked.connect(self.edit_touchstone)
        delete = QPushButton("Delete Selected"); delete.clicked.connect(self.delete_touchstone)
        row.addWidget(add); row.addWidget(edit); row.addWidget(delete); row.addStretch()
        layout.addLayout(row)
        return page

    def history_page(self):
        page, layout, self.history_table = self.manager_page(
            "Investigator History",
            "Store investigator history, eras, connections, and long-form notes.",
            ["Investigator", "Era", "Connection", "History"]
        )
        row = QHBoxLayout()
        add = QPushButton("Add Entry"); add.clicked.connect(self.add_history)
        edit = QPushButton("Edit Selected"); edit.clicked.connect(self.edit_history)
        delete = QPushButton("Delete Selected"); delete.clicked.connect(self.delete_history)
        row.addWidget(add); row.addWidget(edit); row.addWidget(delete); row.addStretch()
        layout.addLayout(row)
        return page

    def assets_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.banner(
            "Assets", "Campaign Assets",
            "Files are copied into the archive so they remain available after the original file moves."
        ))
        self.asset_table = QTableWidget(0, 3)
        self.asset_table.setHorizontalHeaderLabels(["Name", "Type", "Stored Path"])
        self.asset_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.asset_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.asset_table)
        row = QHBoxLayout()
        add = QPushButton("Add Asset"); add.clicked.connect(self.add_asset)
        open_button = QPushButton("Open Selected"); open_button.clicked.connect(self.open_asset)
        delete = QPushButton("Delete Selected"); delete.clicked.connect(self.delete_asset)
        row.addWidget(add); row.addWidget(open_button); row.addWidget(delete); row.addStretch()
        layout.addLayout(row)
        return page

    def tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.banner(
            "Tools", "Archive Tools",
            "Full backups include campaigns, characters, portraits, PDFs, relationship maps, and assets."
        ))
        actions = [
            ("Export Full Archive ZIP", self.export_full_backup),
            ("Restore Full Archive ZIP", self.import_full_backup),
            ("Export JSON Only", self.export_data),
            ("Import JSON Only", self.import_data),
            ("Open Data Folder", lambda: os.startfile(str(data_root()))),
            ("Delete Selected Chronicle", self.delete_chronicle),
        ]
        for title, callback in actions:
            button = QPushButton(title)
            if title == "Delete Selected Chronicle":
                button.setObjectName("Danger")
            button.clicked.connect(callback)
            layout.addWidget(button)
        layout.addStretch()
        return page

    def current_chronicle(self):
        return next((c for c in self.store.chronicles() if c.id == self.cid), None)

    def current_character(self):
        return next((c for c in self.store.characters() if c.id == self.charid), None)

    def queue_autosave(self):
        if not self.loading:
            self.autosave.start()

    def manual_save(self):
        self.persist_current()
        QMessageBox.information(self, APP_NAME, "Saved.")

    def save_visible_planner_fields(self):
        chronicle = self.current_chronicle()
        if not chronicle: return
        for key, editor in self.plan_fields.items():
            chronicle.planner[key] = editor.toPlainText() if isinstance(editor, QTextEdit) else editor.text()
        self.store.put_chronicle(chronicle)

    def persist_current(self):
        if self.loading: return
        chronicle = self.current_chronicle()
        if not chronicle: return
        for key, editor in self.plan_fields.items():
            chronicle.planner[key] = editor.toPlainText() if isinstance(editor, QTextEdit) else editor.text()
        for key, editor in self.note_fields.items():
            chronicle.notes[key] = editor.toPlainText()
        self.store.put_chronicle(chronicle)

    def switch_page(self, index):
        self.persist_current()
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.nav):
            button.setProperty("active", i == index)
            button.style().unpolish(button); button.style().polish(button)
        if index == 2: self.relationship_map.load_current()
        self.refresh_managers()

    def refresh_chronicles(self):
        wanted = self.cid or self.store.db.get("last_chronicle","")
        self.loading = True
        self.chronicles.blockSignals(True)
        self.chronicles.clear(); self.clone_source.clear()
        for chronicle in self.store.chronicles():
            self.chronicles.addItem(chronicle.name, chronicle.id)
            self.clone_source.addItem(chronicle.name, chronicle.id)
        self.chronicles.blockSignals(False)
        if self.chronicles.count():
            index = self.chronicles.findData(wanted)
            self.chronicles.setCurrentIndex(index if index >= 0 else 0)
            self.cid = self.chronicles.currentData()
        else:
            self.cid = ""
        self.loading = False
        self.refresh_characters()
        self.refresh_views()

    def choose_chronicle(self, index):
        if self.loading: return
        self.persist_current()
        self.cid = self.chronicles.itemData(index) or ""
        self.charid = ""
        self.store.db["last_chronicle"] = self.cid
        self.store.save()
        self.refresh_characters()
        self.refresh_views()

    def refresh_characters(self):
        self.charlist.blockSignals(True)
        self.charlist.clear()
        term = self.search.text().strip().lower()
        for char in self.store.characters(self.cid):
            if term and term not in char.name.lower(): continue
            item = QListWidgetItem(f"{char.name}\n{char.role} · {char.condition}\n{char.ruleset}")
            item.setData(Qt.UserRole, char.id)
            self.charlist.addItem(item)
        self.charlist.blockSignals(False)
        if self.charid:
            for i in range(self.charlist.count()):
                if self.charlist.item(i).data(Qt.UserRole) == self.charid:
                    self.charlist.setCurrentRow(i); break

    def select_character_in_list(self, char_id):
        for index in range(self.charlist.count()):
            item = self.charlist.item(index)
            if item.data(Qt.UserRole) == char_id:
                self.charlist.setCurrentRow(index)
                return

    def choose_character(self, item, previous):
        self.charid = item.data(Qt.UserRole) if item else ""
        self.refresh_character_view()

    def refresh_views(self):
        chronicle = self.current_chronicle()
        title = chronicle.name if chronicle else "No campaign selected"
        self.plan_banner.page_title.setText(title)
        self.chron_banner.page_title.setText(title)
        self.load_planner_fields()
        self.loading = True
        for key, editor in self.note_fields.items():
            editor.setPlainText(chronicle.notes.get(key,"") if chronicle else "")
        self.loading = False
        self.refresh_character_view()
        self.refresh_assets()
        self.refresh_managers()

    def refresh_character_view(self):
        char = self.current_character()
        self.char_banner.page_title.setText(char.name if char else "No character selected")
        if not char:
            self.charinfo.clear()
            self.portrait.clear()
            self.pdf_status.setText("No character sheet selected.")
            return
        self.charinfo.setPlainText(
            f"Ruleset: {char.ruleset}\nRole: {char.role}\nPlayer: {char.player}\n"
            f"Concept: {char.concept}\nClan / Occupation: {char.clan}\nCondition: {char.condition}"
        )
        if char.portrait and Path(char.portrait).is_file():
            self.portrait.setPixmap(QPixmap(char.portrait))
        else:
            self.portrait.clear()
        try:
            pdf = self.store.char_pdf(char)
            self.pdf_status.setText(
                f"Stored character PDF:\n{pdf}\n"
                f"Size: {pdf.stat().st_size:,} bytes"
            )
        except Exception as exc:
            self.pdf_status.setText(f"PDF unavailable: {exc}")

    def load_planner_fields(self):
        chronicle = self.current_chronicle()
        self.loading = True
        for key, editor in self.plan_fields.items():
            value = chronicle.planner.get(key,"") if chronicle else ""
            if isinstance(editor, QTextEdit): editor.setPlainText(value)
            else: editor.setText(value)
        self.loading = False

    def quick_create(self):
        name = self.new_campaign.text().strip()
        if not name:
            dialog = ChronicleDialog(self)
            if not dialog.exec(): return
            chronicle = Chronicle(id=str(uuid.uuid4()), name=dialog.value("name"))
            for key in dialog.fields:
                setattr(chronicle, key, dialog.value(key))
        else:
            chronicle = Chronicle(id=str(uuid.uuid4()), name=name)
        self.store.put_chronicle(chronicle)
        self.cid = chronicle.id
        self.new_campaign.clear()
        self.refresh_chronicles()

    def edit_chronicle(self):
        chronicle = self.current_chronicle()
        if not chronicle:
            QMessageBox.information(self, APP_NAME, "Create or select a campaign first."); return
        dialog = ChronicleDialog(self, chronicle)
        if dialog.exec():
            for key in dialog.fields:
                setattr(chronicle, key, dialog.value(key))
            self.store.put_chronicle(chronicle)
            self.cid = chronicle.id
            self.refresh_chronicles()

    def delete_chronicle(self):
        chronicle = self.current_chronicle()
        if not chronicle:
            QMessageBox.information(self, APP_NAME, "No campaign is selected."); return
        if QMessageBox.question(self, APP_NAME, f"Delete '{chronicle.name}' and all of its characters?") == QMessageBox.Yes:
            self.store.delete_chronicle(chronicle.id)
            self.cid = ""; self.charid = ""; self.refresh_chronicles()

    def clone_chronicle(self):
        source_id = self.clone_source.currentData()
        source = next((c for c in self.store.chronicles() if c.id == source_id), None)
        if not source:
            QMessageBox.information(self, APP_NAME, "There is no campaign to clone.")
            return
        data = asdict(source)
        data["id"] = str(uuid.uuid4())
        data["name"] = source.name + " Copy"
        clone = Chronicle(**data)
        self.store.put_chronicle(clone)

        old_to_new = {}
        for char in self.store.characters(source.id):
            char_data = asdict(char)
            new_id = str(uuid.uuid4())
            old_to_new[char.id] = new_id
            char_data["id"] = new_id
            char_data["chronicle_id"] = clone.id
            cloned = Character(**char_data)
            if char.portrait and Path(char.portrait).is_file():
                cloned.portrait = self.store.copy_portrait(char.portrait, new_id)
            self.store.put_character(cloned)
            self.store.clone_character_files(char.id, new_id)

        # Clone private/campaign maps with remapped character IDs.
        source_maps = self.store.db.get("maps", {}).get(source.id, {})
        cloned_maps = json.loads(json.dumps(source_maps))
        serialized = json.dumps(cloned_maps)
        for old_id, new_id in old_to_new.items():
            serialized = serialized.replace(old_id, new_id)
        self.store.db.setdefault("maps", {})[clone.id] = json.loads(serialized)

        self.store.save()
        self.cid = clone.id
        self.refresh_chronicles()

    def add_character(self):
        if not self.current_chronicle():
            QMessageBox.information(self, APP_NAME, "Create or select a campaign first.")
            return
        dialog = CharacterDialog(self)
        if dialog.exec():
            char_id = str(uuid.uuid4())
            portrait = self.store.copy_portrait(dialog.fields["portrait"].text(), char_id)
            char = Character(
                id=char_id,
                chronicle_id=self.cid,
                name=dialog.fields["name"].text().strip(),
                ruleset=dialog.ruleset.currentText(),
                role=dialog.role.currentText(),
                player=dialog.fields["player"].text(),
                concept=dialog.fields["concept"].text(),
                clan=dialog.fields["clan"].text(),
                condition=dialog.condition.currentText(),
                portrait=portrait
            )
            self.store.put_character(char)
            try:
                self.store.char_pdf(char)
            except Exception as exc:
                QMessageBox.critical(self, APP_NAME, f"Character created, but the default PDF could not be copied:\n{exc}")
            self.charid = char.id
            self.refresh_characters()
            self.select_character_in_list(char.id)
            self.refresh_character_view()

    def edit_character(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first.")
            return
        dialog = CharacterDialog(self, char)
        if dialog.exec():
            old_ruleset = char.ruleset
            for key in ("name","player","concept","clan"):
                setattr(char, key, dialog.fields[key].text())
            selected_portrait = dialog.fields["portrait"].text()
            if selected_portrait and selected_portrait != char.portrait:
                char.portrait = self.store.copy_portrait(selected_portrait, char.id)
            char.ruleset = dialog.ruleset.currentText()
            char.role = dialog.role.currentText()
            char.condition = dialog.condition.currentText()
            self.store.put_character(char)
            if old_ruleset != char.ruleset:
                answer = QMessageBox.question(
                    self, APP_NAME,
                    "The ruleset changed. Reset this character's PDF to the new ruleset default?"
                )
                if answer == QMessageBox.Yes:
                    self.store.reset_pdf(char)
            self.charid = char.id
            self.refresh_characters()
            self.select_character_in_list(char.id)
            self.refresh_character_view()
            self.relationship_map.load_current()

    def delete_character(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        if QMessageBox.question(self, APP_NAME, f"Delete '{char.name}'?") == QMessageBox.Yes:
            self.store.delete_character(char.id)
            self.charid = ""
            self.refresh_characters()
            self.refresh_character_view()

    def clone_character(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first.")
            return
        clone_id = str(uuid.uuid4())
        data = asdict(char)
        data["id"] = clone_id
        data["name"] = char.name + " Copy"
        clone = Character(**data)
        if char.portrait and Path(char.portrait).is_file():
            clone.portrait = self.store.copy_portrait(char.portrait, clone_id)
        self.store.put_character(clone)
        self.store.clone_character_files(char.id, clone_id)
        self.charid = clone_id
        self.refresh_characters()
        self.select_character_in_list(clone_id)
        self.refresh_character_view()

    def open_char_pdf_external(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first.")
            return
        try:
            os.startfile(str(self.store.char_pdf(char)))
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def export_char_pdf(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first.")
            return
        try:
            source = self.store.char_pdf(char)
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Character PDF", f"{char.name}.pdf", "PDF (*.pdf)"
            )
            if path:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                shutil.copy2(source, path)
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def open_sheet(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        try:
            window = PdfWindow(self.store, char, self)
            self.pdfwins.append(window)
            window.show()
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not open the PDF:\n{exc}")

    def import_char_pdf(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        path, _ = QFileDialog.getOpenFileName(self, "Import PDF", "", "PDF (*.pdf)")
        if path:
            try:
                self.store.replace_pdf(char, path)
                self.refresh_character_view()
            except Exception as exc:
                QMessageBox.critical(self, APP_NAME, str(exc))

    def reset_char_pdf(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        if QMessageBox.question(self, APP_NAME, "Reset this character to the untouched default PDF?") == QMessageBox.Yes:
            try:
                self.store.reset_pdf(char)
                self.refresh_character_view()
            except Exception as exc:
                QMessageBox.critical(self, APP_NAME, str(exc))

    def load_map(self):
        self.relationship_map.load_current()

    def link_selected(self):
        self.relationship_map.edit_selected_relationship()

    def save_map(self):
        self.relationship_map.save_current()

    def refresh_assets(self):
        rows = [x for x in self.store.db["assets"] if x.get("chronicle_id") == self.cid]
        self.asset_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, key in enumerate(("name","type","path")):
                self.asset_table.setItem(row_index, column, QTableWidgetItem(str(row.get(key,""))))
            self.asset_table.item(row_index,0).setData(Qt.UserRole,row.get("id"))

    def add_asset(self):
        if not self.current_chronicle():
            QMessageBox.information(self, APP_NAME, "Create or select a campaign first.")
            return
        source, _ = QFileDialog.getOpenFileName(self, "Choose Asset")
        if not source:
            return
        asset_id = str(uuid.uuid4())
        try:
            stored = self.store.copy_asset(source, asset_id)
            self.store.db["assets"].append({
                "id": asset_id,
                "chronicle_id": self.cid,
                "name": Path(source).name,
                "type": Path(source).suffix.lower(),
                "path": stored
            })
            self.store.save()
            self.refresh_assets()
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def open_asset(self):
        row = self.asset_table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "Select an asset first.")
            return
        path = self.asset_table.item(row,2).text()
        if Path(path).exists():
            os.startfile(path)
        else:
            QMessageBox.warning(self, APP_NAME, "The stored asset file is missing.")

    def delete_asset(self):
        row = self.asset_table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "Select an asset first.")
            return
        asset_id = self.asset_table.item(row,0).data(Qt.UserRole)
        asset = next((x for x in self.store.db["assets"] if x.get("id") == asset_id), None)
        if asset and asset.get("path"):
            Path(asset["path"]).unlink(missing_ok=True)
        self.store.db["assets"] = [x for x in self.store.db["assets"] if x.get("id") != asset_id]
        self.store.save()
        self.refresh_assets()

    def fill_manager_table(self, table, rows, keys):
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, key in enumerate(keys):
                table.setItem(r, c, QTableWidgetItem(str(row.get(key,""))))
            table.item(r,0).setData(Qt.UserRole,row.get("id"))

    def refresh_managers(self):
        if not hasattr(self, "clue_table"):
            return
        clues = [x for x in self.store.db.get("clues",[]) if x.get("chronicle_id") == self.cid]
        touchstones = [x for x in self.store.db.get("touchstones",[]) if x.get("chronicle_id") == self.cid]
        history = [x for x in self.store.db.get("history",[]) if x.get("chronicle_id") == self.cid]
        self.fill_manager_table(self.clue_table, clues, ["title","notes","found_by"])
        self.fill_manager_table(self.touchstone_table, touchstones, ["name","character","connection","notes"])
        self.fill_manager_table(self.history_table, history, ["investigator","era","connection","history"])

    def edit_record_dialog(self, title, labels, existing=None):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(650, 420)
        form = QFormLayout(dialog)
        editors = {}
        existing = existing or {}
        for key, label, multiline in labels:
            editor = QTextEdit() if multiline else QLineEdit()
            if multiline:
                editor.setMinimumHeight(100)
                editor.setPlainText(str(existing.get(key,"")))
            else:
                editor.setText(str(existing.get(key,"")))
            editors[key] = editor
            form.addRow(label, editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if not dialog.exec():
            return None
        return {
            key: editor.toPlainText() if isinstance(editor,QTextEdit) else editor.text()
            for key, editor in editors.items()
        }

    def selected_record(self, table, collection):
        row = table.currentRow()
        if row < 0:
            return None
        record_id = table.item(row,0).data(Qt.UserRole)
        return next((x for x in self.store.db[collection] if x.get("id") == record_id), None)

    def add_record(self, collection, title, labels):
        if not self.current_chronicle():
            QMessageBox.information(self, APP_NAME, "Create or select a campaign first.")
            return
        values = self.edit_record_dialog(title, labels)
        if values is None:
            return
        values.update({"id":str(uuid.uuid4()), "chronicle_id":self.cid})
        self.store.db[collection].append(values)
        self.store.save()
        self.refresh_managers()

    def edit_record(self, table, collection, title, labels):
        record = self.selected_record(table, collection)
        if not record:
            QMessageBox.information(self, APP_NAME, "Select an entry first.")
            return
        values = self.edit_record_dialog(title, labels, record)
        if values is None:
            return
        record.update(values)
        self.store.save()
        self.refresh_managers()

    def delete_record(self, table, collection):
        record = self.selected_record(table, collection)
        if not record:
            QMessageBox.information(self, APP_NAME, "Select an entry first.")
            return
        self.store.db[collection] = [x for x in self.store.db[collection] if x.get("id") != record.get("id")]
        self.store.save()
        self.refresh_managers()

    def add_clue(self):
        self.add_record("clues","Add Clue",[("title","Title",False),("notes","Notes",True),("found_by","Found By",False)])
    def edit_clue(self):
        self.edit_record(self.clue_table,"clues","Edit Clue",[("title","Title",False),("notes","Notes",True),("found_by","Found By",False)])
    def delete_clue(self):
        self.delete_record(self.clue_table,"clues")

    def add_touchstone(self):
        self.add_record("touchstones","Add Touchstone",[("name","Name",False),("character","Character",False),("connection","Connection",False),("notes","Notes",True)])
    def edit_touchstone(self):
        self.edit_record(self.touchstone_table,"touchstones","Edit Touchstone",[("name","Name",False),("character","Character",False),("connection","Connection",False),("notes","Notes",True)])
    def delete_touchstone(self):
        self.delete_record(self.touchstone_table,"touchstones")

    def add_history(self):
        self.add_record("history","Add Investigator History",[("investigator","Investigator",False),("era","Era",False),("connection","Connection",False),("history","History",True)])
    def edit_history(self):
        self.edit_record(self.history_table,"history","Edit Investigator History",[("investigator","Investigator",False),("era","Era",False),("connection","Connection",False),("history","History",True)])
    def delete_history(self):
        self.delete_record(self.history_table,"history")

    def export_full_backup(self):
        self.persist_current()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Full Archive", "NocturneArchive-Backup.zip", "ZIP (*.zip)"
        )
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            self.store.full_backup(Path(path))
            QMessageBox.information(self, APP_NAME, "Full archive backup created.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def import_full_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore Full Archive", "", "ZIP (*.zip)")
        if not path:
            return
        if QMessageBox.question(
            self, APP_NAME,
            "Restoring replaces all current campaigns, characters, PDFs, portraits, maps, and assets. Continue?"
        ) != QMessageBox.Yes:
            return
        try:
            self.store.restore_backup(Path(path))
            self.cid = ""
            self.charid = ""
            self.refresh_chronicles()
            self.relationship_map.load_current()
            QMessageBox.information(self, APP_NAME, "Archive restored.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def export_data(self):
        self.persist_current()
        path, _ = QFileDialog.getSaveFileName(self, "Export Archive", "NocturneArchive.json", "JSON (*.json)")
        if path:
            if not path.lower().endswith(".json"): path += ".json"
            shutil.copy2(self.store.db_file, path)

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Archive", "", "JSON (*.json)")
        if not path: return
        try:
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(loaded, dict): raise ValueError
            blank = self.store.blank()
            for key in blank:
                if key in loaded: blank[key] = loaded[key]
            self.store.db = blank
            self.store.save()
            self.cid = ""; self.charid = ""
            self.refresh_chronicles()
        except Exception:
            QMessageBox.warning(self, APP_NAME, "Invalid archive file.")

    def closeEvent(self, event):
        self.persist_current()
        if self.cid: self.relationship_map.save_current()
        self.store.save()
        super().closeEvent(event)

def main():
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS","--disable-features=Vulkan --use-angle=d3d11")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(bundle_root() / "assets" / "NocturneArchive-V.ico")))
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
