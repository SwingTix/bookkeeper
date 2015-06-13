import os
import unittest

def suite():
    """ For compatability with django 1.5 and earlier.  """

    current = os.path.dirname(os.path.realpath(__file__))
    top = os.path.normpath(os.path.join(current, "..", ".."))
    return unittest.TestLoader().discover(current, pattern='test_*.py', top_level_dir=top)

