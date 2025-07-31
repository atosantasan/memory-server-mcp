# PyInstaller hook for fastmcp - Windows optimized
from PyInstaller.utils.hooks import copy_metadata, collect_all, collect_submodules

# Copy metadata for all required packages
datas = []
for pkg in ['fastmcp', 'mcp', 'fastapi', 'uvicorn', 'pydantic', 'pydantic-core', 'typing-extensions', 'starlette']:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass  # Package might not be installed or have metadata

# Collect all fastmcp modules and submodules
hiddenimports = collect_submodules('fastmcp')

# Add specific fastmcp modules
hiddenimports += [
    'fastmcp.server', 
    'fastmcp.server.server',
    'fastmcp.server.context',
    'fastmcp.client', 
    'fastmcp.settings', 
    'fastmcp.utilities.logging',
]

# Add additional imports that might be missed
hiddenimports += [
    # Core Python modules
    'importlib.metadata',
    'pkg_resources',
    'sqlite3',
    'json',
    'logging',
    'logging.handlers',
    'datetime',
    'asyncio',
    'asyncio.events',
    'asyncio.protocols',
    'asyncio.transports',
    'asyncio.selector_events',
    'asyncio.proactor_events',  # Windows specific
    'multiprocessing',
    'multiprocessing.reduction',
    'multiprocessing.spawn',
    
    # FastAPI and dependencies
    'fastapi',
    'fastapi.applications',
    'fastapi.routing',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.exceptions',
    'starlette',
    'starlette.applications',
    'starlette.middleware',
    'starlette.routing',
    'starlette.responses',
    'starlette.exceptions',
    
    # Uvicorn server
    'uvicorn',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.server',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    
    # Pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic.main',
    'pydantic.validators',
    'pydantic._internal',
    'pydantic.json_schema',
    
    # Type annotations
    'typing',
    'typing_extensions',
    'dataclasses',
]

# Remove duplicates
hiddenimports = list(set(hiddenimports))