# PyInstaller hook for fastmcp
from PyInstaller.utils.hooks import copy_metadata, collect_all

# Copy metadata for fastmcp
datas = copy_metadata('fastmcp')
datas += copy_metadata('mcp')

# Collect all fastmcp modules
hiddenimports = ['fastmcp.server', 'fastmcp.client', 'fastmcp.settings', 'fastmcp.utilities.logging']

# Add additional imports that might be missed
hiddenimports += [
    'importlib.metadata',
    'pkg_resources',
    'fastmcp.server.server',
    'fastmcp.server.context',
]