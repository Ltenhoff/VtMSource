from __future__ import annotations

import os
import shutil
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from .pdf_store import PdfStore

APP_NAME = "Nocturne Archive"
DATA_DIR_NAME = "NocturneArchive.Data"


def bundled_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def executable_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def ensure_runtime_assets() -> tuple[Path, Path, Path, Path]:
    bundle = bundled_root()
    base = executable_root()
    data_root = base / DATA_DIR_NAME
    runtime = data_root / "RuntimeAssets"
    profile_dir = data_root / "BrowserProfile"
    logs = data_root / "Logs"
    runtime.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    source_web = bundle / "web"
    source_assets = bundle / "assets"
    target_web = runtime / "web"
    target_assets = runtime / "assets"

    if target_web.exists():
        shutil.rmtree(target_web)
    if target_assets.exists():
        shutil.rmtree(target_assets)
    shutil.copytree(source_web, target_web)
    shutil.copytree(source_assets, target_assets)
    return target_web / "index.html", profile_dir, data_root, target_assets


class PdfBridge(QObject):
    sheetChanged = Signal(str, str)
    nativeSaveRequested = Signal()

    def __init__(self, store: PdfStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.active_character_id = ""

    @Slot(str, result=bool)
    def setActiveCharacter(self, character_id: str) -> bool:
        self.active_character_id = str(character_id or "")
        return bool(self.active_character_id)

    @Slot(str, result=bool)
    def requestNativeSave(self, character_id: str) -> bool:
        self.active_character_id = str(character_id or "")
        self.nativeSaveRequested.emit()
        return True

    @Slot(str, str, result=str)
    def ensureCharacterPdf(self, character_id: str, ruleset: str) -> str:
        self.active_character_id = str(character_id or "")
        return QUrl.fromLocalFile(str(self.store.ensure_character_sheet(character_id, ruleset).path)).toString()

    @Slot(str, result=str)
    def importCharacterPdf(self, character_id: str) -> str:
        source, _ = QFileDialog.getOpenFileName(None, "Import PDF", "", "PDF files (*.pdf)")
        if not source:
            return ""
        self.active_character_id = str(character_id or "")
        sheet = self.store.import_pdf(character_id, Path(source))
        url = QUrl.fromLocalFile(str(sheet.path)).toString()
        self.sheetChanged.emit(character_id, url)
        return url

    @Slot(str, str, result=str)
    def saveCharacterPdfBytes(self, character_id: str, pdf_base64: str) -> str:
        sheet = self.store.save_base64(character_id, pdf_base64)
        url = QUrl.fromLocalFile(str(sheet.path)).toString()
        self.sheetChanged.emit(character_id, url)
        return url

    @Slot(str, str, result=bool)
    def exportCharacterPdf(self, character_id: str, suggested_name: str) -> bool:
        destination, _ = QFileDialog.getSaveFileName(
            None,
            "Save Character PDF",
            suggested_name or "character-sheet.pdf",
            "PDF files (*.pdf)",
        )
        if not destination:
            return False
        if not destination.lower().endswith(".pdf"):
            destination += ".pdf"
        self.store.export_pdf(character_id, Path(destination))
        return True

    @Slot(str, str, result=str)
    def resetCharacterPdf(self, character_id: str, ruleset: str) -> str:
        self.active_character_id = str(character_id or "")
        sheet = self.store.reset_pdf(character_id, ruleset)
        url = QUrl.fromLocalFile(str(sheet.path)).toString()
        self.sheetChanged.emit(character_id, url)
        return url


class AppPage(QWebEnginePage):
    def createWindow(self, window_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        popup = BrowserWindow(self.profile(), parent_view=None)
        popup.resize(1100, 850)
        popup.show()
        QApplication.instance()._nocturne_windows.append(popup)  # type: ignore[attr-defined]
        return popup.page()


class BrowserWindow(QWebEngineView):
    def __init__(self, profile: QWebEngineProfile, parent_view: QWebEngineView | None = None):
        super().__init__(parent_view)
        self.setPage(AppPage(profile, self))
        self.setWindowTitle(APP_NAME)
        icon = bundled_root() / "assets" / "NocturneArchive-V.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))


class MainWindow(BrowserWindow):
    @Slot()
    def trigger_pdf_save(self) -> None:
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        QTest.keyClick(self, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)


def configure_profile(profile_dir: Path, store: PdfStore, bridge: PdfBridge) -> QWebEngineProfile:
    profile = QWebEngineProfile("NocturneArchive", QApplication.instance())
    profile.setPersistentStoragePath(str(profile_dir))
    profile.setCachePath(str(profile_dir / "Cache"))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    profile.setDownloadPath(str(Path.home() / "Downloads"))

    settings = profile.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

    def on_download(item: QWebEngineDownloadRequest) -> None:
        suggested = item.downloadFileName() or "character-sheet.pdf"
        destination, _ = QFileDialog.getSaveFileName(None, "Save PDF", suggested, "PDF files (*.pdf)")
        if not destination:
            item.cancel()
            return
        if not destination.lower().endswith(".pdf"):
            destination += ".pdf"
        target = Path(destination)
        item.setDownloadDirectory(str(target.parent))
        item.setDownloadFileName(target.name)

        def completed() -> None:
            if item.state() != QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                return
            character_id = bridge.active_character_id
            if not character_id or not target.is_file():
                return
            try:
                sheet = store.import_pdf(character_id, target)
                bridge.sheetChanged.emit(character_id, QUrl.fromLocalFile(str(sheet.path)).toString())
            except Exception as exc:  # pragma: no cover - surfaced to user
                QMessageBox.warning(None, APP_NAME, f"The PDF was saved locally, but its character copy could not be updated.\n\n{exc}")

        item.stateChanged.connect(completed)
        item.accept()

    profile.downloadRequested.connect(on_download)
    return profile


def write_startup_error(exc: BaseException) -> Path:
    base = executable_root() / DATA_DIR_NAME / "Logs"
    base.mkdir(parents=True, exist_ok=True)
    log = base / "startup.log"
    log.write_text("".join(traceback.format_exception(exc)), encoding="utf-8")
    return log


def main() -> int:
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-features=msSmartScreenProtection,Vulkan --disable-gpu-driver-bug-workarounds --use-angle=d3d11",
    )
    os.environ.setdefault("QT_OPENGL", "angle")

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("NocturneArchive")
    icon = bundled_root() / "assets" / "NocturneArchive-V.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    app._nocturne_windows = []  # type: ignore[attr-defined]

    try:
        index_file, profile_dir, data_root, runtime_assets = ensure_runtime_assets()
        store = PdfStore(data_root, runtime_assets)
        bridge = PdfBridge(store)
        profile = configure_profile(profile_dir, store, bridge)

        window = MainWindow(profile)
        bridge.nativeSaveRequested.connect(window.trigger_pdf_save)
        channel = QWebChannel(window.page())
        channel.registerObject("pdfBridge", bridge)
        window.page().setWebChannel(channel)
        window._pdf_bridge = bridge  # type: ignore[attr-defined]
        window._web_channel = channel  # type: ignore[attr-defined]

        window.resize(1500, 950)
        window.show()
        window.load(QUrl.fromLocalFile(str(index_file)))
        app._nocturne_windows.append(window)  # type: ignore[attr-defined]
        return app.exec()
    except BaseException as exc:
        log = write_startup_error(exc)
        QMessageBox.critical(None, APP_NAME, f"The application could not start.\n\nDetails: {exc}\n\nLog: {log}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
