#!/usr/bin/env python3
"""
Test script for full server startup
Tests both MCP and FastAPI servers startup
"""

import asyncio
import sys
import os
import signal
import time

# Add current directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_server, logger

async def test_server_startup_with_timeout():
    """Test server startup with automatic shutdown after a few seconds"""
    print("Testing full server startup (will auto-shutdown in 3 seconds)...")
    
    # Create a task to run the server
    server_task = asyncio.create_task(asyncio.to_thread(run_server))
    
    # Wait for a few seconds then cancel
    try:
        await asyncio.wait_for(server_task, timeout=3.0)
    except asyncio.TimeoutError:
        print("✓ Server started successfully and ran for 3 seconds")
        # The server is still running, which is expected
        return True
    except Exception as e:
        print(f"✗ Server startup failed: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("=== Full Server Startup Test ===")
    
    try:
        # Test server startup with timeout
        result = asyncio.run(test_server_startup_with_timeout())
        
        if result:
            print("✓ Full server startup test completed successfully!")
            return 0
        else:
            print("✗ Full server startup test failed!")
            return 1
            
    except KeyboardInterrupt:
        print("Test interrupted by user")
        return 0
    except Exception as e:
        print(f"Test error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)