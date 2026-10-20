import ctypes
import hashlib
from ctypes import wintypes
from pathlib import Path


def enable_utf8(executable: Path, manifest_path: Path):
    original = hashlib.sha256(executable.read_bytes()).hexdigest()
    manifest = manifest_path.read_bytes()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    kernel.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                      wintypes.WORD, ctypes.c_void_p, wintypes.DWORD]
    kernel.UpdateResourceW.restype = wintypes.BOOL
    kernel.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    kernel.EndUpdateResourceW.restype = wintypes.BOOL
    handle = kernel.BeginUpdateResourceW(str(executable), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_string_buffer(manifest)
    if not kernel.UpdateResourceW(handle, ctypes.c_void_p(24), ctypes.c_void_p(1),
                                  0, buffer, len(manifest)):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel.EndUpdateResourceW(handle, True)
        raise error
    if not kernel.EndUpdateResourceW(handle, False):
        raise ctypes.WinError(ctypes.get_last_error())
    return original
