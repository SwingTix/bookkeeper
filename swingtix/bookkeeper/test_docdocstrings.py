

def load_tests(loader,tests,pattern):

    readme_rst = "../../README.rst"
    import doctest

    tests.addTests(doctest.DocFileSuite(readme_rst))
    return tests

