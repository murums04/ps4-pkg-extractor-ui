import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .assets import resource_root
from .metadata import PackageError, PackageInfo, read_package


class ExtractionError(RuntimeError):
    pass


class ExtractionCancelled(ExtractionError):
    pass


def bundled_command() -> list[str]:
    if sys.platform == "win32" and sys.getwindowsversion().build < 18362:
        raise ExtractionError("The extractor requires Windows 10 version 1903 or later for Unicode paths.")
    name = "pkg_extractor.exe" if sys.platform == "win32" else "pkg_extractor"
    executable = resource_root() / "backend" / name
    if not executable.is_file():
        raise ExtractionError("The bundled extractor was not found. Reinstall or re-extract the complete app.")
    return [str(executable)]


def stream_output(process, messages, stop):
    try:
        for line in iter(lambda: process.stdout.readline(16384), ""):
            while not stop.is_set():
                try:
                    messages.put(line.rstrip("\r\n"), timeout=0.1)
                    break
                except queue.Full:
                    continue
            if stop.is_set():
                break
    finally:
        process.stdout.close()


def run_extractor(command, source, staging, working_directory, cancel, progress, log):
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    environment = os.environ.copy()
    if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
        environment["LD_LIBRARY_PATH"] = os.pathsep.join(
            [str(resource_root() / "backend"), str(resource_root())])
    try:
        process = subprocess.Popen(
            [*command, str(source), str(staging)], cwd=working_directory, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", env=environment, **options)
    except OSError as error:
        raise ExtractionError(f"Could not start the extractor: {error}") from error
    messages = queue.Queue(maxsize=128)
    stop_reader = threading.Event()
    reader = threading.Thread(target=stream_output, args=(process, messages, stop_reader), daemon=True)
    reader.start()
    complete = False
    current = total = 0
    failure = None
    try:
        while reader.is_alive() or not messages.empty() or process.poll() is None:
            if cancel.is_set():
                raise ExtractionCancelled("Extraction cancelled.")
            try:
                line = messages.get(timeout=0.05)
            except queue.Empty:
                continue
            if not line:
                continue
            if line.startswith("THE END "):
                complete = True
                log(line)
                continue
            match = re.match(r"^\s*Extracting file (\d+) of (\d+)(?: to .+)?$", line)
            if match:
                current, total = map(int, match.groups())
                progress(current, total)
            else:
                log(line)
            if (line.startswith(("Cannot open PKG file :", "Cannot extract PKG file :",
                                 "Could not read SFO.", "PSF file there is no CONTENT_ID"))
                    or line.endswith("doesn't appear to be a valid PKG file")):
                failure = line
        exit_code = process.wait()
        if cancel.is_set():
            raise ExtractionCancelled("Extraction cancelled.")
        if failure:
            raise ExtractionError(failure)
        if exit_code != 0:
            raise ExtractionError(f"The extractor stopped with code {exit_code}. See details.")
        if not complete or (total and current != total):
            raise ExtractionError("The extractor did not finish the package.")
    finally:
        stop_reader.set()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        reader.join(timeout=3)
    return current, total


def verify_output(staging: Path, info: PackageInfo, total: int):
    package_folder = staging / info.output_relative
    metadata_file = package_folder / "sce_sys" / "param.sfo"
    if not metadata_file.is_file() or metadata_file.is_symlink():
        raise ExtractionError("The extractor did not create the expected package files.")
    if metadata_file.read_bytes() != info.sfo:
        raise ExtractionError("The extracted package metadata does not match the input.")
    if info.pfs_size > 0 and total == 0:
        raise ExtractionError("The extractor produced metadata but no package payload.")
    for folder, directories, files in os.walk(staging, followlinks=False):
        for name in directories + files:
            path = Path(folder) / name
            if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(staging):
                raise ExtractionError("The extracted output contains an unsupported linked path.")


def publish_output(staging: Path, output: Path, name: str) -> Path:
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")[:100] or "package"
    if safe_name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1, 10)), *("LPT" + str(i) for i in range(1, 10))}:
        safe_name = "package-" + safe_name
    for number in range(1, 100_001):
        target = output / (safe_name if number == 1 else f"{safe_name} ({number})")
        try:
            target.mkdir()
        except FileExistsError:
            continue
        try:
            for child in staging.iterdir():
                child.rename(target / child.name)
            return target
        except OSError as error:
            raise ExtractionError(f"Could not finish moving the result. Recovery files remain at {target} and {staging}: {error}") from error
    raise ExtractionError("Too many output folders with this name.")


def extract_package(source: Path, output: Path, command=None, cancel=None,
                    progress=None, log=None) -> Path:
    cancel = cancel if cancel is not None else threading.Event()
    progress = progress or (lambda current, total: None)
    log = log or (lambda message: None)
    staging = None
    preserve_staging = False
    try:
        if cancel.is_set():
            raise ExtractionCancelled("Extraction cancelled.")
        info = read_package(source)
        before = info.source.stat()
        output = Path(output).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        command = command or bundled_command()
        staging = Path(tempfile.mkdtemp(prefix=".pkg-", dir=output)).resolve()
        payload = staging / "payload"
        payload.mkdir()
        working_directory = staging / "engine-work"
        # Upstream's static initializer uses this portable folder instead of the emulator profile.
        (working_directory / "user").mkdir(parents=True)
        log(f"Input: {info.source}")
        log(f"{info.kind} · {info.title_id} · {info.title}")
        _, total = run_extractor(command, info.source, payload, working_directory, cancel, progress, log)
        after = info.source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ExtractionError("The input file changed during extraction.")
        verify_output(payload, info, total)
        if cancel.is_set():
            raise ExtractionCancelled("Extraction cancelled.")
        preserve_staging = True
        package_root = payload / info.output_relative.parts[0]
        result = publish_output(package_root, output, package_root.name)
        preserve_staging = False
        log(f"Output: {result}")
        return result
    except (OSError, PackageError) as error:
        raise ExtractionError(str(error)) from error
    finally:
        if staging is not None and staging.exists() and not preserve_staging:
            if staging.parent != output or not staging.name.startswith(".pkg-") or staging.is_symlink():
                raise ExtractionError(f"Could not safely remove the partial output at {staging}.")
            try:
                shutil.rmtree(staging)
            except OSError as error:
                raise ExtractionError(f"Partial output remains at {staging}: {error}") from error
