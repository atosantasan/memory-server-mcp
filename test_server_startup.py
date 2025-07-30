#!/usr/bin/env python3
"""
Test script for server startup functionality
Tests the server lifecycle management implementation
"""

import asyncio
import logging
import sys
import os
import time
from unittest.mock import patch, MagicMock

# Add current directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import Config, ServerManager, logger

async def test_server_startup():
    """Test server startup and shutdown functionality"""
    print("Testing server startup and lifecycle management...")
    
    # Test configuration validation
    try:
        Config.validate_config()
        print("✓ Configuration validation passed")
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False
    
    # Test server manager initialization
    try:
        server_manager = ServerManager()
        print("✓ ServerManager initialized successfully")
    except Exception as e:
        print(f"✗ ServerManager initialization failed: {e}")
        return False
    
    # Test logging setup
    try:
        test_logger = Config.setup_logging()
        test_logger.info("Test log message")
        print("✓ Logging setup successful")
    except Exception as e:
        print(f"✗ Logging setup failed: {e}")
        return False
    
    # Test shutdown signal
    try:
        server_manager.signal_shutdown()
        print("✓ Shutdown signal test passed")
    except Exception as e:
        print(f"✗ Shutdown signal test failed: {e}")
        return False
    
    print("All server startup tests passed!")
    return True

async def test_config_environment_variables():
    """Test configuration with environment variables"""
    print("\nTesting environment variable configuration...")
    
    # Test with custom environment variables
    test_env = {
        "MEMORY_SERVER_HOST": "127.0.0.1",
        "MEMORY_SERVER_PORT": "9000",
        "MEMORY_LOG_LEVEL": "DEBUG",
        "MEMORY_MAX_SEARCH_RESULTS": "50"
    }
    
    with patch.dict(os.environ, test_env):
        # Reload config class to pick up new environment variables
        import importlib
        import main
        importlib.reload(main)
        
        # Check if environment variables are properly loaded
        if main.Config.HOST == "127.0.0.1":
            print("✓ HOST environment variable loaded correctly")
        else:
            print(f"✗ HOST environment variable not loaded: {main.Config.HOST}")
            return False
        
        if main.Config.PORT == 9000:
            print("✓ PORT environment variable loaded correctly")
        else:
            print(f"✗ PORT environment variable not loaded: {main.Config.PORT}")
            return False
        
        if main.Config.LOG_LEVEL == "DEBUG":
            print("✓ LOG_LEVEL environment variable loaded correctly")
        else:
            print(f"✗ LOG_LEVEL environment variable not loaded: {main.Config.LOG_LEVEL}")
            return False
    
    print("Environment variable configuration tests passed!")
    return True

async def main():
    """Main test function"""
    print("=== Server Startup and Lifecycle Management Tests ===")
    
    # Run tests
    startup_test = await test_server_startup()
    env_test = await test_config_environment_variables()
    
    if startup_test and env_test:
        print("\n✓ All tests passed successfully!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)