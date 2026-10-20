from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QProgressBar, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__
from .about import AboutDialog
from .assets import asset_path
from .jobs import ExtractionWorker
from .metadata import PackageError, read_package
from .native_theme import install_native_theme
from .theme import STYLE
from .updates import UpdateChecker


def label(text, name="", wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 14, 18, 14)
        layout.addWidget(label("↓", "DropIcon"))
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(label("Drop PKG files", "DropTitle"))
        text.addWidget(label("Games · Updates · DLC", "Hint"))
        layout.addLayout(text, 1)
        self.add_button = QPushButton("Add files…")
        self.add_button.setAccessibleName("Add PKG files")
        layout.addWidget(self.add_button)

    def highlight(self, active):
        self.setProperty("dragging", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if self.isEnabled() and event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.highlight(True)

    def dragLeaveEvent(self, event):
        self.highlight(False)

    def dropEvent(self, event):
        self.highlight(False)
        if self.isEnabled():
            self.files_dropped.emit([Path(url.toLocalFile()) for url in event.mimeData().urls()
                                     if url.isLocalFile()])
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self, command=None):
        super().__init__()
        install_native_theme()
        self.extractor_command = command
        self.sources = []
        self.results = {}
        self.worker = None
        self.close_after_cancel = False
        self.update_checker = UpdateChecker(self)
        self.setWindowTitle(f"murums PS4 PKG Extractor UI · {__version__}")
        self.setWindowIcon(QIcon(str(asset_path("icon.svg"))))
        self.resize(1060, 780)
        self.setMinimumSize(900, 660)
        self.setStyleSheet(STYLE)
        self.build_interface()
        self.update_actions()

    def build_interface(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(13)
        header = QHBoxLayout()
        identity = QVBoxLayout()
        identity.setSpacing(2)
        identity.addWidget(label("FILE TOOLS", "Brand"))
        identity.addWidget(label("murums PS4 PKG Extractor UI", "Title"))
        identity.addWidget(label("Extract PS4 packages into separate folders.", "Subtitle"))
        header.addLayout(identity, 1)
        about = QPushButton("About")
        about.setObjectName("Quiet")
        about.clicked.connect(self.show_about)
        header.addWidget(about, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self.drop_area = DropArea()
        self.add_button = self.drop_area.add_button
        self.add_button.clicked.connect(self.choose_files)
        self.drop_area.files_dropped.connect(self.add_files)
        layout.addWidget(self.drop_area)
        queue_header = QHBoxLayout()
        self.queue_label = label("Files · 0", "SectionTitle")
        queue_header.addWidget(self.queue_label, 1)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.setObjectName("Quiet")
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("Quiet")
        self.clear_button.clicked.connect(self.clear_files)
        queue_header.addWidget(self.remove_button)
        queue_header.addWidget(self.clear_button)
        layout.addLayout(queue_header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PACKAGE", "TYPE", "STATUS", "RESULT"])
        self.table.setAccessibleName("Packages to extract")
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(44)
        for column in (0, 3):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        for column, width in ((1, 85), (2, 120)):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, width)
        self.table.setMinimumHeight(100)
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setAccessibleName("Extraction details")
        self.details.setMaximumBlockCount(3000)
        self.details.setMinimumHeight(70)
        self.details.hide()
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(self.details)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        panel = QFrame()
        panel.setObjectName("OutputPanel")
        output_layout = QVBoxLayout(panel)
        output_layout.setContentsMargins(14, 11, 14, 11)
        output_layout.setSpacing(6)
        output_label = label("Output folder", "SectionTitle")
        output_layout.addWidget(output_label)
        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Choose a PKG output folder")
        self.output_edit.setAccessibleName("Output folder")
        output_label.setBuddy(self.output_edit)
        self.output_edit.textChanged.connect(self.update_actions)
        output_row.addWidget(self.output_edit, 1)
        self.browse_button = QPushButton("Browse…")
        self.browse_button.clicked.connect(self.choose_output)
        output_row.addWidget(self.browse_button)
        output_layout.addLayout(output_row)
        output_layout.addWidget(label("Folders by title ID: CUSA…, CUSA…-patch. Existing names get numbered copies.", "Hint"))
        layout.addWidget(panel)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setAccessibleName("Overall extraction progress")
        layout.addWidget(self.progress)
        actions = QHBoxLayout()
        self.details_button = QPushButton("Show details")
        self.details_button.setObjectName("Quiet")
        self.details_button.clicked.connect(self.toggle_details)
        self.open_button = QPushButton("Open output folder")
        self.open_button.setObjectName("Quiet")
        self.open_button.clicked.connect(self.open_output)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_extraction)
        self.cancel_button.hide()
        self.extract_button = QPushButton("Extract PKG")
        self.extract_button.setObjectName("Primary")
        self.extract_button.clicked.connect(self.start_extraction)
        actions.addWidget(self.details_button)
        actions.addWidget(self.open_button)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.extract_button)
        layout.addLayout(actions)
        self.status_label = label("Add PKG files to get started.", "Hint", True)
        layout.addWidget(self.status_label)
        order = [self.add_button, self.table, self.remove_button, self.clear_button,
                 self.output_edit, self.browse_button, self.extract_button, self.cancel_button,
                 self.details_button, self.open_button, about]
        for before, after in zip(order, order[1:]):
            QWidget.setTabOrder(before, after)

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add PS4 packages", "", "PS4 packages (*.pkg)")
        self.add_files([Path(path) for path in paths])

    def add_files(self, paths):
        if self.worker is not None:
            return
        skipped = 0
        for path in paths:
            try:
                path = Path(path).resolve(strict=True)
                if not path.is_file() or path.suffix.lower() != ".pkg" or path in self.sources:
                    skipped += 1
                    continue
            except (OSError, ValueError):
                skipped += 1
                continue
            kind = "—"
            tooltip = str(path)
            try:
                info = read_package(path)
                kind = info.kind
                tooltip += f"\n{info.title_id} · {info.title}"
            except PackageError as error:
                tooltip += f"\n{error}"
            self.sources.append(path)
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, text in enumerate((path.name, kind, "Ready", "—")):
                self.table.setItem(row, column, QTableWidgetItem(text))
            self.table.item(row, 0).setToolTip(tooltip)
        if self.sources and not self.output_edit.text():
            self.output_edit.setText(str(self.sources[0].parent))
        self.results.clear()
        self.extract_button.setText("Extract PKG")
        self.queue_label.setText(f"Files · {len(self.sources)}")
        self.status_label.setText(f"Queued: {len(self.sources)}" +
                                  (f" · Skipped: {skipped} duplicates or non-PKG files" if skipped else ""))
        self.update_actions()

    def remove_selected(self):
        if self.worker is not None:
            return
        for row in sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True):
            self.sources.pop(row)
            self.table.removeRow(row)
        self.results.clear()
        self.queue_label.setText(f"Files · {len(self.sources)}")
        self.status_label.setText(f"Queued: {len(self.sources)}")
        self.update_actions()

    def clear_files(self):
        if self.worker is not None:
            return
        self.sources.clear()
        self.results.clear()
        self.table.setRowCount(0)
        self.details.clear()
        self.progress.setValue(0)
        self.queue_label.setText("Files · 0")
        self.status_label.setText("Add PKG files to get started.")
        self.extract_button.setText("Extract PKG")
        self.update_actions()

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_edit.text())
        if path:
            self.output_edit.setText(path)

    def update_actions(self):
        busy = self.worker is not None
        output_text = self.output_edit.text().strip()
        try:
            existing = bool(output_text) and Path(output_text).expanduser().is_dir()
        except (OSError, ValueError):
            existing = False
        self.drop_area.setEnabled(not busy)
        self.output_edit.setEnabled(not busy)
        self.browse_button.setEnabled(not busy)
        self.remove_button.setEnabled(not busy and bool(self.table.selectedIndexes()))
        self.clear_button.setEnabled(not busy and bool(self.sources))
        self.extract_button.setEnabled(not busy and bool(self.sources) and bool(output_text))
        self.open_button.setEnabled(existing)
        self.cancel_button.setVisible(busy)

    def start_extraction(self):
        if self.worker is not None or not self.extract_button.isEnabled():
            return
        self.results.clear()
        self.details.clear()
        self.progress.setRange(0, 0)
        for row in range(len(self.sources)):
            self.set_row(row, "Waiting", "—")
        self.worker = ExtractionWorker(list(self.sources), Path(self.output_edit.text().strip()),
                                       self, self.extractor_command)
        self.worker.file_started.connect(self.file_started)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.message.connect(self.details.appendPlainText)
        self.worker.file_finished.connect(self.file_finished)
        self.worker.finished.connect(self.batch_finished)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Reading package…")
        self.update_actions()
        self.worker.start()

    def file_started(self, row):
        self.set_row(row, "Extracting", "—")
        self.progress.setRange(0, 0)
        self.status_label.setText(f"Extracting {row + 1} of {len(self.sources)} · {self.sources[row].name}")

    def update_progress(self, row, current, total):
        self.progress.setRange(0, 100)
        percent = min(99, int(current * 100 / max(total, 1)))
        self.progress.setValue(int((row * 100 + percent) / max(len(self.sources), 1)))
        self.status_label.setText(f"Package {row + 1} of {len(self.sources)} · Entry {current:,} of {total:,}")

    def set_row(self, row, state, result):
        colors = {"Extracted": "#73e0be", "Failed": "#ffb4b4",
                  "Cancelled": "#d7bd8a", "Extracting": "#70cfee"}
        self.table.item(row, 2).setText(state)
        self.table.item(row, 2).setForeground(QColor(colors.get(state, "#a7bbce")))
        self.table.item(row, 3).setText(result)

    def file_finished(self, row, state, detail):
        self.results[row] = state
        self.set_row(row, state, Path(detail).name if state == "Extracted" else detail)
        self.table.item(row, 3).setToolTip(detail)
        self.details.appendPlainText(f"{state} · {self.sources[row].name}\n{detail}\n")
        self.progress.setRange(0, 100)
        self.progress.setValue(int((row + 1) * 100 / max(len(self.sources), 1)))
        if state == "Failed":
            self.details.show()
            self.details_button.setText("Hide details")

    def batch_finished(self):
        worker = self.worker
        self.worker = None
        worker.deleteLater()
        counts = {state: list(self.results.values()).count(state)
                  for state in ("Extracted", "Failed", "Cancelled")}
        self.status_label.setText(" · ".join(f"{count} {state.lower()}" for state, count in counts.items()))
        self.extract_button.setText("Extract again")
        self.update_actions()
        if self.close_after_cancel:
            self.close()

    def cancel_extraction(self):
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling… Keeping completed results.")

    def toggle_details(self):
        visible = not self.details.isVisible()
        self.details.setVisible(visible)
        self.details_button.setText("Hide details" if visible else "Show details")

    def open_output(self):
        path = str(Path(self.output_edit.text().strip()).expanduser().resolve())
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.status_label.setText("Could not open folder. Copy the output path above.")

    def show_about(self):
        dialog = AboutDialog(self.update_checker, self)
        dialog.exec()
        dialog.deleteLater()

    def closeEvent(self, event):
        if self.worker is not None:
            self.close_after_cancel = True
            self.cancel_extraction()
            event.ignore()
        else:
            event.accept()
