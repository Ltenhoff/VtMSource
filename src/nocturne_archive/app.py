from __future__ import annotations

import os
import shutil
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

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


def ensure_runtime_assets() -> tuple[Path, Path]:
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

    # Refresh application files every launch, but never touch BrowserProfile.
    if target_web.exists():
        shutil.rmtree(target_web)
    if target_assets.exists():
        shutil.rmtree(target_assets)
    shutil.copytree(source_web, target_web)
    shutil.copytree(source_assets, target_assets)
    return target_web / "index.html", profile_dir


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
    def closeEvent(self, event):  # noqa: N802
        # Let the web app's beforeunload/save logic run normally.
        super().closeEvent(event)


def configure_profile(profile_dir: Path) -> QWebEngineProfile:
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
        # Qt displays the native save path selected by the web app/browser.
        if not item.downloadDirectory():
            item.setDownloadDirectory(str(Path.home() / "Downloads"))
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
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-features=msSmartScreenProtection")
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("NocturneArchive")
    icon = bundled_root() / "assets" / "NocturneArchive-V.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    app._nocturne_windows = []  # type: ignore[attr-defined]

    try:
        index_file, profile_dir = ensure_runtime_assets()
        profile = configure_profile(profile_dir)
        window = MainWindow(profile)
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
