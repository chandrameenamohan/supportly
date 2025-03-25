#!/usr/bin/env python
"""
Script to run the sample test cases for the products database integration.
This script provides a convenient way to run the sample tests with detailed output.
"""

import os
import sys
import asyncio
import unittest
import importlib
import argparse
from unittest.mock import patch
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def setup_colored_output():
    """Set up colored output for test results."""
    try:
        import colorama
        colorama.init()
        return True
    except ImportError:
        print("Note: Install 'colorama' for colored test output")
        return False


def color_text(text, color_code):
    """Color text if colorama is available."""
    if setup_colored_output():
        return f"{color_code}{text}\033[0m"
    return text


def green(text):
    """Return text in green color."""
    return color_text(text, "\033[92m")


def red(text):
    """Return text in red color."""
    return color_text(text, "\033[91m")


def yellow(text):
    """Return text in yellow color."""
    return color_text(text, "\033[93m")


def blue(text):
    """Return text in blue color."""
    return color_text(text, "\033[94m")


def run_sample_tests(test_name=None, verbose=False):
    """
    Run the sample test cases.
    
    Args:
        test_name: The name of the test to run, or None to run all tests
        verbose: Whether to show verbose output
    """
    print(blue("\n=== Running Sample Test Cases for Products Database Integration ===\n"))
    
    # Check if the test modules are available
    try:
        from database.products_agent import ProductsAgent
        from database.products_repository import ProductsRepository
        print(green("✓ Database modules are available"))
    except ImportError:
        print(red("❌ Database modules are not available"))
        print(yellow("Please make sure the database package is installed and in your PYTHONPATH"))
        return False
    
    # Try to import the main application modules
    try:
        from agents.products_agent import ProductsAgent as MainProductsAgent
        print(green("✓ Main application modules are available"))
        main_app_available = True
    except ImportError:
        print(yellow("⚠ Main application modules are not available - some tests will be skipped"))
        main_app_available = False
    
    # Run the tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Import the test module
    try:
        test_module = importlib.import_module("database.tests.test_main_application_sample")
        print(green("✓ Test module loaded successfully"))
        
        # Add the tests to the suite
        if test_name:
            suite.addTest(loader.loadTestsFromName(test_name, test_module))
        else:
            if main_app_available:
                suite.addTest(loader.loadTestsFromTestCase(test_module.TestProductsAgentSample))
                suite.addTest(loader.loadTestsFromTestCase(test_module.TestMainIntegrationSample))
                print(green("✓ Added all test cases to the suite"))
            else:
                suite.addTest(loader.loadTestsFromTestCase(test_module.TestProductsAgentSample))
                print(yellow("⚠ Added only ProductsAgentSample test cases (main application not available)"))
        
        # Create a test runner
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        
        # Run the tests
        print(blue("\n--- Starting Tests ---\n"))
        start_time = datetime.now()
        result = runner.run(suite)
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Print test result summary
        print(blue("\n--- Test Results ---\n"))
        if result.wasSuccessful():
            print(green(f"✓ All tests passed ({result.testsRun} tests) in {duration.total_seconds():.2f} seconds"))
        else:
            print(red(f"❌ {len(result.failures) + len(result.errors)} tests failed out of {result.testsRun}"))
            
            if result.failures:
                print(red("\nFailures:"))
                for test, traceback in result.failures:
                    print(red(f"- {test}"))
                    if verbose:
                        print(traceback)
            
            if result.errors:
                print(red("\nErrors:"))
                for test, traceback in result.errors:
                    print(red(f"- {test}"))
                    if verbose:
                        print(traceback)
        
        return result.wasSuccessful()
    
    except ImportError as e:
        print(red(f"❌ Failed to load test module: {e}"))
        return False


def show_help():
    """Show additional help information."""
    print(blue("\nAdditional Information:"))
    print("  This script runs the sample test cases for the products database integration.")
    print("  The tests are designed to demonstrate how to test the integration between")
    print("  the database ProductsAgent and the main application.")
    print("\n  The following test cases are available:")
    print("  - TestProductsAgentSample: Tests for the ProductsAgent without main application")
    print("  - TestMainIntegrationSample: Tests for integration with the main application")
    print("\n  Examples:")
    print("  - Run a specific test:")
    print("    python run_sample_test.py -t TestProductsAgentSample.test_search_products")
    print("  - Run all tests with verbose output:")
    print("    python run_sample_test.py -v")
    print("\n  Note: Some tests will be skipped if the main application modules are not available.")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run sample test cases for the products database integration"
    )
    parser.add_argument(
        "-t", "--test", 
        help="Specific test to run (e.g., TestProductsAgentSample.test_search_products)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Show verbose output"
    )
    parser.add_argument(
        "--help-more", 
        action="store_true", 
        help="Show more detailed help information"
    )
    
    args = parser.parse_args()
    
    if args.help_more:
        show_help()
        sys.exit(0)
    
    # Run the tests
    success = run_sample_tests(args.test, args.verbose)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 