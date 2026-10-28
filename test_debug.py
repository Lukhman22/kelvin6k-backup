import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest

if __name__ == '__main__':
    # Run all tests using discover
    suite = unittest.defaultTestLoader.discover('tests')
    
    # We want to see the stdout of the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
