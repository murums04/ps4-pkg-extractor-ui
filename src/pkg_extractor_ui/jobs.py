import threading

from PySide6.QtCore import QThread, Signal

from .backend import ExtractionCancelled, ExtractionError, extract_package


class ExtractionWorker(QThread):
    file_started = Signal(int)
    progress_changed = Signal(int, int, int)
    file_finished = Signal(int, str, str)
    message = Signal(str)

    def __init__(self, sources, output, parent=None, command=None):
        super().__init__(parent)
        self.sources = sources
        self.output = output
        self.command = command
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def run(self):
        for row, source in enumerate(self.sources):
            if self.cancelled.is_set():
                self.file_finished.emit(row, "Cancelled", "Not started.")
                continue
            self.file_started.emit(row)
            last_percent = -1

            def progress(current, total):
                nonlocal last_percent
                percent = int(current * 100 / max(total, 1))
                if percent != last_percent:
                    self.progress_changed.emit(row, current, total)
                    last_percent = percent
            try:
                result = extract_package(source, self.output, self.command, self.cancelled,
                                         progress, self.message.emit)
                self.file_finished.emit(row, "Extracted", str(result))
            except ExtractionCancelled as error:
                self.file_finished.emit(row, "Cancelled", str(error))
            except (ExtractionError, OSError) as error:
                self.file_finished.emit(row, "Failed", str(error))
            except Exception as error:
                self.file_finished.emit(row, "Failed", f"Unexpected extraction error: {error}")
