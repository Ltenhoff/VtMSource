
from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QBrush, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QFrame, QFormLayout, QDialog, QDialogButtonBox,
    QFileDialog, QMessageBox, QSplitter, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar, QGroupBox
)
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineSettings, QWebEngineDownloadRequest
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
        self.sheets.mkdir(parents=True, exist_ok=True)
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
        self.save()

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
        self.setWindowTitle(f"{char.name} — PDF Sheet")
        self.resize(1250, 900)
        self.profile = QWebEngineProfile(f"sheet-{char.id}", self)
        self.profile.setPersistentStoragePath(str(data_root() / "PdfProfiles" / char.id))
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.profile.downloadRequested.connect(self.download)
        self.view = QWebEngineView()
        self.view.setPage(self.profile.newPage())
        self.setCentralWidget(self.view)
        toolbar = QToolBar("PDF")
        for title, callback in [
            ("Reload", self.reload), ("Import PDF", self.import_pdf), ("Reset PDF", self.reset),
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

class NodeItem(QGraphicsEllipseItem):
    def __init__(self, char_id, name, x, y):
        super().__init__(-48, -48, 96, 96)
        self.char_id = char_id
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#18241e")))
        self.setPen(QPen(QColor("#a48c67"), 2))
        self.setFlags(
            QGraphicsEllipseItem.ItemIsMovable |
            QGraphicsEllipseItem.ItemIsSelectable |
            QGraphicsEllipseItem.ItemSendsGeometryChanges
        )
        text = QGraphicsTextItem(name, self)
        text.setDefaultTextColor(QColor("#f1e6cf"))
        text.setTextWidth(86)
        text.setPos(-43, -12)

class MapView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.nodes = {}
        self.edges = []

    def load_map(self, chars, data):
        self.scene().clear()
        self.nodes = {}
        self.edges = list(data.get("edges", []))
        positions = data.get("nodes", {})
        for i, char in enumerate(chars):
            pos = positions.get(char.id, {"x": 150 + (i % 5) * 180, "y": 120 + (i // 5) * 160})
            node = NodeItem(char.id, char.name, pos["x"], pos["y"])
            self.scene().addItem(node)
            self.nodes[char.id] = node
        self.redraw_edges()

    def redraw_edges(self):
        for edge in self.edges:
            a = self.nodes.get(edge.get("a")); b = self.nodes.get(edge.get("b"))
            if a and b:
                line = QGraphicsLineItem(a.x(), a.y(), b.x(), b.y())
                line.setPen(QPen(QColor("#b58a54"), 2))
                line.setZValue(-1)
                self.scene().addItem(line)

    def snapshot(self):
        return {
            "nodes": {key: {"x": node.x(), "y": node.y()} for key, node in self.nodes.items()},
            "edges": self.edges
        }

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
        for index, text in enumerate(["Campaign Planner","Chronicle","Relationship Map","Character","Assets","Tools"]):
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
        self.charlist = QListWidget()
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
        page = QWidget(); layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        for title, callback in [("Load Chronicle Characters",self.load_map),("Link Selected",self.link_selected),("Save Map",self.save_map)]:
            button = QPushButton(title); button.clicked.connect(callback); bar.addWidget(button)
        bar.addStretch(); layout.addLayout(bar)
        self.mapview = MapView(); layout.addWidget(self.mapview)
        return page

    def character_page(self):
        inner = QWidget(); layout = QVBoxLayout(inner)
        self.char_banner = self.banner("Character","No character selected","Identity, portrait, condition, and native PDF sheet.")
        layout.addWidget(self.char_banner)
        card = QFrame(); card.setObjectName("Card"); grid = QGridLayout(card)
        self.portrait = QLabel(); self.portrait.setFixedSize(420,520); self.portrait.setScaledContents(True)
        grid.addWidget(self.portrait,0,0,6,1)
        self.charinfo = QTextEdit(); self.charinfo.setReadOnly(True); grid.addWidget(self.charinfo,0,1)
        actions = [
            ("Edit Identity",self.edit_character),("Open PDF Window",self.open_sheet),
            ("Import Saved PDF",self.import_char_pdf),("Reset PDF",self.reset_char_pdf),
            ("Delete Character",self.delete_character)
        ]
        for row,(title,callback) in enumerate(actions,1):
            button = QPushButton(title); button.clicked.connect(callback); grid.addWidget(button,row,1)
        layout.addWidget(card); layout.addStretch()
        return self.wrap(inner)

    def assets_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(self.banner("Assets","Campaign Assets","Store references and file paths associated with the selected chronicle."))
        self.asset_table = QTableWidget(0,3)
        self.asset_table.setHorizontalHeaderLabels(["Name","Type","Path"])
        self.asset_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.asset_table)
        row = QHBoxLayout()
        add = QPushButton("Add Asset"); add.clicked.connect(self.add_asset)
        delete = QPushButton("Delete Selected"); delete.clicked.connect(self.delete_asset)
        row.addWidget(add); row.addWidget(delete); row.addStretch(); layout.addLayout(row)
        return page

    def tools_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(self.banner("Tools","Archive Tools","Backup, restore, and local data management."))
        for title, callback in [
            ("Export Full Archive",self.export_data),("Import Full Archive",self.import_data),
            ("Open Data Folder",lambda: os.startfile(str(data_root()))),
            ("Delete Selected Chronicle",self.delete_chronicle)
        ]:
            button = QPushButton(title); button.clicked.connect(callback); layout.addWidget(button)
        layout.addStretch(); return page

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
        if index == 2: self.load_map()

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

    def refresh_character_view(self):
        char = self.current_character()
        self.char_banner.page_title.setText(char.name if char else "No character selected")
        if not char:
            self.charinfo.clear(); self.portrait.clear(); return
        self.charinfo.setPlainText(
            f"Ruleset: {char.ruleset}\nRole: {char.role}\nPlayer: {char.player}\n"
            f"Concept: {char.concept}\nClan / Occupation: {char.clan}\nCondition: {char.condition}"
        )
        if char.portrait and Path(char.portrait).is_file():
            self.portrait.setPixmap(QPixmap(char.portrait))
        else:
            self.portrait.clear()

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
            QMessageBox.information(self, APP_NAME, "There is no campaign to clone."); return
        data = asdict(source); data["id"] = str(uuid.uuid4()); data["name"] = source.name + " Copy"
        clone = Chronicle(**data)
        self.store.put_chronicle(clone)
        for char in self.store.characters(source.id):
            char_data = asdict(char); char_data["id"] = str(uuid.uuid4()); char_data["chronicle_id"] = clone.id
            self.store.put_character(Character(**char_data))
        self.cid = clone.id
        self.refresh_chronicles()

    def add_character(self):
        if not self.current_chronicle():
            QMessageBox.information(self, APP_NAME, "Create or select a campaign first."); return
        dialog = CharacterDialog(self)
        if dialog.exec():
            char = Character(
                id=str(uuid.uuid4()), chronicle_id=self.cid,
                name=dialog.fields["name"].text().strip(),
                ruleset=dialog.ruleset.currentText(), role=dialog.role.currentText(),
                player=dialog.fields["player"].text(), concept=dialog.fields["concept"].text(),
                clan=dialog.fields["clan"].text(), condition=dialog.condition.currentText(),
                portrait=dialog.fields["portrait"].text()
            )
            self.store.put_character(char)
            self.charid = char.id
            self.refresh_characters()
            self.refresh_character_view()

    def edit_character(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        dialog = CharacterDialog(self, char)
        if dialog.exec():
            for key in ("name","player","concept","clan","portrait"):
                setattr(char, key, dialog.fields[key].text())
            char.ruleset = dialog.ruleset.currentText()
            char.role = dialog.role.currentText()
            char.condition = dialog.condition.currentText()
            self.store.put_character(char)
            self.charid = char.id
            self.refresh_characters()
            self.refresh_character_view()

    def delete_character(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        if QMessageBox.question(self, APP_NAME, f"Delete '{char.name}'?") == QMessageBox.Yes:
            self.store.delete_character(char.id)
            self.charid = ""
            self.refresh_characters()
            self.refresh_character_view()

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
            try: self.store.replace_pdf(char, path)
            except Exception as exc: QMessageBox.critical(self, APP_NAME, str(exc))

    def reset_char_pdf(self):
        char = self.current_character()
        if not char:
            QMessageBox.information(self, APP_NAME, "Select a character first."); return
        if QMessageBox.question(self, APP_NAME, "Reset this character to the untouched default PDF?") == QMessageBox.Yes:
            try: self.store.reset_pdf(char)
            except Exception as exc: QMessageBox.critical(self, APP_NAME, str(exc))

    def load_map(self):
        if not self.current_chronicle():
            self.mapview.scene().clear(); return
        data = self.store.db["maps"].setdefault(self.cid, {"nodes":{},"edges":[]})
        self.mapview.load_map(self.store.characters(self.cid), data)

    def link_selected(self):
        selected = [item for item in self.mapview.scene().selectedItems() if isinstance(item, NodeItem)]
        if len(selected) != 2:
            QMessageBox.information(self, APP_NAME, "Select exactly two character nodes."); return
        ids = [item.char_id for item in selected]
        if not any({edge.get("a"),edge.get("b")} == set(ids) for edge in self.mapview.edges):
            self.mapview.edges.append({"a":ids[0],"b":ids[1],"type":"mutual","note":""})
        self.save_map()

    def save_map(self):
        if not self.cid: return
        self.store.db["maps"][self.cid] = self.mapview.snapshot()
        self.store.save()
        self.load_map()

    def refresh_assets(self):
        rows = [x for x in self.store.db["assets"] if x.get("chronicle_id") == self.cid]
        self.asset_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, key in enumerate(("name","type","path")):
                self.asset_table.setItem(row_index,column,QTableWidgetItem(str(row.get(key,""))))
            self.asset_table.item(row_index,0).setData(Qt.UserRole,row.get("id"))

    def add_asset(self):
        if not self.current_chronicle():
            QMessageBox.information(self, APP_NAME, "Create or select a campaign first."); return
        path, _ = QFileDialog.getOpenFileName(self, "Choose Asset")
        if not path: return
        self.store.db["assets"].append({
            "id":str(uuid.uuid4()),"chronicle_id":self.cid,
            "name":Path(path).name,"type":Path(path).suffix.lower(),"path":path
        })
        self.store.save(); self.refresh_assets()

    def delete_asset(self):
        row = self.asset_table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "Select an asset first."); return
        asset_id = self.asset_table.item(row,0).data(Qt.UserRole)
        self.store.db["assets"] = [x for x in self.store.db["assets"] if x.get("id") != asset_id]
        self.store.save(); self.refresh_assets()

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
        if self.cid: self.save_map()
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
