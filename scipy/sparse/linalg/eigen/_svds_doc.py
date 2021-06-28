
def _svds_arpack_doc(A, k=6, ncv=None, tol=0, which='LM', v0=None,
                     maxiter=None, return_singular_vectors=True,
                     solver='arpack', random_state=None):
    """
    Partial singular value decomposition of a sparse matrix using ARPACK.

    Compute the largest or smallest `k` singular values and corresponding
    singular vectors of a sparse matrix `A`. The order in which the singular
    values are returned is not guaranteed.

    In the descriptions below, let ``M, N = A.shape``.

    Parameters
    ----------
    A : sparse matrix or LinearOperator
        Matrix to decompose.
    k : int, default: 6
        Number of singular values and singular vectors to compute.
        Must satisfy ``1 <= k <= min(M, N) - 1``.
    ncv : int, optional
        The number of Lanczos vectors generated.
        The default is ``min(n, max(2*k + 1, 20))``.
        If specified, must satistify ``k + 1 < ncv < min(M, N)``; ``ncv > 2*k``
        is recommended.
    tol : float, optional
        Tolerance for singular values. Zero (default) means machine precision.
    which : {'LM', 'SM'}
        Which `k` singular values to find: either the largest magnitude ('LM')
        or smallest magnitude ('SM') singular values.
    v0 : ndarray, optional
        The starting vector for iteration:
        an (approximate) left singular vector if ``N > M`` and a right singular
        vector otherwise. Must be of length ``min(M, N)``.
        Default: random
    maxiter : int, optional
        Maximum number of Arnoldi update iterations allowed;
        default is ``min(M, N) * 10``.
    return_singular_vectors : bool or str, default: True
        Singular values are always computed and returned; this parameter
        controls the computation and return of singular vectors.

        - ``True``: return singular vectors.
        - ``False``: do not return singular vectors.
        - ``"u"``: only return the left singular values, without computing the
          right singular vectors (if ``N > M``).
        - ``"vh"``: only return the right singular values, without computing
          the left singular vectors (if ``N <= M``).

    solver : str, optional
            This is the solver-specific documentation for ``solver='arpack'``.
            :ref:`'lobpcg' <sparse.linalg.svds-lobpcg>` and
            :ref:`'propack' <sparse.linalg.svds-propack>`
            are also supported.
    random_state : {None, int, `numpy.random.Generator`,
                    `numpy.random.RandomState`}, optional
        Pseudorandom number generator state used to generate resamples.

        If `seed` is ``None`` (or `np.random`), the `numpy.random.RandomState`
        singleton is used.
        If `seed` is an int, a new ``RandomState`` instance is used,
        seeded with `seed`.
        If `seed` is already a ``Generator`` or ``RandomState`` instance then
        that instance is used.

    Returns
    -------
    u : ndarray, shape=(M, k)
        Unitary matrix having left singular vectors as columns.
        If `return_singular_vectors` is ``"vh"``, this variable is not
        computed, and ``None`` is returned instead.
    s : ndarray, shape=(k,)
        The singular values.
    vh : ndarray, shape=(k, N)
        Unitary matrix having right singular vectors as rows.
        If `return_singular_vectors` is ``"u"``, this variable is not computed,
        and ``None`` is returned instead.

    Notes
    -----
    This is a naive implementation using ARPACK as an eigensolver
    on ``A.conj().T @ A`` or ``A @ A.conj().T``, depending on which one is more
    efficient.

    Examples
    --------
    Construct a matrix ``A`` from singular values and vectors.

    >>> from scipy.stats import ortho_group
    >>> from scipy.sparse import csc_matrix, diags
    >>> from scipy.sparse.linalg import svds
    >>> rng = np.random.default_rng()
    >>> orthogonal = csc_matrix(ortho_group.rvs(10, random_state=rng))
    >>> s = [0.0001, 0.001, 3, 4, 5]  # singular values
    >>> u = orthogonal[:, :5]         # left singular vectors
    >>> vT = orthogonal[:, 5:].T      # right singular vectors
    >>> A = u @ diags(s) @ vT

    With only three singular values/vectors, the SVD approximates the original
    matrix.

    >>> u2, s2, vT2 = svds(A, k=3, solver='arpack')
    >>> A2 = u2 @ np.diag(s2) @ vT2
    >>> np.allclose(A2, A.todense(), atol=1e-3)
    True

    With all five singular values/vectors, we can reproduce the original
    matrix.

    >>> u3, s3, vT3 = svds(A, k=5, solver='arpack')
    >>> A3 = u3 @ np.diag(s3) @ vT3
    >>> np.allclose(A3, A.todense())
    True

    The singular values match the expected singular values, and the singular
    values are as expected up to a difference in sign. Consequently, the
    returned arrays of singular vectors must also be orthogonal.

    >>> (np.allclose(s3, s) and
    ...  np.allclose(np.abs(u3), np.abs(u.todense())) and
    ...  np.allclose(np.abs(vT3), np.abs(vT.todense())))
    True
    """
    pass


def _svds_lobpcg_doc(A, k=6, ncv=None, tol=0, which='LM', v0=None,
                     maxiter=None, return_singular_vectors=True,
                     solver='lobpcg', random_state=None):
    """
    Partial singular value decomposition of a sparse matrix using LOBPCG.

    Compute the largest or smallest `k` singular values and corresponding
    singular vectors of a sparse matrix `A`. The order in which the singular
    values are returned is not guaranteed.

    In the descriptions below, let ``M, N = A.shape``.

    Parameters
    ----------
    A : sparse matrix or LinearOperator
        Matrix to decompose.
    k : int, default: 6
        Number of singular values and singular vectors to compute.
        Must satisfy ``1 <= k <= min(M, N) - 1``.
    ncv : int, optional
        Ignored.
    tol : float, optional
        Tolerance for singular values. Zero (default) means machine precision.
    which : {'LM', 'SM'}
        Which `k` singular values to find: either the largest magnitude ('LM')
        or smallest magnitude ('SM') singular values.
    v0 : ndarray, optional
        If `k` is 1, the starting vector for iteration:
        an (approximate) left singular vector if ``N > M`` and a right singular
        vector otherwise. Must be of length ``min(M, N)``.
        Ignored otherwise.
        Default: random
    maxiter : int, default: 20
        Maximum number of iterations.
    return_singular_vectors : bool or str, default: True
        Singular values are always computed and returned; this parameter
        controls the computation and return of singular vectors.

        - ``True``: return singular vectors.
        - ``False``: do not return singular vectors.
        - ``"u"``: only return the left singular values, without computing the
          right singular vectors (if ``N > M``).
        - ``"vh"``: only return the right singular values, without computing
          the left singular vectors (if ``N <= M``).

    solver : str, optional
            This is the solver-specific documentation for ``solver='lobpcg'``.
            :ref:`'arpack' <sparse.linalg.svds-arpack>` and
            :ref:`'propack' <sparse.linalg.svds-propack>`
            are also supported.
    random_state : {None, int, `numpy.random.Generator`,
                    `numpy.random.RandomState`}, optional
        Pseudorandom number generator state used to generate resamples.

        If `seed` is ``None`` (or `np.random`), the `numpy.random.RandomState`
        singleton is used.
        If `seed` is an int, a new ``RandomState`` instance is used,
        seeded with `seed`.
        If `seed` is already a ``Generator`` or ``RandomState`` instance then
        that instance is used.

    Returns
    -------
    u : ndarray, shape=(M, k)
        Unitary matrix having left singular vectors as columns.
        If `return_singular_vectors` is ``"vh"``, this variable is not
        computed, and ``None`` is returned instead.
    s : ndarray, shape=(k,)
        The singular values.
    vh : ndarray, shape=(k, N)
        Unitary matrix having right singular vectors as rows.
        If `return_singular_vectors` is ``"u"``, this variable is not computed,
        and ``None`` is returned instead.

    Notes
    -----
    This is a naive implementation using LOBPCG as an eigensolver
    on ``A.conj().T @ A`` or ``A @ A.conj().T``, depending on which one is more
    efficient.

    Examples
    --------
    Construct a matrix ``A`` from singular values and vectors.

    >>> from scipy.stats import ortho_group
    >>> from scipy.sparse import csc_matrix, diags
    >>> from scipy.sparse.linalg import svds
    >>> rng = np.random.default_rng()
    >>> orthogonal = csc_matrix(ortho_group.rvs(10, random_state=rng))
    >>> s = [0.0001, 0.001, 3, 4, 5]  # singular values
    >>> u = orthogonal[:, :5]         # left singular vectors
    >>> vT = orthogonal[:, 5:].T      # right singular vectors
    >>> A = u @ diags(s) @ vT

    With only three singular values/vectors, the SVD approximates the original
    matrix.

    >>> u2, s2, vT2 = svds(A, k=3, solver='lobpcg')
    >>> A2 = u2 @ np.diag(s2) @ vT2
    >>> np.allclose(A2, A.todense(), atol=1e-3)
    True

    With all five singular values/vectors, we can reproduce the original
    matrix.

    >>> u3, s3, vT3 = svds(A, k=5, solver='lobpcg')
    >>> A3 = u3 @ np.diag(s3) @ vT3
    >>> np.allclose(A3, A.todense())
    True

    The singular values match the expected singular values, and the singular
    values are as expected up to a difference in sign. Consequently, the
    returned arrays of singular vectors must also be orthogonal.

    >>> (np.allclose(s3, s) and
    ...  np.allclose(np.abs(u3), np.abs(u.todense())) and
    ...  np.allclose(np.abs(vT3), np.abs(vT.todense())))
    True
    """
    pass


def _svds_propack_doc(A, k=6, ncv=None, tol=0, which='LM', v0=None,
                     maxiter=None, return_singular_vectors=True,
                     solver='propack', random_state=None):
    """
    Partial singular value decomposition of a sparse matrix using PROPACK.

    Compute the largest or smallest `k` singular values and corresponding
    singular vectors of a sparse matrix `A`. The order in which the singular
    values are returned is not guaranteed.

    In the descriptions below, let ``M, N = A.shape``.

    Parameters
    ----------
    A : sparse matrix or LinearOperator
        Matrix to decompose. If `A` is a ``LinearOperator``
        object, it must define both ``matvec`` and ``rmatvec`` methods.
    k : int, default: 6
        Number of singular values and singular vectors to compute.
        Must satisfy ``1 <= k <= min(M, N)``.
    ncv : int, optional
        Ignored.
    tol : float, optional
        The desired relative accuracy for computed singular values.
        Zero (default) means machine precision.
    which : {'LM', 'SM'}
        Which `k` singular values to find: either the largest magnitude ('LM')
        or smallest magnitude ('SM') singular values. Note that choosing
        ``which='SM'`` will force the ``irl`` option to be set ``True``.
    v0 : ndarray, optional
        Starting vector for iterations: must be of length ``A.shape[0]``.
        If not specified, PROPACK will generate a starting vector.
    maxiter : int, optional
        Maximum number of iterations / maximal dimension of the Krylov
        subspace. Default is ``5 * k``.
    return_singular_vectors : bool or str, default: True
        Singular values are always computed and returned; this parameter
        controls the computation and return of singular vectors.

        - ``True``: return singular vectors.
        - ``False``: do not return singular vectors.
        - ``"u"``: only return the left singular values, without computing the
          right singular vectors (if ``N > M``).
        - ``"vh"``: only return the right singular values, without computing
          the left singular vectors (if ``N <= M``).

    solver : str, optional
            This is the solver-specific documentation for ``solver='propack'``.
            :ref:`'arpack' <sparse.linalg.svds-arpack>` and
            :ref:`'lobpcg' <sparse.linalg.svds-lobpcg>`
            are also supported.
    random_state : {None, int, `numpy.random.Generator`,
                    `numpy.random.RandomState`}, optional
        Pseudorandom number generator state used to generate resamples.

        If `seed` is ``None`` (or `np.random`), the `numpy.random.RandomState`
        singleton is used.
        If `seed` is an int, a new ``RandomState`` instance is used,
        seeded with `seed`.
        If `seed` is already a ``Generator`` or ``RandomState`` instance then
        that instance is used.

    Returns
    -------
    u : ndarray, shape=(M, k)
        Unitary matrix having left singular vectors as columns.
        If `return_singular_vectors` is ``"vh"``, this variable is not
        computed, and ``None`` is returned instead.
    s : ndarray, shape=(k,)
        The singular values.
    vh : ndarray, shape=(k, N)
        Unitary matrix having right singular vectors as rows.
        If `return_singular_vectors` is ``"u"``, this variable is not computed,
        and ``None`` is returned instead.

    Notes
    -----
    This is an interface to the Fortran library PROPACK [1]_.

    References
    ----------

    .. [1] Larsen, Rasmus Munk. "PROPACK-Software for large and sparse SVD
       calculations." Available online. URL
       http://sun. stanford. edu/rmunk/PROPACK (2004): 2008-2009.

    Examples
    --------
    Construct a matrix ``A`` from singular values and vectors.

    >>> from scipy.stats import ortho_group
    >>> from scipy.sparse import csc_matrix, diags
    >>> from scipy.sparse.linalg import svds
    >>> rng = np.random.default_rng()
    >>> orthogonal = csc_matrix(ortho_group.rvs(10, random_state=rng))
    >>> s = [0.0001, 0.001, 3, 4, 5]  # singular values
    >>> u = orthogonal[:, :5]         # left singular vectors
    >>> vT = orthogonal[:, 5:].T      # right singular vectors
    >>> A = u @ diags(s) @ vT

    With only three singular values/vectors, the SVD approximates the original
    matrix.

    >>> u2, s2, vT2 = svds(A, k=3, solver='propack')
    >>> A2 = u2 @ np.diag(s2) @ vT2
    >>> np.allclose(A2, A.todense(), atol=1e-3)
    True

    With all five singular values/vectors, we can reproduce the original
    matrix.

    >>> u3, s3, vT3 = svds(A, k=5, solver='propack')
    >>> A3 = u3 @ np.diag(s3) @ vT3
    >>> np.allclose(A3, A.todense())
    True

    The singular values match the expected singular values, and the singular
    values are as expected up to a difference in sign. Consequently, the
    returned arrays of singular vectors must also be orthogonal.

    >>> (np.allclose(s3, s) and
    ...  np.allclose(np.abs(u3), np.abs(u.todense())) and
    ...  np.allclose(np.abs(vT3), np.abs(vT.todense())))
    True
    """
    pass
