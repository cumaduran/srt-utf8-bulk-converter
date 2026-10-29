"""Modern Qt Widgets desktop interface for SRT UTF-8 Studio."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from threading import Event

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QRadioButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHeaderView, QAbstractItemView, QScrollArea,
)

from srtstudio import __version__
from srtstudio.core import Job, Options, Result, build_plan, convert_one


BASE = Path(__file__).resolve().parent.parent


STYLE = """
QWidget { color: #E9EEFA; font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }
QWidget#Background { background-color: #0B1020; }
QScrollArea { background: #0B1020; border: none; }
QFrame#Panel { background: #141C30; border: 1px solid #28314A; border-radius: 16px; }
QFrame#Hero { border-radius: 18px; border: 1px solid #5C52C4;
 background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #29265F,stop:0.55 #25275B,stop:1 #1A395A); }
QFrame#DropArea { background: #111A2E; border: 2px dashed #52618B; border-radius: 13px; }
QFrame#DropArea[active="true"] { background: #25284E; border: 2px dashed #A99BFF; }
QLabel#Title { color: #FFFFFF; font-size: 26px; font-weight: 800; }
QLabel#HeroTitle { color: #FFFFFF; font-size: 22px; font-weight: 750; }
QLabel#Section { color: #F6F8FF; font-size: 17px; font-weight: 750; }
QLabel#Muted { color: #9AA9C9; }
QLabel#Small { color: #AAB8D4; font-size: 12px; }
QLabel#Badge { color: #C6C4FF; background: #302B69; border: 1px solid #544AA5; border-radius: 10px; padding: 4px 9px; }
QPushButton { background: #26334F; color: #EDF2FF; border: 1px solid #3A4A6B;
 border-radius: 9px; padding: 10px 13px; font-weight: 650; }
QPushButton:hover { background: #334567; border-color: #64769C; }
QPushButton:pressed { background: #1C2942; }
QPushButton:disabled { background: #1C2738; color: #64718A; border-color: #29354A; }
QPushButton#Primary { background: #7C63EE; color: white; border: 1px solid #9983FF; font-size: 14px; padding: 13px 16px; }
QPushButton#Primary:hover { background: #947FF7; }
QPushButton#Primary:disabled { background: #3D3C66; color: #8C8BAB; border-color: #3D3C66; }
QPushButton#Danger { background: #513040; border-color: #895267; }
QPushButton#Danger:hover { background: #714253; }
QLineEdit { background: #10182B; color: #EEF2FC; border: 1px solid #384560;
 border-radius: 9px; padding: 10px 12px; selection-background-color: #7765D8; }
QLineEdit:focus { border: 1px solid #A28EFF; }
QLineEdit:disabled { color: #72809B; border: 1px solid #29354A; }
QCheckBox, QRadioButton { color: #D5DEEF; spacing: 9px; padding: 4px 2px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QTableWidget { background: #11192A; color: #DCE5F6; border: 1px solid #29354E;
 border-radius: 10px; gridline-color: #25324A; alternate-background-color: #151E32;
 selection-background-color: #37355F; selection-color: white; }
QHeaderView::section { background: #1C2840; border: none; border-right: 1px solid #2C3B59;
 color: #AEBEE0; padding: 10px 9px; font-weight: 650; }
QTableWidget::item { padding: 8px; }
QPlainTextEdit { background: #0F1729; color: #AEBDE0; border: 1px solid #2B3753;
 border-radius: 10px; padding: 9px; font-family: 'Cascadia Code', Consolas, monospace; font-size: 12px; }
QProgressBar { background: #26314C; border: none; border-radius: 6px; min-height: 11px;
 text-align: center; color: transparent; }
QProgressBar::chunk { border-radius: 6px; background: #8C7BFF; }
QToolTip { color: #FFFFFF; background: #262D45; border: 1px solid #6772A1; }
"""


def label(text: str, kind: str = 'Muted', word_wrap: bool = False) -> QLabel:
    item = QLabel(text)
    item.setObjectName(kind)
    item.setWordWrap(word_wrap)
    return item


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName('Panel')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(21, 20, 21, 20)
    layout.setSpacing(13)
    return frame, layout


class DropArea(QFrame):
    paths_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName('DropArea')
        self.setAcceptDrops(True)
        self.setProperty('active', False)
        self.setMinimumHeight(98)
        stack = QVBoxLayout(self)
        stack.setSpacing(4)
        stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = label('＋   SRT dosyalarını veya klasörleri buraya sürükle', 'Section')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.addWidget(title)
        detail = label('Tek dosya, çoklu dosya ve klasör desteklenir.', 'Small')
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.addWidget(detail)

    def _set_active(self, active: bool):
        self.setProperty('active', active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._set_active(False)
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()


class ConversionThread(QThread):
    progress = Signal(object, int, int)
    completed = Signal(object, bool)

    def __init__(self, jobs: list[Job], overwrite: bool):
        super().__init__()
        self.jobs = jobs
        self.overwrite = overwrite
        self.cancelled = Event()

    def run(self):
        output = []
        for number, job in enumerate(self.jobs, 1):
            if self.cancelled.is_set():
                break
            result = convert_one(job, overwrite=self.overwrite)
            output.append(result)
            self.progress.emit(result, number, len(self.jobs))
        self.completed.emit(output, self.cancelled.is_set())

    def request_cancel(self):
        self.cancelled.set()


class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sources: list[Path] = []
        self.hidden_files: set[Path] = set()
        self.jobs: list[Job] = []
        self.row_by_path: dict[Path, int] = {}
        self.worker: ConversionThread | None = None
        self.running = False
        self.last_output_path: Path | None = None

        self.setWindowTitle('SRT UTF-8 Studio')
        self.resize(1260, 870)
        self.setMinimumSize(960, 700)
        icon = BASE / 'assets' / 'app.ico'
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        background = QWidget()
        background.setObjectName('Background')
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(background)
        self.setCentralWidget(scroll)
        root = QVBoxLayout(background)
        root.setContentsMargins(27, 21, 27, 20)
        root.setSpacing(18)

        self._build_header(root)
        self._build_hero(root)
        body = QHBoxLayout()
        body.setSpacing(18)
        root.addLayout(body, 1)
        self._build_sources(body)
        self._build_options(body)
        self._build_footer(root)
        self._refresh_plan()

    def _build_header(self, parent):
        bar = QHBoxLayout()
        bar.setSpacing(13)
        logo = QLabel()
        logo.setFixedSize(48, 48)
        img = QPixmap(str(BASE / 'assets' / 'app.png'))
        if not img.isNull():
            logo.setPixmap(img.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation))
        bar.addWidget(logo)
        heading = QVBoxLayout()
        heading.setSpacing(0)
        heading.addWidget(label('SRT UTF-8 Studio', 'Title'))
        heading.addWidget(label('Modern altyazı kodlama dönüştürücü', 'Small'))
        bar.addLayout(heading)
        bar.addStretch()
        bar.addWidget(label('Windows • SRT • UTF-8', 'Badge'))
        about = QLabel('<a href="https://github.com/cumaduran" style="color:#A99BFF;text-decoration:none;">@cumaduran ↗</a>')
        about.setOpenExternalLinks(True)
        bar.addWidget(about)
        parent.addLayout(bar)

    def _build_hero(self, parent):
        hero = QFrame()
        hero.setObjectName('Hero')
        outer = QHBoxLayout(hero)
        outer.setContentsMargins(24, 18, 24, 18)
        texts = QVBoxLayout()
        texts.setSpacing(6)
        texts.addWidget(label('Altyazıların, doğru karakterlerle.', 'HeroTitle'))
        texts.addWidget(label('Windows-1254 ve UTF-8 dosyalarını güvenle UTF-8 BOM’suz biçimine dönüştür.', 'Small'))
        outer.addLayout(texts, 1)
        self.summary_pill = label('0 dosya hazır', 'Badge')
        outer.addWidget(self.summary_pill)
        parent.addWidget(hero)

    def _build_sources(self, parent):
        panel, col = card()
        parent.addWidget(panel, 7)
        heading = QHBoxLayout()
        heading.addWidget(label('01   Kaynak altyazılar', 'Section'))
        heading.addStretch()
        self.btn_clear = QPushButton('Temizle')
        self.btn_clear.clicked.connect(self._clear_sources)
        heading.addWidget(self.btn_clear)
        col.addLayout(heading)
        zone = DropArea()
        zone.paths_dropped.connect(self._add_sources)
        col.addWidget(zone)

        actions = QHBoxLayout()
        self.btn_add_files = QPushButton('＋  Dosya seç')
        self.btn_add_files.clicked.connect(self._select_files)
        actions.addWidget(self.btn_add_files)
        self.btn_add_dir = QPushButton('▣  Klasör seç')
        self.btn_add_dir.clicked.connect(self._select_folder)
        actions.addWidget(self.btn_add_dir)
        actions.addStretch()
        self.selected_label = label('Henüz kaynak seçilmedi', 'Small')
        actions.addWidget(self.selected_label)
        col.addLayout(actions)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Dosya', 'Konum', 'Kodlama', 'Durum'])
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(255)
        col.addWidget(self.table, 1)
        self.btn_remove = QPushButton('Seçili dosyaları çıkar')
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_remove.setToolTip('Seçili altyazıları işlem listesinden kaldırır.')
        col.addWidget(self.btn_remove)

    def _build_options(self, parent):
        panel, col = card()
        panel.setMaximumWidth(368)
        parent.addWidget(panel, 4)
        col.addWidget(label('02   Çıktı ve ayarlar', 'Section'))
        col.addWidget(label('Çıktı konumu', 'Small'))
        self.radio_auto = QRadioButton('Kaynak yanında /utf8 klasörü')
        self.radio_auto.setChecked(True)
        self.radio_auto.toggled.connect(self._update_output_mode)
        col.addWidget(self.radio_auto)
        self.radio_custom = QRadioButton('Özel çıktı klasörü')
        col.addWidget(self.radio_custom)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText('Çıktı klasörünü seç...')
        self.output_edit.textChanged.connect(self._refresh_plan)
        col.addWidget(self.output_edit)
        self.btn_output = QPushButton('Klasör seç…')
        self.btn_output.clicked.connect(self._browse_output)
        col.addWidget(self.btn_output)
        self._update_output_mode()

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet('background: #2B3753; border: none;')
        col.addWidget(line)
        col.addWidget(label('İşlem seçenekleri', 'Small'))
        self.cb_recursive = QCheckBox('Alt klasörleri de tara')
        self.cb_recursive.setChecked(True)
        self.cb_recursive.toggled.connect(self._refresh_plan)
        col.addWidget(self.cb_recursive)
        self.cb_structure = QCheckBox('Alt klasör yapısını koru')
        self.cb_structure.setChecked(True)
        self.cb_structure.toggled.connect(self._refresh_plan)
        col.addWidget(self.cb_structure)
        self.cb_overwrite = QCheckBox('Mevcut çıktıların üzerine yaz')
        self.cb_overwrite.setToolTip('Kapalıyken zaten var olan çıktı dosyaları atlanır.')
        col.addWidget(self.cb_overwrite)

        info = label('KODLAMA  •  Otomatik UTF-8 kontrolü → Windows-1254 → UTF-8 (BOM yok)', 'Small', True)
        info.setStyleSheet('color:#BBB6FF; background:#262449; padding:12px; border-radius:10px;')
        col.addWidget(info)
        col.addStretch()
        self.btn_convert = QPushButton('⚡   Dönüştürmeyi başlat')
        self.btn_convert.setObjectName('Primary')
        self.btn_convert.clicked.connect(self._start)
        col.addWidget(self.btn_convert)
        self.btn_cancel = QPushButton('İptal et')
        self.btn_cancel.setObjectName('Danger')
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        col.addWidget(self.btn_cancel)

    def _build_footer(self, parent):
        panel, col = card()
        col.setSpacing(9)
        head = QHBoxLayout()
        head.addWidget(label('03   İşlem durumu', 'Section'))
        head.addStretch()
        self.status_label = label('Başlamak için bir klasör veya SRT dosyası seç.', 'Small')
        head.addWidget(self.status_label)
        col.addLayout(head)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        col.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        self.log.setMinimumHeight(78)
        self.log.setMaximumHeight(118)
        col.addWidget(self.log)
        foot = QHBoxLayout()
        foot.addWidget(label(f'v{__version__}  •  © 2026 cumaduran  •  Orijinal dosyalar korunur', 'Small'))
        foot.addStretch()
        self.btn_open = QPushButton('Çıktı klasörünü aç ↗')
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._open_output)
        foot.addWidget(self.btn_open)
        col.addLayout(foot)
        parent.addWidget(panel)

    def _log(self, message: str):
        self.log.appendPlainText(message)

    def _add_sources(self, paths):
        if self.running:
            return
        before = set(self.sources)
        for raw in paths:
            path = Path(raw).expanduser().resolve()
            if path in before:
                continue
            if path.is_dir() or (path.is_file() and path.suffix.casefold() == '.srt'):
                self.sources.append(path)
                before.add(path)
                if path.is_file():
                    self.hidden_files.discard(path)
        self._refresh_plan()

    def _select_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'SRT dosyalarını seç', '', 'SRT Altyazıları (*.srt *.SRT)')
        if paths:
            self._add_sources(paths)

    def _select_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Altyazı klasörünü seç')
        if path:
            self._add_sources([path])

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, 'Çıktı klasörünü seç', self.output_edit.text())
        if path:
            self.radio_custom.setChecked(True)
            self.output_edit.setText(path)

    def _update_output_mode(self):
        use_custom = self.radio_custom.isChecked()
        self.output_edit.setEnabled(use_custom)
        self.btn_output.setEnabled(use_custom)
        self._refresh_plan()

    def _options(self):
        custom = None
        if self.radio_custom.isChecked() and self.output_edit.text().strip():
            custom = Path(self.output_edit.text().strip())
        return Options(tuple(self.sources), custom, self.cb_recursive.isChecked(),
                       self.cb_structure.isChecked(), self.cb_overwrite.isChecked())

    def _refresh_plan(self):
        if (self.running or not hasattr(self, 'table') or not hasattr(self, 'radio_custom')
                or not hasattr(self, 'cb_recursive') or not hasattr(self, 'btn_convert')
                or not hasattr(self, 'progress')):
            return
        self.jobs = [job for job in build_plan(self._options())
                     if job.source not in self.hidden_files]
        self.row_by_path.clear()
        self.table.setRowCount(len(self.jobs))
        for index, job in enumerate(self.jobs):
            self.row_by_path[job.source] = index
            items = [job.source.name, str(job.source.parent), '—',
                     'Çakışma' if job.conflict else 'Hazır']
            for column, text in enumerate(items):
                cell = QTableWidgetItem(text)
                if column == 0:
                    cell.setToolTip(str(job.source))
                if column == 3 and job.conflict:
                    cell.setForeground(QColor('#F6BB71'))
                    cell.setToolTip(job.conflict)
                self.table.setItem(index, column, cell)
        self.selected_label.setText(f'{len(self.sources)} kaynak')
        self.summary_pill.setText(f'{len(self.jobs)} dosya hazır')
        self.btn_convert.setEnabled(bool(self.jobs))
        self.progress.setValue(0)

    def _remove_selected(self):
        if self.running:
            return
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        files = {self.jobs[i].source for i in rows if i < len(self.jobs)}
        if not files:
            return
        self.hidden_files.update(files)
        self.sources = [path for path in self.sources if not (path.is_file() and path in files)]
        self._refresh_plan()

    def _clear_sources(self):
        if self.running:
            return
        self.sources.clear()
        self.hidden_files.clear()
        self._refresh_plan()
        self.log.clear()

    def _set_running(self, running: bool):
        self.running = running
        for item in (self.btn_add_files, self.btn_add_dir, self.btn_clear,
                     self.btn_remove, self.radio_auto, self.radio_custom,
                     self.cb_recursive, self.cb_structure, self.cb_overwrite):
            item.setEnabled(not running)
        self.output_edit.setEnabled(not running and self.radio_custom.isChecked())
        self.btn_output.setEnabled(not running and self.radio_custom.isChecked())
        self.btn_convert.setEnabled(not running and bool(self.jobs))
        self.btn_cancel.setEnabled(running)

    def _start(self):
        if self.running or not self.jobs:
            return
        if self.radio_custom.isChecked() and not self.output_edit.text().strip():
            QMessageBox.warning(self, 'Çıktı klasörü gerekli', 'Özel çıktı klasörü seçmelisin.')
            return
        self._set_running(True)
        self.last_output_path = None
        self.btn_open.setEnabled(False)
        self.progress.setValue(0)
        self.log.clear()
        self._log(f'▶ {len(self.jobs)} SRT dosyası işleme alındı.')
        self.status_label.setText('Dönüştürülüyor…')
        self.worker = ConversionThread(self.jobs[:], self.cb_overwrite.isChecked())
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_complete)
        self.worker.finished.connect(self._thread_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_progress(self, result: Result, processed: int, total: int):
        display = {'done': 'Tamamlandı', 'warning': 'Uyarı',
                   'skipped': 'Atlandı', 'failed': 'Hata'}[result.status]
        color = {'done': '#8CE0B7', 'warning': '#F4C57A',
                 'skipped': '#9DB1D4', 'failed': '#FF929C'}[result.status]
        index = self.row_by_path.get(result.source)
        if index is not None:
            enc = self.table.item(index, 2)
            state = self.table.item(index, 3)
            if enc:
                enc.setText(result.encoding)
            if state:
                state.setText(display)
                state.setToolTip(result.message)
                state.setForeground(QColor(color))
        self.progress.setValue(round(processed / total * 100))
        self.status_label.setText(f'{processed} / {total} işleniyor')
        self._log(f'[{display}] {result.source.name} — {result.message}')
        if result.status in ('done', 'warning'):
            self.last_output_path = self.last_output_path or result.destination.parent
            self.btn_open.setEnabled(True)

    def _on_complete(self, results, cancelled: bool):
        counts = Counter(result.status for result in results)
        summary = (f'{counts["done"]} başarılı · {counts["warning"]} uyarı · '
                   f'{counts["skipped"]} atlandı · {counts["failed"]} hata')
        if cancelled:
            summary = 'İptal edildi · ' + summary
        self._log('─────────────────────────────────────────')
        self._log('✓ İşlem bitti: ' + summary)
        self.status_label.setText(summary)
        self.summary_pill.setText(f'{len(results)} / {len(self.jobs)} işlendi')
        self._set_running(False)
    def _thread_finished(self):
        self.worker = None

    def _cancel(self):
        if self.worker and self.running:
            self.worker.request_cancel()
            self.status_label.setText('İptal isteniyor…')

    def _open_output(self):
        if self.last_output_path and self.last_output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output_path)))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait()
        super().closeEvent(event)


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('SRT UTF-8 Studio')
    app.setApplicationDisplayName('SRT UTF-8 Studio')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    app.setFont(QFont('Segoe UI', 10))
    window = Studio()
    window.show()
    return app.exec()
