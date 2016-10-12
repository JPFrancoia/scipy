import numpy as np
from numpy.testing import (run_module_suite, TestCase, assert_equal,
        assert_allclose, assert_raises, assert_)
from numpy.testing.decorators import skipif, knownfailureif

from scipy.interpolate import (BSpline, splev, splrep, BPoly, PPoly,
        make_interp_spline, make_lsq_spline, _bspl)
from scipy.interpolate._bsplines import _not_a_knot, _augknt
import scipy.linalg as sl


class TestBSpline(TestCase):

    def test_ctor(self):
        # knots should be an ordered 1D array of finite real numbers
        assert_raises((TypeError, ValueError), BSpline,
                **dict(t=[1, 1.j], c=[1.], k=0))
        assert_raises(ValueError, BSpline, **dict(t=[1, np.nan], c=[1.], k=0))
        assert_raises(ValueError, BSpline, **dict(t=[1, np.inf], c=[1.], k=0))
        assert_raises(ValueError, BSpline, **dict(t=[1, -1], c=[1.], k=0))
        assert_raises(ValueError, BSpline, **dict(t=[[1], [1]], c=[1.], k=0))

        # for n+k+1 knots and degree k need at least n coefficients
        assert_raises(ValueError, BSpline, **dict(t=[0, 1, 2], c=[1], k=0))
        assert_raises(ValueError, BSpline,
                **dict(t=[0, 1, 2, 3, 4], c=[1., 1.], k=2))

        # non-integer orders
        assert_raises(ValueError, BSpline,
                **dict(t=[0., 0., 1., 2., 3., 4.], c=[1., 1., 1.], k="cubic"))
        assert_raises(ValueError, BSpline,
                **dict(t=[0., 0., 1., 2., 3., 4.], c=[1., 1., 1.], k=2.5))

        # basic inteval cannot have measure zero (here: [1..1])
        assert_raises(ValueError, BSpline,
                **dict(t=[0., 0, 1, 1, 2, 3], c=[1., 1, 1], k=2))

        # tck vs self.tck
        b, t, c, k = _make_random_spline()
        assert_allclose(t, b.t)
        assert_allclose(c, b.c)
        assert_equal(k, b.k)

    def test_tck(self):
        b, t, c, k = _make_random_spline()
        tck = b.tck
        assert_allclose(t, tck[0], atol=1e-15, rtol=1e-15)
        assert_allclose(c, tck[1], atol=1e-15, rtol=1e-15)
        assert_equal(k, tck[2])

        # b.tck is read-only
        try:
            b.tck = 'foo'
        except AttributeError:
            pass
        except:
            raise AssertionError("AttributeError not raised.")

    def test_degree_0(self):
        xx = np.linspace(0, 1, 10)

        b = BSpline(t=[0, 1], c=[3.], k=0)
        assert_allclose(b(xx), 3)

        b = BSpline(t=[0, 0.35, 1], c=[3, 4], k=0)
        assert_allclose(b(xx), np.where(xx < 0.35, 3, 4))

    def test_degree_1(self):
        t = [0, 1, 2, 3, 4]
        c = [1, 2, 3]
        k = 1
        b = BSpline(t, c, k)

        x = np.linspace(1, 3, 50)
        assert_allclose(c[0]*B_012(x) + c[1]*B_012(x-1) + c[2]*B_012(x-2),
                        b(x), atol=1e-14)
        assert_allclose(splev(x, (t, c, k)), b(x), atol=1e-14)

    def test_bernstein(self):
        # a special knot vector: Bernstein polynomials
        k = 3
        t = np.asarray([0]*(k+1) + [1]*(k+1))
        c = np.asarray([1., 2., 3., 4.])
        bp = BPoly(c.reshape(-1, 1), [0, 1])
        bspl = BSpline(t, c, k)

        xx = np.linspace(-1., 2., 10)
        assert_allclose(bp(xx, extrapolate=True),
                        bspl(xx, extrapolate=True), atol=1e-14)
        assert_allclose(splev(xx, (t, c, k)),
                        bspl(xx), atol=1e-14)

    def test_rndm_naive_eval(self):
        # test random coefficient spline *on the base interval*,
        # t[k] <= x < t[-k-1]
        b, t, c, k = _make_random_spline()
        xx = np.linspace(t[k], t[-k-1], 50)
        y_b = b(xx)

        y_n = [_naive_eval(x, t, c, k) for x in xx]
        assert_allclose(y_b, y_n, atol=1e-14)

        y_n2 = [_naive_eval_2(x, t, c, k) for x in xx]
        assert_allclose(y_b, y_n2, atol=1e-14)

    def test_rndm_splev(self):
        b, t, c, k = _make_random_spline()
        xx = np.linspace(t[k], t[-k-1], 50)
        assert_allclose(b(xx), splev(xx, (t, c, k)), atol=1e-14)

    def test_rndm_splrep(self):
        np.random.seed(1234)
        x = np.sort(np.random.random(20))
        y = np.random.random(20)

        tck = splrep(x, y)
        b = BSpline(*tck)

        t, k = b.t, b.k
        xx = np.linspace(t[k], t[-k-1], 80)
        assert_allclose(b(xx), splev(xx, tck), atol=1e-14)

    def test_rndm_unity(self):
        b, t, c, k = _make_random_spline()
        b.c = np.ones_like(b.c)
        xx = np.linspace(t[k], t[-k-1], 100)
        assert_allclose(b(xx), 1.)

    def test_vectorization(self):
        n, k = 22, 3
        t = np.sort(np.random.random(n))
        c = np.random.random(size=(n, 6, 7))
        b = BSpline(t, c, k)
        tm, tp = t[k], t[-k-1]
        xx = tm + (tp - tm) * np.random.random((3, 4, 5))
        assert_equal(b(xx).shape, (3, 4, 5, 6, 7))

    def test_len_c(self):
        # for n+k+1 knots, only first n coefs are used.
        # and BTW this is consistent with FITPACK
        n, k = 33, 3
        t = np.sort(np.random.random(n+k+1))
        c = np.random.random(n)

        # pad coefficients with random garbage
        c_pad = np.r_[c, np.random.random(k+1)]

        b, b_pad = BSpline(t, c, k), BSpline(t, c_pad, k)

        dt = t[-1] - t[0]
        xx = np.linspace(t[0] - dt, t[-1] + dt, 50)
        assert_allclose(b(xx), b_pad(xx), atol=1e-14)
        assert_allclose(b(xx), splev(xx, (t, c, k)), atol=1e-14)
        assert_allclose(b(xx), splev(xx, (t, c_pad, k)), atol=1e-14)

    def test_endpoints(self):
        # base interval is closed
        b, t, c, k = _make_random_spline()
        tm, tp = t[k], t[-k-1]
        for extrap in (True, False):
            assert_allclose(b([tm, tp], extrap),
                            b([tm + 1e-10, tp - 1e-10], extrap), atol=1e-9)

    def test_continuity(self):
        # assert continuity at internal knots
        b, t, c, k = _make_random_spline()
        assert_allclose(b(t[k+1:-k-1] - 1e-10), b(t[k+1:-k-1] + 1e-10),
                atol=1e-9)

    def test_extrap(self):
        b, t, c, k = _make_random_spline()
        dt = t[-1] - t[0]
        xx = np.linspace(t[k] - dt, t[-k-1] + dt, 50)
        mask = (t[k] < xx) & (xx < t[-k-1])

        # extrap has no effect within the base interval
        assert_allclose(b(xx[mask], extrapolate=True),
                        b(xx[mask], extrapolate=False))

        # extrapolated values agree with FITPACK
        assert_allclose(b(xx, extrapolate=True),
                splev(xx, (t, c, k), ext=0))

    def test_default_extrap(self):
        # BSpline defaults to extrapolate=True
        b, t, c, k = _make_random_spline()
        xx = [t[0] - 1, t[-1] + 1]
        yy = b(xx)
        assert_(not np.all(np.isnan(yy)))

    def test_ppoly(self):
        b, t, c, k = _make_random_spline()
        pp = PPoly.from_spline((t, c, k))

        xx = np.linspace(t[k], t[-k], 100)
        assert_allclose(b(xx), pp(xx), atol=1e-14, rtol=1e-14)

    def test_derivative_rndm(self):
        b, t, c, k = _make_random_spline()
        xx = np.linspace(t[0], t[-1], 50)
        xx = np.r_[xx, t]

        for der in range(1, k+1):
            yd = splev(xx, (t, c, k), der=der)
            assert_allclose(yd, b(xx, nu=der), atol=1e-14)

        # higher derivatives all vanish
        assert_allclose(b(xx, nu=k+1), 0)

    def test_derivative_jumps(self):
        # example from de Boor, Chap IX, example (24)
        # NB: knots augmented & corresp coefs are zeroed out
        # in agreement with the convention (29)
        k = 2
        t = [-1, -1, 0, 1, 1, 3, 4, 6, 6, 6, 7, 7]
        np.random.seed(1234)
        c = np.r_[0, 0, np.random.random(5), 0, 0]
        b = BSpline(t, c, k)

        # b is continuous at x != 6 (triple knot)
        x = np.asarray([1, 3, 4, 6])
        assert_allclose(b(x[x != 6] - 1e-10),
                        b(x[x != 6] + 1e-10))
        assert_(not np.allclose(b(6.-1e-10), b(6+1e-10)))

        # 1st derivative jumps at double knots, 1 & 6:
        x0 = np.asarray([3, 4])
        assert_allclose(b(x0 - 1e-10, nu=1),
                        b(x0 + 1e-10, nu=1))
        x1 = np.asarray([1, 6])
        assert_(not np.all(np.allclose(b(x1 - 1e-10, nu=1),
                                       b(x1 + 1e-10, nu=1))))

        # 2nd derivative is not guaranteed to be continuous either
        assert_(not np.all(np.allclose(b(x - 1e-10, nu=2),
                                       b(x + 1e-10, nu=2))))

    def test_basis_element_quadratic(self):
        xx = np.linspace(-1, 4, 20)
        b = BSpline.basis_element(t=[0, 1, 2, 3])
        assert_allclose(b(xx),
                        splev(xx, (b.t, b.c, b.k)), atol=1e-14)
        assert_allclose(b(xx),
                        B_0123(xx), atol=1e-14)

        b = BSpline.basis_element(t=[0, 1, 1, 2])
        xx = np.linspace(0, 2, 10)
        assert_allclose(b(xx),
                np.where(xx < 1, xx*xx, (2.-xx)**2), atol=1e-14)

    def test_basis_element_rndm(self):
        b, t, c, k = _make_random_spline()
        xx = np.linspace(t[k], t[-k-1], 20)
        assert_allclose(b(xx), _sum_basis_elements(xx, t, c, k), atol=1e-14)

    def test_cmplx(self):
        b, t, c, k = _make_random_spline()
        cc = c * (1. + 3.j)

        b = BSpline(t, cc, k)
        b_re = BSpline(t, b.c.real, k)
        b_im = BSpline(t, b.c.imag, k)

        xx = np.linspace(t[k], t[-k-1], 20)
        assert_allclose(b(xx).real, b_re(xx), atol=1e-14)
        assert_allclose(b(xx).imag, b_im(xx), atol=1e-14)

    def test_nan(self):
        # nan in, nan out.
        b = BSpline.basis_element([0, 1, 1, 2])
        assert_(np.isnan(b(np.nan)))

    def test_derivative_method(self):
        b, t, c, k = _make_random_spline(k=5)
        b0 = BSpline(t, c, k)
        xx = np.linspace(t[k], t[-k-1], 20)
        for j in range(1, k):
            b = b.derivative()
            assert_allclose(b0(xx, j), b(xx), atol=1e-12, rtol=1e-12)

    def test_antiderivative_method(self):
        b, t, c, k = _make_random_spline()
        xx = np.linspace(t[k], t[-k-1], 20)
        assert_allclose(b.antiderivative().derivative()(xx),
                        b(xx), atol=1e-14, rtol=1e-14)

        # repeat with n-D array for c
        c = np.c_[c, c, c]
        c = np.dstack((c, c))
        b = BSpline(t, c, k)
        assert_allclose(b.antiderivative().derivative()(xx),
                        b(xx), atol=1e-14, rtol=1e-14)

    def test_integral(self):
        b = BSpline.basis_element([0, 1, 2])  # x for x < 1 else 2 - x
        assert_allclose(b.integrate(0, 1), 0.5)
        assert_allclose(b.integrate(1, 0), -0.5)

        # extrapolate or zeros outside of [0, 2]; default is yes
        assert_allclose(b.integrate(-1, 1), 0)
        assert_allclose(b.integrate(-1, 1, extrapolate=True), 0)
        assert_allclose(b.integrate(-1, 1, extrapolate=False), 0.5)

    def test_subclassing(self):
        # classmethods should not decay to the base class
        class B(BSpline):
            pass

        b = B.basis_element([0, 1, 2, 2])
        assert_equal(b.__class__, B)
        assert_equal(b.derivative().__class__, B)
        assert_equal(b.antiderivative().__class__, B)

    ### Test the tuple interface: for backwards-compatible interoperability
    ### with spl* functions, a BSpline instance needs to behave as a
    ### tuple (t, c, k). Specifically, support unpacking and indexing/slicing.

    def test_unpacking(self):
        # BSpline object unpacks into a tck-tuple, if asked
        _, t, c, k = _make_random_spline()
        b = BSpline(t, c, k)
        tt, cc, kk = b
        assert_allclose(t, tt, atol=1e-15)
        assert_allclose(c, cc, atol=1e-15)
        assert_equal(k, kk)

        def wrong_unpacking(spl):
            t, = spl
        assert_raises(ValueError, wrong_unpacking, b)

    def test_indexing(self):
        b, t, c, k = _make_random_spline()
        assert_allclose(b[0], t, atol=1e-15)
        assert_allclose(b[1], c, atol=1e-15)
        assert_equal(b[2], k)

        assert_equal(b[-1], k)
        assert_allclose(b[-2], c, atol=1e-15)
        assert_allclose(b[-3], t, atol=1e-15)

        def wrong_index(idx):
            b[idx]
        assert_raises(IndexError, wrong_index, 3)
        assert_raises(IndexError, wrong_index, -4)

    def test_slicing(self):
        b, t, c, k = _make_random_spline()
        tck = (t, c, k)
        assert_equal(b[:], tck[:])
        assert_equal(b[1:], tck[1:])
        assert_equal(b[:-1], tck[:-1])
        assert_equal(b[1:9], tck[1:9])


def test_knots_multiplicity():
    # Take a spline w/ random coefficients, throw in knots of varying
    # multiplicity.

    def check_splev(b, j, der=0, atol=1e-14, rtol=1e-14):
        # check evaluations against FITPACK, incl extrapolations
        t, c, k = b.t, b.c, b.k
        x = np.unique(t)
        x = np.r_[t[0]-0.1, 0.5*(x[1:] + x[:1]), t[-1]+0.1]
        assert_allclose(splev(x, (t, c, k), der), b(x, der),
                atol=atol, rtol=rtol, err_msg='der = %s  k = %s' % (der, b.k))

    # test loop itself
    # [the index `j` is for interpreting the traceback in case of a failure]
    for k in [1, 2, 3, 4, 5]:
        b, t, c, k = _make_random_spline(k=k)
        for j, b1 in enumerate(_make_multiples(b)):
            yield check_splev, b1, j
            for der in range(1, k+1):
                yield check_splev, b1, j, der, 1e-12, 1e-12


### stolen from @pv, verbatim
def _naive_B(x, k, i, t):
    """
    Naive way to compute B-spline basis functions. Useful only for testing!
    computes B(x; t[i],..., t[i+k+1])
    """
    if k == 0:
        return 1.0 if t[i] <= x < t[i+1] else 0.0
    if t[i+k] == t[i]:
        c1 = 0.0
    else:
        c1 = (x - t[i])/(t[i+k] - t[i]) * _naive_B(x, k-1, i, t)
    if t[i+k+1] == t[i+1]:
        c2 = 0.0
    else:
        c2 = (t[i+k+1] - x)/(t[i+k+1] - t[i+1]) * _naive_B(x, k-1, i+1, t)
    return (c1 + c2)


### stolen from @pv, verbatim
def _naive_eval(x, t, c, k):
    """
    Naive B-spline evaluation. Useful only for testing!
    """
    if x == t[k]:
        i = k
    else:
        i = np.searchsorted(t, x) - 1
    assert t[i] <= x <= t[i+1]
    assert i >= k and i < len(t) - k
    return sum(c[i-j] * _naive_B(x, k, i-j, t) for j in range(0, k+1))


def _naive_eval_2(x, t, c, k):
    """Naive B-spline evaluation, another way."""
    n = len(t) - (k+1)
    assert n >= k+1
    assert len(c) >= n
    assert t[k] <= x <= t[n]
    return sum(c[i] * _naive_B(x, k, i, t) for i in range(n))


def _sum_basis_elements(x, t, c, k):
    n = len(t) - (k+1)
    assert n >= k+1
    assert len(c) >= n
    s = 0.
    for i in range(n):
        b = BSpline.basis_element(t[i:i+k+2], extrapolate=False)(x)
        s += c[i] * np.nan_to_num(b)   # zero out out-of-bounds elements
    return s


def B_012(x):
    """ A linear B-spline function B(x | 0, 1, 2)."""
    x = np.atleast_1d(x)
    return np.piecewise(x, [(x < 0) | (x > 2),
                            (x >= 0) & (x < 1),
                            (x >= 1) & (x <= 2)],
                           [lambda x: 0., lambda x: x, lambda x: 2.-x])


def B_0123(x, der=0):
    """A quadratic B-spline function B(x | 0, 1, 2, 3)."""
    x = np.atleast_1d(x)
    conds = [x < 1, (x > 1) & (x < 2), x > 2]
    if der == 0:
        funcs = [lambda x: x*x/2.,
                 lambda x: 3./4 - (x-3./2)**2,
                 lambda x: (3.-x)**2 / 2]
    elif der == 2:
        funcs = [lambda x: 1.,
                 lambda x: -2.,
                 lambda x: 1.]
    else:
        raise ValueError('never be here: der=%s' % der)
    pieces = np.piecewise(x, conds, funcs)
    return pieces


def _make_random_spline(n=35, k=3):
    np.random.seed(123)
    t = np.sort(np.random.random(n+k+1))
    c = np.random.random(n)
    return BSpline(t, c, k), t, c, k


def _make_multiples(b):
    """Increase knot multiplicity."""
    c, k = b.c, b.k

    t1 = b.t.copy()
    t1[17:19] = t1[17]
    t1[22] = t1[21]
    yield BSpline(t1, c, k)

    t1 = b.t.copy()
    t1[:k+1] = t1[0]
    yield BSpline(t1, c, k)

    t1 = b.t.copy()
    t1[-k-1:] = t1[-1]
    yield BSpline(t1, c, k)


class TestInterp(TestCase):
    #
    # Test basic ways of constructing interpolating splines.
    #
    xx = np.linspace(0., 2.*np.pi)
    yy = np.sin(xx)

    def test_order_0(self):
        b = make_interp_spline(self.xx, self.yy, k=0)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)

    def test_linear(self):
        b = make_interp_spline(self.xx, self.yy, k=1)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)

    def test_not_a_knot(self):
        for k in [3, 5]:
            b = make_interp_spline(self.xx, self.yy, k)
            assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)

    def test_quadratic_deriv(self):
        der = [(1, 8.)]  # order, value: f'(x) = 8.

        # derivative at right-hand edge
        b = make_interp_spline(self.xx, self.yy, k=2, deriv_r=der)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)
        assert_allclose(b(self.xx[-1], 1), der[0][1], atol=1e-14, rtol=1e-14)

        # derivative at left-hand edge
        b = make_interp_spline(self.xx, self.yy, k=2, deriv_l=der)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)
        assert_allclose(b(self.xx[0], 1), der[0][1], atol=1e-14, rtol=1e-14)

    def test_cubic_deriv(self):
        k = 3

        # first derivatives at left & right edges:
        der_l, der_r = [(1, 3.)], [(1, 4.)]
        b = make_interp_spline(self.xx, self.yy, k,
                               deriv_l=der_l, deriv_r=der_r)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)
        assert_allclose([b(self.xx[0], 1), b(self.xx[-1], 1)],
                        [der_l[0][1], der_r[0][1]], atol=1e-14, rtol=1e-14)

        # 'natural' cubic spline, zero out 2nd derivatives at the boundaries
        der_l, der_r = [(2, 0)], [(2, 0)]
        b = make_interp_spline(self.xx, self.yy, k,
                               deriv_l=der_l, deriv_r=der_r)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)

    def test_quintic_derivs(self):
        k, n = 5, 7
        x = np.arange(n).astype(np.float_)
        y = np.sin(x)
        der_l = [(1, -12.), (2, 1)]
        der_r = [(1, 8.), (2, 3.)]
        b = make_interp_spline(x, y, k=5, deriv_l=der_l, deriv_r=der_r)
        assert_allclose(b(x), y, atol=1e-14, rtol=1e-14)
        assert_allclose([b(x[0], 1), b(x[0], 2)],
                        [val for (nu, val) in der_l])
        assert_allclose([b(x[-1], 1), b(x[-1], 2)],
                        [val for (nu, val) in der_r])

    @knownfailureif(True, 'unstable')
    def test_cubic_deriv_unstable(self):
        # 1st and 2nd derivative at x[0], no derivative information at x[-1]
        # The problem is not that it fails [who would use this anyway],
        # the problem is that it fails *silently*, and I've no idea
        # how to detect this sort of instability.
        # In this particular case: it's OK for len(t) < 20, goes haywire
        # at larger `len(t)`.
        k = 3
        t = _augknt(self.xx, k)

        der_l = [(1, 3.), (2, 4.)]
        b = make_interp_spline(self.xx, self.yy, k, t, deriv_l=der_l)
        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)

    def test_knots_not_data_sites(self):
        # Knots need not coincide with the data sites.
        # use a quadratic spline, knots are at data averages,
        # two additional constraints are zero 2nd derivs at edges
        k, n = 2, 8
        t = np.r_[(self.xx[0],)*(k+1),
                  (self.xx[1:] + self.xx[:-1]) / 2.,
                  (self.xx[-1],)*(k+1)]
        b = make_interp_spline(self.xx, self.yy, k, t,
                               deriv_l=[(2, 0)], deriv_r=[(2, 0)])

        assert_allclose(b(self.xx), self.yy, atol=1e-14, rtol=1e-14)
        assert_allclose([b(self.xx[0], 2), b(self.xx[-1], 2)], [0., 0.],
                atol=1e-14)

    def test_complex(self):
        k = 3
        xx = self.xx
        yy = self.yy + 1.j*self.yy

        # first derivatives at left & right edges:
        der_l, der_r = [(1, 3.j)], [(1, 4.+2.j)]
        b = make_interp_spline(xx, yy, k,
                               deriv_l=der_l, deriv_r=der_r)
        assert_allclose(b(xx), yy, atol=1e-14, rtol=1e-14)
        assert_allclose([b(xx[0], 1), b(xx[-1], 1)],
                        [der_l[0][1], der_r[0][1]], atol=1e-14, rtol=1e-14)

    def test_int_xy(self):
        x = np.arange(10).astype(np.int_)
        y = np.arange(10).astype(np.int_)

        # cython chokes on "buffer type mismatch"
        make_interp_spline(x, y, k=1)

    def test_sliced_input(self):
        # cython code chokes on non C contiguous arrays
        xx = np.linspace(-1, 1, 100)

        x = xx[::5]
        y = xx[::5]

        make_interp_spline(x, y, k=1)

    def test_check_finite(self):
        # check_finite defaults to True; nans and such trigger a ValueError
        x = np.arange(10).astype(float)
        y = x**2

        for z in [np.nan, np.inf, -np.inf]:
            y[-1] = z
            assert_raises(ValueError, make_interp_spline, x, y)

    def test_multiple_rhs(self):
        yy = np.c_[np.sin(self.xx), np.cos(self.xx)]
        der_l = [(1, [1., 2.])]
        der_r = [(1, [3., 4.])]

        b = make_interp_spline(self.xx, yy, k=3,
                               deriv_l=der_l, deriv_r=der_r)
        assert_allclose(b(self.xx), yy, atol=1e-14, rtol=1e-14)
        assert_allclose(b(self.xx[0], 1), der_l[0][1], atol=1e-14, rtol=1e-14)
        assert_allclose(b(self.xx[-1], 1), der_r[0][1], atol=1e-14, rtol=1e-14)

    def test_shapes(self):
        np.random.seed(1234)
        k, n = 3, 22
        x = np.sort(np.random.random(size=n))
        y = np.random.random(size=(n, 5, 6, 7))

        b = make_interp_spline(x, y, k)
        assert_equal(b.c.shape, (n, 5, 6, 7))

        # now throw in some derivatives
        d_l = [(1, np.random.random((5, 6, 7)))]
        d_r = [(1, np.random.random((5, 6, 7)))]
        b = make_interp_spline(x, y, k, deriv_l=d_l, deriv_r=d_r)
        assert_equal(b.c.shape, (n + k - 1, 5, 6, 7))

    def test_full_matrix(self):
        np.random.seed(1234)
        k, n = 3, 7
        x = np.sort(np.random.random(size=n))
        y = np.random.random(size=n)
        t = _not_a_knot(x, k)

        b = make_interp_spline(x, y, k, t)
        cf = make_interp_full_matr(x, y, t, k)
        assert_allclose(b.c, cf, atol=1e-14, rtol=1e-14)


def make_interp_full_matr(x, y, t, k):
    """Assemble an spline order k with knots t to interpolate
    y(x) using full matrices.
    Not-a-knot BC only.

    This routine is here for testing only (even though it's functional).
    """
    assert x.size == y.size
    assert t.size == x.size + k + 1
    n = x.size

    A = np.zeros((n, n), dtype=np.float_)

    for j in range(n):
        xval = x[j]
        if xval == t[k]:
            left = k
        else:
            left = np.searchsorted(t, xval) - 1

        # fill a row
        bb = _bspl.evaluate_all_bspl(t, k, xval, left)
        A[j, left-k:left+1] = bb

    c = sl.solve(A, y)
    return c


### XXX: 'periodic' interp spline using full matrices
def make_interp_per_full_matr(x, y, t, k):
    x, y, t = map(np.asarray, (x, y, t))

    n = x.size
    nt = t.size - k - 1

    # have `n` conditions for `nt` coefficients; need nt-n derivatives
    assert nt - n == k - 1

    # LHS: the collocation matrix + derivatives at edges
    A = np.zeros((nt, nt), dtype=np.float_)

    # derivatives at x[0]:
    offset = 0

    if x[0] == t[k]:
        left = k
    else:
        left = np.searchsorted(t, x[0]) - 1

    if x[-1] == t[k]:
        left2 = k
    else:
        left2 = np.searchsorted(t, x[-1]) - 1

    for i in range(k-1):
        bb = _bspl.evaluate_all_bspl(t, k, x[0], left, nu=i+1)
        A[i, left-k:left+1] = bb
        bb = _bspl.evaluate_all_bspl(t, k, x[-1], left2, nu=i+1)
        A[i, left2-k:left2+1] = -bb
        offset += 1

    # RHS
    y = np.r_[[0]*(k-1), y]

    # collocation matrix
    for j in range(n):
        xval = x[j]
        # find interval
        if xval == t[k]:
            left = k
        else:
            left = np.searchsorted(t, xval) - 1

        # fill a row
        bb = _bspl.evaluate_all_bspl(t, k, xval, left)
        A[j + offset, left-k:left+1] = bb

    c = sl.solve(A, y)
    return c


def make_lsq_full_matrix(x, y, t, k=3):
    """Make the least-square spline, full matrices."""
    x, y, t = map(np.asarray, (x, y, t))
    m = x.size
    n = t.size - k - 1

    A = np.zeros((m, n), dtype=np.float_)

    i = 0
    for j in range(m):
        xval = x[j]
        # find interval
        if xval == t[k]:
            left = k
        else:
            left = np.searchsorted(t, xval) - 1

        # fill a row
        bb = _bspl.evaluate_all_bspl(t, k, xval, left)
        A[j, left-k:left+1] = bb

    # have observation matrix, can solve the LSQ problem
    B = np.dot(A.T, A)
    Y = np.dot(A.T, y)
    c = sl.solve(B, Y)

    return c, (A, Y)


class TestLSQ(TestCase):
    #
    # Test make_lsq_spline
    #
    np.random.seed(1234)
    n, k = 13, 3
    x = np.sort(np.random.random(n))
    y = np.random.random(n)
    t = _augknt(np.linspace(x[0], x[-1], 7), k)

    def test_lstsq(self):
        # check LSQ construction vs a full matrix version
        x, y, t, k = self.x, self.y, self.t, self.k

        c0, AY = make_lsq_full_matrix(x, y, t, k)
        b = make_lsq_spline(x, y, t, k)

        assert_allclose(b.c, c0)
        assert_equal(b.c.shape, (t.size - k - 1,))

        # also check against numpy.lstsq
        aa, yy = AY
        c1, _, _, _ = np.linalg.lstsq(aa, y)
        assert_allclose(b.c, c1)

    def test_weights(self):
        # weights = 1 is same as None
        x, y, t, k = self.x, self.y, self.t, self.k
        w = np.ones_like(x)

        b = make_lsq_spline(x, y, t, k)
        b_w = make_lsq_spline(x, y, t, k, w=w)

        assert_equal(b.t, b_w.t)
        assert_equal(b.c, b_w.c)
        assert_equal(b.k, b_w.k)

    def test_multiple_rhs(self):
        x, t, k, n = self.x, self.t, self.k, self.n
        y = np.random.random(size=(n, 5, 6, 7))

        b = make_lsq_spline(x, y, t, k)
        assert_equal(b.c.shape, (t.size-k-1, 5, 6, 7))

    def test_complex(self):
        # cmplx-valued `y`
        x, t, k = self.x, self.t, self.k
        yc = self.y * (1. + 2.j)

        b = make_lsq_spline(x, yc, t, k)
        b_re = make_lsq_spline(x, yc.real, t, k)
        b_im = make_lsq_spline(x, yc.imag, t, k)

        assert_allclose(b(x), b_re(x) + 1.j*b_im(x), atol=1e-15, rtol=1e-15)

    def test_int_xy(self):
        x = np.arange(10).astype(np.int_)
        y = np.arange(10).astype(np.int_)
        t = _augknt(x, k=1)
        # cython chokes on "buffer type mismatch"
        make_lsq_spline(x, y, t, k=1)

    def test_sliced_input(self):
        # cython code chokes on non C contiguous arrays
        xx = np.linspace(-1, 1, 100)

        x = xx[::3]
        y = xx[::3]
        t = _augknt(x, 1)
        make_lsq_spline(x, y, t, k=1)

    def test_checkfinite(self):
        # check_finite defaults to True; nans and such trigger a ValueError
        x = np.arange(12).astype(float)
        y = x**2
        t = _augknt(x, 3)

        for z in [np.nan, np.inf, -np.inf]:
            y[-1] = z
            assert_raises(ValueError, make_lsq_spline, x, y, t)


if __name__ == "__main__":
    run_module_suite()
