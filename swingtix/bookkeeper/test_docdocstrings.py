
import os
import unittest

def load_tests(loader,tests,pattern):

    readme_rst = "../../README.rst"
    readme_rst_relative = os.path.join(os.path.dirname(__file__), readme_rst)
    if os.path.isfile(readme_rst_relative):
        import doctest

        tests.addTests(doctest.DocFileSuite(readme_rst))
        return tests
    else:
        print "skipping documentation tests: README.rst not found."
        return unittest.TestSuite()

