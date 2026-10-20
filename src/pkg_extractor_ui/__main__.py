import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .backend import ExtractionError, extract_package


def main():
    parser = argparse.ArgumentParser(description="Extract PS4 PKG files with shadPS4Plus.")
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--extract", action="store_true", help="Extract without the UI")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path, help="Write a new JSON result report")
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check-ui", type=Path, help=argparse.SUPPRESS)
    checks.add_argument("--check-updates", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.extract:
        if not args.files or args.output_dir is None:
            parser.error("--extract requires files and --output-dir")
        if args.report and args.report.exists():
            parser.error("The report already exists; choose a new path.")
        results = []
        for source in args.files:
            try:
                output = extract_package(source, args.output_dir)
                results.append({"source": str(source), "status": "extracted", "output": str(output)})
            except ExtractionError as error:
                results.append({"source": str(source), "status": "failed", "error": str(error)})
        if args.report:
            with args.report.open("x", encoding="utf-8") as report:
                json.dump(results, report, indent=2)
        elif sys.stdout is not None:
            print(json.dumps(results, indent=2))
        return int(any(result["status"] == "failed" for result in results))

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .window import MainWindow
    application = QApplication(sys.argv[:1])
    application.setApplicationName("PS4 PKG Extractor UI")
    application.setOrganizationName("murums")
    application.setStyle("Fusion")
    window = MainWindow()
    window.add_files(args.files)
    window.show()
    if args.check_updates:
        updates = window.update_checker
        completed_requests = []
        updates.manager.finished.connect(lambda reply: completed_requests.append(reply.url().toString()))

        def record_updates():
            try:
                with args.check_updates.open("x", encoding="utf-8") as report:
                    json.dump({"endpoint": updates.endpoint, "state": updates.state,
                               "message": updates.message, "requests": completed_requests}, report)
                application.exit(0 if updates.state in {"current", "available", "unpublished"} else 1)
            except OSError:
                application.exit(1)

        def update_finished():
            if updates.state not in {"idle", "checking"}:
                QTimer.singleShot(0, record_updates)

        updates.changed.connect(update_finished)
    if args.check_ui:
        def record_ui():
            try:
                from .backend import bundled_command
                with args.check_ui.open("x", encoding="utf-8") as report:
                    json.dump({"visible": window.isVisible(), "width": window.width(),
                               "height": window.height(), "platform": application.platformName(),
                               "extractor": bundled_command()[0]}, report)
                application.exit(0)
            except (OSError, ExtractionError):
                application.exit(1)
        QTimer.singleShot(350, record_ui)
    else:
        window.update_checker.start_automatic_check()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
