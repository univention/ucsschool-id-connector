import pytest
import doctest


@pytest.mark.parametrize('filename', ['example.md','example2.rst'])
def test_doc(filename):
    results: doctest.TestResults = doctest.testfile(filename, optionflags=doctest.ELLIPSIS)
    assert results.failed == 0
