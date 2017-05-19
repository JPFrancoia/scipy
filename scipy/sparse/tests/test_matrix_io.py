from __future__ import division, print_function, absolute_import

import sys
import os
import numpy as np
import tempfile

from numpy.testing import assert_array_almost_equal, run_module_suite, assert_, assert_raises, dec
from scipy._lib._version import NumpyVersion

from scipy.sparse import csc_matrix, csr_matrix, bsr_matrix, dia_matrix, coo_matrix, save_npz, load_npz


def _save_and_load(matrix):
    fd, tmpfile = tempfile.mkstemp(suffix='.npz')
    os.close(fd)
    try:
        save_npz(tmpfile, matrix)
        loaded_matrix = load_npz(tmpfile)
    finally:
        os.remove(tmpfile)
    return loaded_matrix

def _check_save_and_load(dense_matrix):
    for matrix_class in [csc_matrix, csr_matrix, bsr_matrix, dia_matrix, coo_matrix]:
        matrix = matrix_class(dense_matrix)
        loaded_matrix = _save_and_load(matrix)
        assert_(type(loaded_matrix) is matrix_class)
        assert_(loaded_matrix.shape == dense_matrix.shape)
        assert_(loaded_matrix.dtype == dense_matrix.dtype)
        assert_array_almost_equal(loaded_matrix.toarray(), dense_matrix)

def test_save_and_load_random():
    N = 10
    np.random.seed(0)
    dense_matrix = np.random.random((N, N))
    dense_matrix[dense_matrix > 0.7] = 0
    _check_save_and_load(dense_matrix)

def test_save_and_load_empty():
    dense_matrix = np.zeros((4,6))
    _check_save_and_load(dense_matrix)

def test_save_and_load_one_entry():
    dense_matrix = np.zeros((4,6))
    dense_matrix[1,2] = 1
    _check_save_and_load(dense_matrix)


@dec.skipif(NumpyVersion(np.__version__) < '1.10.0',
            'disabling unpickling requires numpy >= 1.10.0')
def test_malicious_load():
    class Executor(object):
        def __reduce__(self):
            return (assert_, (False, 'unexpected code execution'))

    fd, tmpfile = tempfile.mkstemp(suffix='.npz')
    os.close(fd)
    try:
        np.savez(tmpfile, format=Executor())

        # Should raise a ValueError, not execute code
        assert_raises(ValueError, load_npz, tmpfile)
    finally:
        os.remove(tmpfile)


if __name__ == "__main__":
    run_module_suite()
