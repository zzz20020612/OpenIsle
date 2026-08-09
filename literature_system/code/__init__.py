"""code 包初始化。

将 code/ 根目录加入 sys.path，让子包中的模块可以用绝对导入
（如 `from config import SQLITE_PATH`）访问根目录的基础模块。
这样既保持了包结构，又兼容旧的运行方式（`python code/collect/fetch_and_save.py`）。
"""
import os as _os
import sys as _sys

_CODE_ROOT = _os.path.dirname(_os.path.abspath(__file__))
if _CODE_ROOT not in _sys.path:
    _sys.path.insert(0, _CODE_ROOT)
