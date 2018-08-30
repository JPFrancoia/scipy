from . cimport c_zeros


# callback function wrapper that extracts function, args from params struct
cdef double scipy_newton_functions_func(double x, void *params):
    cdef scipy_newton_parameters *myparams = <scipy_newton_parameters *> params
    cdef void* args = myparams.args
    cdef callback_type func = myparams.function

    return func(x, args)  # callback_type takes a double and a struct


# callback function wrapper that extracts function, args from params struct
cdef double scipy_newton_functions_fprime(double x, void *params):
    cdef scipy_newton_parameters *myparams = <scipy_newton_parameters *> params
    cdef void* args = myparams.args
    cdef callback_type fprime = myparams.function_derivative

    return fprime(x, args)  # callback_type takes a double and a struct


# callback function wrapper that extracts function, args from params struct
cdef double scipy_newton_functions_fprime2(double x, void *params):
    cdef scipy_newton_parameters *myparams = <scipy_newton_parameters *> params
    cdef void* args = myparams.args
    cdef callback_type fprime2 = myparams.function_second_derivative

    return fprime2(x, args)  # callback_type takes a double and a struct


# Newton-Raphson method
cdef double newton(callback_type func, double p0, callback_type fprime, void *args, double tol, int maxiter, scipy_newton_parameters *full_output):
    cdef double root
    cdef scipy_newton_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = func
    myparams.function_derivative = fprime
    root = c_zeros.newton(scipy_newton_functions_func, p0, scipy_newton_functions_fprime, <c_zeros.default_parameters *> &myparams, tol, maxiter)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root


# Secant method
cdef double secant(callback_type func, double p0, void *args, double tol, int maxiter, scipy_newton_parameters *full_output):
    cdef double root
    cdef scipy_newton_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = func
    root = c_zeros.secant(scipy_newton_functions_func, p0, <c_zeros.default_parameters *> &myparams, tol, maxiter)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root


# Halley's method
cdef double halley(callback_type func, double p0, callback_type fprime, void *args, double tol, int maxiter, callback_type fprime2, scipy_newton_parameters *full_output):
    cdef double root
    cdef scipy_newton_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = func
    myparams.function_derivative = fprime
    myparams.function_second_derivative = fprime2
    root = c_zeros.halley(scipy_newton_functions_func, p0, scipy_newton_functions_fprime, <c_zeros.default_parameters *> &myparams, tol, maxiter, scipy_newton_functions_fprime2)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root


# callback function wrapper that extracts function, args from params struct
cdef double scipy_zeros_functions_func(double x, void *params):
    cdef scipy_zeros_parameters *myparams = <scipy_zeros_parameters *> params
    cdef void* args = myparams.args
    cdef callback_type f = myparams.function

    return f(x, args)  # callback_type takes a double and a struct


# cythonized way to call scalar bisect
cdef double bisect(callback_type f, double xa, double xb, void *args, double xtol, double rtol, int iter, scipy_zeros_parameters *full_output):
    cdef double root
    cdef scipy_zeros_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = f
    root = c_zeros.bisect(scipy_zeros_functions_func, xa, xb, xtol, rtol, iter, <c_zeros.default_parameters *> &myparams)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root


# cythonized way to call scalar ridder
cdef double ridder(callback_type f, double xa, double xb, void *args, double xtol, double rtol, int iter, scipy_zeros_parameters *full_output):
    cdef double root
    cdef scipy_zeros_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = f
    root = c_zeros.ridder(scipy_zeros_functions_func, xa, xb, xtol, rtol, iter, <c_zeros.default_parameters *> &myparams)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root


# cythonized way to call scalar brenth
cdef double brenth(callback_type f, double xa, double xb, void *args, double xtol, double rtol, int iter, scipy_zeros_parameters *full_output):
    cdef double root
    cdef scipy_zeros_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = f
    root = c_zeros.brenth(scipy_zeros_functions_func, xa, xb, xtol, rtol, iter, <c_zeros.default_parameters *> &myparams)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root


# cythonized way to call scalar brentq
cdef double brentq(callback_type f, double xa, double xb, void *args, double xtol, double rtol, int iter, scipy_zeros_parameters *full_output):
    cdef double root
    cdef scipy_zeros_parameters myparams
    # create params struct
    myparams.args = args
    myparams.function = f
    root = c_zeros.brentq(scipy_zeros_functions_func, xa, xb, xtol, rtol, iter, <c_zeros.default_parameters *> &myparams)
    if full_output is not NULL:
        full_output.funcalls = myparams.funcalls
        full_output.iterations = myparams.iterations
        full_output.error_num = myparams.error_num
    return root
