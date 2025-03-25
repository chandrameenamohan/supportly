#!/usr/bin/env python
"""
Test runner script for the products database tests.
This script discovers and runs all the tests in the tests directory.
"""

import os
import sys
import unittest

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_tests():
    """Discover and run all tests in the tests directory."""
    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create a test suite from all tests discovered in the tests directory
    test_suite = unittest.defaultTestLoader.discover(test_dir, pattern="test_*.py")
    
    # Create a test runner with verbosity=2 for detailed output
    test_runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the tests
    result = test_runner.run(test_suite)
    
    # Return 0 if all tests pass, 1 otherwise
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    # Exit with the appropriate exit code
    sys.exit(run_tests()) 