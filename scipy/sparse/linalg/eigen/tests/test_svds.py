import re
import copy
import numpy as np

from numpy.testing import (assert_allclose, assert_array_almost_equal_nulp,
                           assert_equal, assert_array_equal)
from pytest import raises as assert_raises
import pytest

from scipy.linalg import hilbert, svd
from scipy.sparse import csc_matrix, csr_matrix, isspmatrix
from scipy.sparse.linalg import LinearOperator
from scipy.sparse.linalg import svds
from scipy.sparse.linalg.eigen.arpack import ArpackNoConvergence


# --- Helper Functions / Classes ---


def sorted_svd(m, k, which='LM'):
    # Compute svd of a dense matrix m, and return singular vectors/values
    # sorted.
    if isspmatrix(m):
        m = m.todense()
    u, s, vh = svd(m)
    if which == 'LM':
        ii = np.argsort(s)[-k:]
    elif which == 'SM':
        ii = np.argsort(s)[:k]
    else:
        raise ValueError("unknown which=%r" % (which,))

    return u[:, ii], s[ii], vh[ii]


def svd_estimate(u, s, vh):
    return np.dot(u, np.dot(np.diag(s), vh))


def _check_svds(A, k, u, s, vh, which="LM", check_usvh_A=False,
                check_svd=True, atol=1e-10, rtol=1e-7):
    n, m = A.shape

    # Check shapes.
    assert_equal(u.shape, (n, k))
    assert_equal(s.shape, (k,))
    assert_equal(vh.shape, (k, m))

    # Check that the original matrix can be reconstituted.
    A_rebuilt = (u*s).dot(vh)
    assert_equal(A_rebuilt.shape, A.shape)
    if check_usvh_A:
        assert_allclose(A_rebuilt, A, atol=atol, rtol=rtol)

    # Check that u is a semi-orthogonal matrix.
    uh_u = np.dot(u.T.conj(), u)
    assert_equal(uh_u.shape, (k, k))
    assert_allclose(uh_u, np.identity(k), atol=atol, rtol=rtol)

    # Check that V is a semi-orthogonal matrix.
    vh_v = np.dot(vh, vh.T.conj())
    assert_equal(vh_v.shape, (k, k))
    assert_allclose(vh_v, np.identity(k), atol=atol, rtol=rtol)

    # Check that scipy.sparse.linalg.svds ~ scipy.linalg.svd
    if check_svd:
        u2, s2, vh2 = sorted_svd(A, k, which)
        assert_allclose(np.abs(u), np.abs(u2), atol=atol, rtol=rtol)
        assert_allclose(s, s2, atol=atol, rtol=rtol)
        assert_allclose(np.abs(vh), np.abs(vh2), atol=atol, rtol=rtol)


class CheckingLinearOperator(LinearOperator):
    def __init__(self, A):
        self.A = A
        self.dtype = A.dtype
        self.shape = A.shape

    def _matvec(self, x):
        assert_equal(max(x.shape), np.size(x))
        return self.A.dot(x)

    def _rmatvec(self, x):
        assert_equal(max(x.shape), np.size(x))
        return self.A.T.conjugate().dot(x)


# --- Test Input Validation ---
# Tests input validation on parameters `k` and `which`
# Needs better input validation checks for all other parameters

class SVDSCommonTests:

    solver = None

    # some of these IV tests could run only once, say with solver=None

    def test_svds_input_validation_A_1(self):
        message = "invalid shape"
        with pytest.raises(ValueError, match=message):
            svds([[[1., 2.], [3., 4.]]], k=1, solver=self.solver)

        message = "`A` must not be empty."
        with pytest.raises(ValueError, match=message):
            svds([[]], k=1, solver=self.solver)

    @pytest.mark.parametrize("A", ("hi", 1, [[1, 2], [3, 4]]))
    def test_svds_input_validation_A_2(self, A):
        message = "`A` must be of floating or complex floating data type."
        with pytest.raises(ValueError, match=message):
            svds(A, k=1, solver=self.solver)

    @pytest.mark.parametrize("k", [-1, 0, 3, 4, 5, 1.5, "1"])
    def test_svds_input_validation_k_1(self, k):
        rng = np.random.default_rng(0)
        A = rng.random((4, 3))

        message = ("`k` must be an integer satisfying")
        with pytest.raises(ValueError, match=message):
            svds(A, k=k, solver=self.solver)

    def test_svds_input_validation_k_2(self):
        # I think the stack trace is reasonable when `k` can't be converted
        # to an int.
        message = "int() argument must be a"
        with pytest.raises(TypeError, match=re.escape(message)):
            svds(np.eye(10), k=[], solver=self.solver)

        message = "invalid literal for int()"
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), k="hi", solver=self.solver)

    @pytest.mark.parametrize("tol", (-1, np.inf, np.nan))
    def test_svds_input_validation_tol_1(self, tol):
        message = "`tol` must be a non-negative floating point value."
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), tol=tol, solver=self.solver)

    @pytest.mark.parametrize("tol", ([], 'hi'))
    def test_svds_input_validation_tol_2(self, tol):
        # I think the stack trace is reasonable here
        message = "'<' not supported between instances"
        with pytest.raises(TypeError, match=message):
            svds(np.eye(10), tol=tol, solver=self.solver)

    @pytest.mark.parametrize("which", ('LA', 'SA', 'ekki', 0))
    def test_svds_input_validation_which(self, which):
        # Regression test for a github issue.
        # https://github.com/scipy/scipy/issues/4590
        # Function was not checking for eigenvalue type and unintended
        # values could be returned.
        with pytest.raises(ValueError, match="`which` must be in"):
            svds(np.eye(10), which=which, solver=self.solver)

    @pytest.mark.parametrize("transpose", (True, False))
    @pytest.mark.parametrize("n", range(4, 9))
    def test_svds_input_validation_v0_1(self, transpose, n):
        rng = np.random.default_rng(0)
        A = rng.random((5, 7))
        v0 = rng.random(n)
        if transpose:
            A = A.T
        k = 2
        message = "`v0` must have shape"

        required_length = (A.shape[0] if self.solver == 'propack'
                           else min(A.shape))
        if n != required_length:
            with pytest.raises(ValueError, match=message):
                svds(A, k=k, v0=v0, solver=self.solver)

    def test_svds_input_validation_v0_2(self):
        A = np.ones((10, 10))
        v0 = np.ones((1, 10))
        message = "`v0` must have shape"
        with pytest.raises(ValueError, match=message):
            svds(A, k=1, v0=v0, solver=self.solver)

    @pytest.mark.parametrize("v0", ("hi", 1, np.ones(10, dtype=int)))
    def test_svds_input_validation_v0_3(self, v0):
        A = np.ones((10, 10))
        message = "`v0` must be of floating or complex floating data type."
        with pytest.raises(ValueError, match=message):
            svds(A, k=1, v0=v0, solver=self.solver)

    @pytest.mark.parametrize("maxiter", (-1, 0, 5.5))
    def test_svds_input_validation_maxiter_1(self, maxiter):
        message = ("`maxiter` must be a non-negative integer.")
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), maxiter=maxiter, solver=self.solver)

    def test_svds_input_validation_maxiter_2(self):
        # I think the stack trace is reasonable when `k` can't be converted
        # to an int.
        message = "int() argument must be a"
        with pytest.raises(TypeError, match=re.escape(message)):
            svds(np.eye(10), maxiter=[], solver=self.solver)

        message = "invalid literal for int()"
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), maxiter="hi", solver=self.solver)

    @pytest.mark.parametrize("rsv", ('ekki', 10))
    def test_svds_input_validation_return_singular_vectors(self, rsv):
        message = "`return_singular_vectors` must be in"
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), return_singular_vectors=rsv, solver=self.solver)

    @pytest.mark.parametrize("random_state", ('ekki', 3.14159, []))
    def test_svds_input_validation_random_state(self, random_state):
        message = "cannot be used to seed a"
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), random_state=random_state, solver=self.solver)

    # --- Test Parameters ---

    @pytest.mark.parametrize("k", [3, 5])
    @pytest.mark.parametrize("which", ["LM", "SM"])
    def test_svds_parameter_k_which(self, k, which):
        # check that the `k` parameter sets the number of eigenvalues/
        # eigenvectors returned.
        # Also check that the `which` parameter sets whether the largest or
        # smallest eigenvalues are returned
        rng = np.random.default_rng(0)
        A = rng.random((10, 10))
        res = svds(A, k=k, which=which, solver=self.solver)
        _check_svds(A, k, *res, which=which)

    # loop instead of parametrize for simplicity
    def test_svds_parameter_tol(self):
        # check the effect of the `tol` parameter on solver accuracy by solving
        # the same problem with varying `tol` and comparing the eigenvalues
        # against ground truth computed
        n = 100  # matrix size
        k = 3    # number of eigenvalues to check

        # generate a random, sparse-ish matrix
        # effect isn't apparent for matrices that are too small
        rng = np.random.default_rng(0)
        A = rng.random((n, n))
        A[A > .1] = 0
        A = A @ A.T

        _, s, _ = svd(A)  # calculate ground truth

        # calculate the error as a function of `tol`
        A = csc_matrix(A)
        def err(tol):
            _, s2, _ = svds(A, k=k, v0=np.ones(n), solver=self.solver, tol=tol)
            return np.linalg.norm((s2 - s[k-1::-1])/s[k-1::-1])

        tols = [1e-4, 1e-2, 1e0]  # tolerance levels to check
        # for 'arpack' and 'propack', accuracies make discrete steps
        accuracies = {'propack': [1e-14, 1e-13, 1e-5],
                      'arpack': [1e-15, 1e-10, 1e-10],
                      'lobpcg': [1e-11, 1e-3, 10]}

        for tol, accuracy in zip(tols, accuracies[self.solver]):
            error = err(tol)
            assert error < accuracy
            assert error > accuracy/10

    def test_svd_v0(self):
        # check that the `v0` parameter affects the solution
        n = 100
        k = 1
        # If k != 1, LOBPCG needs more initial vectors, which are generated
        # with random_state, so it does not pass w/ k >= 2.
        # For some other values of `n`, the AssertionErrors are not raised
        # with different v0s, which is reasonable.

        rng = np.random.default_rng(0)
        A = rng.random((n, n))

        # with the same v0, solutions are the same, and they are accurate
        # v0 takes precedence over random_state
        v0a = rng.random(n)
        res1a = svds(A, k, v0=v0a, solver=self.solver, random_state=0)
        res2a = svds(A, k, v0=v0a, solver=self.solver, random_state=1)
        assert_equal(res1a, res2a)
        _check_svds(A, k, *res1a)

        # with the same v0, solutions are the same, and they are accurate
        v0b = rng.random(n)
        res1b = svds(A, k, v0=v0b, solver=self.solver, random_state=2)
        res2b = svds(A, k, v0=v0b, solver=self.solver, random_state=3)
        assert_equal(res1b, res2b)
        _check_svds(A, k, *res1b)

        # with different v0, solutions can be numerically different
        message = "Arrays are not equal"
        with pytest.raises(AssertionError, match=message):
            assert_equal(res1a, res1b)

    def test_svd_random_state(self):
        # check that the `random_state` parameter affects the solution
        # Admittedly, `n` and `k` are chosen so that all solver pass all
        # these checks. That's a tall order, since LOBPCG doesn't want to
        # achieve the desired accuracy and ARPACK often returns the same
        # singular values/vectors for different v0.
        n = 100
        k = 1

        rng = np.random.default_rng(0)
        A = rng.random((n, n))

        # with the same random_state, solutions are the same and accurate
        res1a = svds(A, k, solver=self.solver, random_state=0)
        res2a = svds(A, k, solver=self.solver, random_state=0)
        assert_equal(res1a, res2a)
        _check_svds(A, k, *res1a)

        # with the same random_state, solutions are the same and accurate
        res1b = svds(A, k, solver=self.solver, random_state=1)
        res2b = svds(A, k, solver=self.solver, random_state=1)
        assert_equal(res1b, res2b)
        _check_svds(A, k, *res1b)

        # with different random_state, solutions can be numerically different
        message = "Arrays are not equal"
        with pytest.raises(AssertionError, match=message):
            assert_equal(res1a, res1b)

    @pytest.mark.parametrize("random_state", (0, 1,
                                              np.random.RandomState(0),
                                              np.random.default_rng(0)))
    def test_svd_random_state_2(self, random_state):
        n = 100
        k = 1

        rng = np.random.default_rng(0)
        A = rng.random((n, n))

        random_state_2 = copy.deepcopy(random_state)

        # with the same random_state, solutions are the same and accurate
        res1a = svds(A, k, solver=self.solver, random_state=random_state)
        res2a = svds(A, k, solver=self.solver, random_state=random_state_2)
        assert_equal(res1a, res2a)

        _check_svds(A, k, *res1a)

    @pytest.mark.parametrize("random_state", (None,
                                              np.random.RandomState(0),
                                              np.random.default_rng(0)))
    def test_svd_random_state_3(self, random_state):
        n = 100
        k = 5

        rng = np.random.default_rng(0)
        A = rng.random((n, n))

        # random_state in different state produces accurate - but not
        # not necessarily identical - results
        res1a = svds(A, k, solver=self.solver, random_state=random_state)
        res2a = svds(A, k, solver=self.solver, random_state=random_state)

        _check_svds(A, k, *res1a)
        _check_svds(A, k, *res2a)

        message = "Arrays are not equal"
        with pytest.raises(AssertionError, match=message):
            assert_equal(res1a, res2a)

    def test_svd_maxiter(self):
        # check that maxiter works as expected: should not return accurate
        # solution after 1 iteration, but should with default `maxiter`
        A = hilbert(6)
        k = 1
        u, s, vh = sorted_svd(A, k)

        if self.solver == 'arpack':
            message = "ARPACK error -1: No convergence"
            with pytest.raises(ArpackNoConvergence, match=message):
                svds(A, k, ncv=3, maxiter=1, solver=self.solver)
        else:
            message = "Not equal to tolerance"
            with pytest.raises(AssertionError, match=message):
                u2, s2, vh2 = svds(A, k, maxiter=1, solver=self.solver)
                assert_allclose(np.abs(u2), np.abs(u))

        u, s, vh = svds(A, k, solver=self.solver)  # default maxiter
        _check_svds(A, k, u, s, vh)

    @pytest.mark.parametrize("rsv", (True, False, 'u', 'vh'))
    @pytest.mark.parametrize("shape", ((5, 7), (6, 6), (7, 5)))
    def test_svd_return_singular_vectors(self, rsv, shape):
        # check that the return_singular_vectors parameter works as expected
        rng = np.random.default_rng(0)
        A = rng.random(shape)
        k = 2
        M, N = shape
        u, s, vh = sorted_svd(A, k)

        if rsv is False:
            s2 = svds(A, k, return_singular_vectors=rsv,
                      solver=self.solver, random_state=rng)
            assert_allclose(s2, s)
        elif rsv == 'u' and N >= M:
            u2, s2, vh2 = svds(A, k, return_singular_vectors=rsv,
                               solver=self.solver, random_state=rng)
            assert_allclose(np.abs(u2), np.abs(u))
            assert_allclose(s2, s)
            assert vh2 is None
        elif rsv == 'vh' and N < M:
            u2, s2, vh2 = svds(A, k, return_singular_vectors=rsv,
                               solver=self.solver, random_state=rng)
            assert u2 is None
            assert_allclose(s2, s)
            assert_allclose(np.abs(vh2), np.abs(vh))
        else:
            u2, s2, vh2 = svds(A, k, return_singular_vectors=rsv,
                              solver=self.solver, random_state=rng)
            assert_allclose(np.abs(u2), np.abs(u))
            assert_allclose(s2, s)
            assert_allclose(np.abs(vh2), np.abs(vh))

    # --- Test Basic Functionality ---
    # Tests the accuracy of each solver for real and complex matrices provided
    # as dense array, sparse matrix, and LinearOperator. Could be written
    # more concisely and use parametrization.

    def test_svd_simple_real(self):
        solver = self.solver
        np.random.seed(0)  # set random seed for generating propack v0

        x = np.array([[1, 2, 3],
                      [3, 4, 3],
                      [1, 0, 2],
                      [0, 0, 1]], float)
        y = np.array([[1, 2, 3, 8],
                      [3, 4, 3, 5],
                      [1, 0, 2, 3],
                      [0, 0, 1, 0]], float)
        z = csc_matrix(x)

        for m in [x.T, x, y, z, z.T]:
            for k in range(1, min(m.shape)):
                u, s, vh = sorted_svd(m, k)
                su, ss, svh = svds(m, k, solver=solver)

                m_hat = svd_estimate(u, s, vh)
                sm_hat = svd_estimate(su, ss, svh)

                assert_array_almost_equal_nulp(
                    m_hat, sm_hat, nulp=1000 if solver != 'propack' else 1436)

    def test_svd_simple_complex(self):
        solver = self.solver

        x = np.array([[1, 2, 3],
                      [3, 4, 3],
                      [1 + 1j, 0, 2],
                      [0, 0, 1]], complex)
        y = np.array([[1, 2, 3, 8 + 5j],
                      [3 - 2j, 4, 3, 5],
                      [1, 0, 2, 3],
                      [0, 0, 1, 0]], complex)
        z = csc_matrix(x)

        for m in [x, x.T.conjugate(), x.T, y, y.conjugate(), z, z.T]:
            for k in range(1, min(m.shape) - 1):
                u, s, vh = sorted_svd(m, k)
                su, ss, svh = svds(m, k, solver=solver)

                m_hat = svd_estimate(u, s, vh)
                sm_hat = svd_estimate(su, ss, svh)

                assert_array_almost_equal_nulp(
                    m_hat, sm_hat, nulp=1000 if solver != 'propack' else 1575)

    def test_svd_linop(self):
        solver = self.solver

        nmks = [(6, 7, 3),
                (9, 5, 4),
                (10, 8, 5)]

        def reorder(args):
            U, s, VH = args
            j = np.argsort(s)
            return U[:, j], s[j], VH[j, :]

        for n, m, k in nmks:
            # Test svds on a LinearOperator.
            A = np.random.RandomState(52).randn(n, m)
            L = CheckingLinearOperator(A)

            if solver == 'propack':
                v0 = np.ones(n)
            else:
                v0 = np.ones(min(A.shape))

            U1, s1, VH1 = reorder(svds(A, k, v0=v0, solver=solver))
            U2, s2, VH2 = reorder(svds(L, k, v0=v0, solver=solver))

            assert_allclose(np.abs(U1), np.abs(U2))
            assert_allclose(s1, s2)
            assert_allclose(np.abs(VH1), np.abs(VH2))
            assert_allclose(np.dot(U1, np.dot(np.diag(s1), VH1)),
                            np.dot(U2, np.dot(np.diag(s2), VH2)))

            # Try again with which="SM".
            A = np.random.RandomState(1909).randn(n, m)
            L = CheckingLinearOperator(A)

            # TODO: arpack crashes when v0=v0, which="SM"
            kwargs = {'v0': v0} if solver not in {None, 'arpack'} else {}
            U1, s1, VH1 = reorder(svds(A, k, which="SM", solver=solver,
                                       **kwargs))
            U2, s2, VH2 = reorder(svds(L, k, which="SM", solver=solver,
                                       **kwargs))

            assert_allclose(np.abs(U1), np.abs(U2))
            assert_allclose(s1, s2)
            assert_allclose(np.abs(VH1), np.abs(VH2))
            assert_allclose(np.dot(U1, np.dot(np.diag(s1), VH1)),
                            np.dot(U2, np.dot(np.diag(s2), VH2)))

            if k < min(n, m) - 1:
                # Complex input and explicit which="LM".
                for (dt, eps) in [(complex, 1e-7), (np.complex64, 1e-3)]:
                    rng = np.random.RandomState(1648)
                    A = (rng.randn(n, m) + 1j * rng.randn(n, m)).astype(dt)
                    L = CheckingLinearOperator(A)

                    U1, s1, VH1 = reorder(svds(A, k, which="LM", solver=solver))
                    U2, s2, VH2 = reorder(svds(L, k, which="LM", solver=solver))

                    assert_allclose(np.abs(U1), np.abs(U2), rtol=eps)
                    assert_allclose(s1, s2, rtol=eps)
                    assert_allclose(np.abs(VH1), np.abs(VH2), rtol=eps)
                    assert_allclose(np.dot(U1, np.dot(np.diag(s1), VH1)),
                                    np.dot(U2, np.dot(np.diag(s2), VH2)),
                                    rtol=eps)

    # --- Test Edge Cases ---
    # Checks a few edge cases. There are obvious ones missing (e.g. empty inpout)
    # but I don't think we need to substantially expand these.

    def test_svd_LM_ones_matrix(self):
        # Check that svds can deal with matrix_rank less than k in LM mode.
        solver = self.solver

        k = 3
        for n, m in (6, 5), (5, 5), (5, 6):
            for t in float, complex:
                A = np.ones((n, m), dtype=t)

                U, s, VH = svds(A, k, solver=solver)

                # Check some generic properties of svd.
                _check_svds(A, k, U, s, VH, check_usvh_A=True, check_svd=False)

                # Check that the largest singular value is near sqrt(n*m)
                # and the other singular values have been forced to zero.
                assert_allclose(np.max(s), np.sqrt(n*m))
                assert_array_equal(sorted(s)[:-1], 0)

    def test_svd_LM_zeros_matrix(self):
        # Check that svds can deal with matrices containing only zeros.
        solver = self.solver

        k = 1
        for n, m in (3, 4), (4, 4), (4, 3):
            for t in float, complex:
                A = np.zeros((n, m), dtype=t)

                U, s, VH = svds(A, k, solver=solver)

                # Check some generic properties of svd.
                _check_svds(A, k, U, s, VH, check_usvh_A=True, check_svd=False)

                # Check that the singular values are zero.
                assert_array_equal(s, 0)

    def test_svd_LM_zeros_matrix_gh_3452(self):
        # Regression test for a github issue.
        # https://github.com/scipy/scipy/issues/3452
        # Note that for complex dype the size of this matrix is too small for k=1.
        solver = self.solver

        n, m, k = 4, 2, 1
        A = np.zeros((n, m))

        U, s, VH = svds(A, k, solver=solver)

        # Check some generic properties of svd.
        _check_svds(A, k, U, s, VH, check_usvh_A=True, check_svd=False)

        # Check that the singular values are zero.
        assert_array_equal(s, 0)


# --- Perform tests with each solver ---

class Test_SVDS_once():
    @pytest.mark.parametrize("solver", ['ekki', object])
    def test_svds_input_validation_solver(self, solver):
        message = "solver must be one of"
        with pytest.raises(ValueError, match=message):
            svds(np.ones((3, 4)), k=2, solver=solver)

class Test_SVDS_ARPACK(SVDSCommonTests):

    def setup_method(self):
        self.solver = 'arpack'


    @pytest.mark.parametrize("ncv", list(range(-1, 8)) + [4.5, "5"])
    def test_svds_input_validation_ncv_1(self, ncv):
        rng = np.random.default_rng(0)
        A = rng.random((6, 7))
        k = 3
        if ncv in {4, 5}:
            u, s, vh = svds(A, k=k, ncv=ncv, solver=self.solver)
        # partial decomposition, so don't check that u@diag(s)@vh=A;
        # do check that scipy.sparse.linalg.svds ~ scipy.linalg.svd
            _check_svds(A, k, u, s, vh)
        else:
            message = ("`ncv` must be an integer satisfying")
            with pytest.raises(ValueError, match=message):
                svds(A, k=k, ncv=ncv, solver=self.solver)

    def test_svds_input_validation_ncv_2(self):
        # I think the stack trace is reasonable when `ncv` can't be converted
        # to an int.
        message = "int() argument must be a"
        with pytest.raises(TypeError, match=re.escape(message)):
            svds(np.eye(10), ncv=[], solver=self.solver)

        message = "invalid literal for int()"
        with pytest.raises(ValueError, match=message):
            svds(np.eye(10), ncv="hi", solver=self.solver)


    # I can't see a robust relationship between `ncv` and relevant outputs
    # (e.g. accuracy, time), so no test of the parameter.

class Test_SVDS_LOBPCG(SVDSCommonTests):

    def setup_method(self):
        self.solver = 'lobpcg'

    def test_svd_random_state_3(self):
        pytest.xfail("LOBPCG is having trouble with accuracy.")

class Test_SVDS_PROPACK(SVDSCommonTests):

    def setup_method(self):
        self.solver = 'propack'
