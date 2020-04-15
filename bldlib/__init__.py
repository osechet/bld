"""
The bld lib provides build helper tools.
"""

#
# Package's version
#
try:
    from ._version import version as __version__
except ImportError:
    # broken installation, we don't even try
    __version__ = "unknown"
