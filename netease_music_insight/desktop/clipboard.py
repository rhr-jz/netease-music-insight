"""Windows Unicode clipboard for reliable copying from the desktop window."""
import ctypes
import sys
import time


def copy_text(value):
    if sys.platform != "win32":
        raise OSError("此桌面复制功能目前仅支持 Windows。")
    if not isinstance(value, str) or not value:
        raise ValueError("没有可复制的 Prompt。")

    kernel = ctypes.windll.kernel32
    user = ctypes.windll.user32
    kernel.GlobalAlloc.argtypes = (ctypes.c_uint, ctypes.c_size_t)
    kernel.GlobalAlloc.restype = ctypes.c_void_p
    kernel.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    kernel.GlobalFree.argtypes = (ctypes.c_void_p,)
    user.OpenClipboard.argtypes = (ctypes.c_void_p,)
    user.SetClipboardData.argtypes = (ctypes.c_uint, ctypes.c_void_p)
    user.SetClipboardData.restype = ctypes.c_void_p

    encoded = (value + "\0").encode("utf-16-le")
    handle = kernel.GlobalAlloc(0x0002, len(encoded))  # GMEM_MOVEABLE
    if not handle:
        raise OSError("无法分配剪贴板内存。")
    opened = False
    try:
        pointer = kernel.GlobalLock(handle)
        if not pointer:
            raise OSError("无法写入剪贴板内存。")
        try:
            ctypes.memmove(pointer, encoded, len(encoded))
        finally:
            kernel.GlobalUnlock(handle)
        for _ in range(5):
            if user.OpenClipboard(None):
                opened = True
                break
            time.sleep(0.05)
        if not opened:
            raise OSError("剪贴板正被其他程序占用，请稍后重试。")
        if not user.EmptyClipboard() or not user.SetClipboardData(13, handle):
            raise OSError("写入剪贴板失败。")
        handle = None  # Clipboard owns the memory after SetClipboardData succeeds.
    finally:
        if opened:
            user.CloseClipboard()
        if handle:
            kernel.GlobalFree(handle)
