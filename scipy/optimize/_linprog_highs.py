"""HiGHS Linear Optimization Methods

Interface to HiGHS linear optimization software.
https://www.maths.ed.ac.uk/hall/HiGHS/

.. versionadded:: 1.5.0

References
----------
.. [1] Q. Huangfu and J.A.J. Hall. "Parallelizing the dual revised simplex
           method." Mathematical Programming Computation, 10 (1), 119-142,
           2018. DOI: 10.1007/s12532-017-0130-5

"""

import numpy as np
from .optimize import _check_unknown_options, OptimizeWarning
from warnings import warn
from ._highs.highs_wrapper import highs_wrapper
from ._highs.constants cimport (
    CONST_I_INF,
    CONST_INF,
    MESSAGE_LEVEL_NONE,
    MESSAGE_LEVEL_VERBOSE,
    MESSAGE_LEVEL_DETAILED,
    MESSAGE_LEVEL_MINIMAL,
    MESSAGE_LEVEL_ALWAYS,

    MODEL_STATUS_NOTSET,
    MODEL_STATUS_LOAD_ERROR,
    MODEL_STATUS_MODEL_ERROR,
    MODEL_STATUS_MODEL_EMPTY,
    MODEL_STATUS_PRESOLVE_ERROR,
    MODEL_STATUS_SOLVE_ERROR,
    MODEL_STATUS_POSTSOLVE_ERROR,
    MODEL_STATUS_PRIMAL_INFEASIBLE,
    MODEL_STATUS_PRIMAL_UNBOUNDED,
    MODEL_STATUS_OPTIMAL,
    MODEL_STATUS_REACHED_DUAL_OBJECTIVE_VALUE_UPPER_BOUND as MODEL_STATUS_RDOVUB,
    MODEL_STATUS_REACHED_TIME_LIMIT,
    MODEL_STATUS_REACHED_ITERATION_LIMIT,
)
from scipy.sparse import csc_matrix, vstack, issparse


def _replace_inf(x):
    # Replace `np.inf` with CONST_INF
    infs = np.isinf(x)
    x[infs] = np.sign(x[infs])*CONST_INF
    return x


def _check_invalid_option_values(option, option_str, allowed, default):
    warning_message = ("Option {0} is {1}, "
                       "but only values in {2} are allowed. Using default."
                       .format(option_str, option, allowed))
    if option not in allowed:
        warn(warning_message, OptimizeWarning)
        return default
    return option


def _linprog_highs(lp, solver, time_limit=None, presolve=True,
                   disp=False, maxiter=None,
                   dual_feasibility_tolerance=None,
                   dual_objective_value_upper_bound=None,
                   message_level=MESSAGE_LEVEL_NONE,
                   primal_feasibility_tolerance=None,
                   simplex_crash_strategy=None,
                   simplex_dual_edge_weight_strategy=None,
                   simplex_primal_edge_weight_strategy=None,
                   simplex_strategy=None,
                   simplex_update_limit=None,
                   **unknown_options):
    r"""
    Solve the following linear programming problem using one of the HiGHS
    solvers:

    .. math::

        \min_x \ & c^T x \\
        \mbox{such that} \ & A_{ub} x \leq b_{ub},\\
        & A_{eq} x = b_{eq},\\
        & l \leq x \leq u ,

    where :math:`x` is a vector of decision variables; :math:`c`,
    :math:`b_{ub}`, :math:`b_{eq}`, :math:`l`, and :math:`u` are vectors; and
    :math:`A_{ub}` and :math:`A_{eq}` are matrices.

    Informally, that's:

    minimize::

        c @ x

    such that::

        A_ub @ x <= b_ub
        A_eq @ x == b_eq
        lb <= x <= ub

    Note that by default ``lb = 0`` and ``ub = None`` unless specified with
    ``bounds``.

    Parameters
    ----------
    lp :  _LPProblem
        A ``scipy.optimize._linprog_util._LPProblem`` ``namedtuple``.
    solver : "ipm" or "simplex" or None
        Which HiGHS solver to use.  If ``None``, HiGHS will determine which
        solver to use based on the problem.

    Options
    -------
    maxiter : int
        The maximum number of iterations to perform in either phase. For
        ``solver='ipm'``, this does not include the number of crossover
        iterations.  Default is ``CONST_I_INF``.
    disp : bool
        Set to ``True`` if indicators of optimization status are to be printed
        to the console each iteration; default ``False``.
    time_limit : float
        The maximum time in seconds allotted to solve the problem; default is
        unlimited (CONST_INF).
    presolve : bool
        Presolve attempts to  identify trivial infeasibilities,
        identify trivial unboundedness, and simplify the problem before
        sending the problem to the main solver. It is generally recommended
        to keep the default setting ``True``; set to ``False`` if presolve is
        to be disabled.
    dual_feasibility_tolerance : double
        Dual feasibility tolerance.  Default is 1e-07.
    dual_objective_value_upper_bound : double
        Upper bound on objective value for dual simplex:
        algorithm terminates if reached.  Default is ``CONST_INF``.
    message_level : int {0, 1, 2, 4, 7}
        Verbosity level, corresponds to:

            ``0``: MESSAGE_LEVEL_NONE

            ``1``: MESSAGE_LEVEL_VERBOSE

            ``2``: MESSAGE_LEVEL_DETAILED

            ``4``: MESSAGE_LEVEL_MINIMAL

            ``7``: MESSAGE_LEVEL_ALWAYS

        Default is ``MESSAGE_LEVEL_NONE``, but note:
        this option is ignored unless option ``disp`` is ``True``.
    primal_feasibility_tolerance : double
        Primal feasibility tolerance.  Default is 1e-07.
    simplex_crash_strategy : int {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
        Strategy for simplex crash: off / LTSSF / Bixby (0/1/2).
        Default is ``0``.  Corresponds to the following:

            ``0``: `SIMPLEX_CRASH_STRATEGY_OFF`

            ``1``: `SIMPLEX_CRASH_STRATEGY_LTSSF_K`

            ``2``: `SIMPLEX_CRASH_STRATEGY_BIXBY`

            ``3``: `SIMPLEX_CRASH_STRATEGY_LTSSF_PRI`

            ``4``: `SIMPLEX_CRASH_STRATEGY_LTSF_K`

            ``5``: `SIMPLEX_CRASH_STRATEGY_LTSF_PRI`

            ``6``: `SIMPLEX_CRASH_STRATEGY_LTSF`

            ``7``: `SIMPLEX_CRASH_STRATEGY_BIXBY_NO_NONZERO_COL_COSTS`

            ``8``: `SIMPLEX_CRASH_STRATEGY_BASIC`

            ``9``: `SIMPLE_CRASH_STRATEGY_TEST_SING`

    simplex_dual_edge_weight_strategy : int {0, 1, 2, 3, 4}
        Strategy for simplex dual edge weights:
        Dantzig / Devex / Steepest Edge.  Default is ``2``.
        Corresponds to the following:

            ``0``: `SIMPLEX_DUAL_EDGE_WEIGHT_STRATEGY_DANTZIG`

            ``1``: `SIMPLEX_DUAL_EDGE_WEIGHT_STRATEGY_DEVEX`

            ``2``: `SIMPLEX_DUAL_EDGE_WEIGHT_STRATEGY_STEEPEST_EDGE_TO_DEVEX_SWITCH`

            ``3``: `SIMPLEX_DUAL_EDGE_WEIGHT_STRATEGY_STEEPEST_EDGE`

            ``4``: `SIMPLEX_DUAL_EDGE_WEIGHT_STRATEGY_STEEPEST_EDGE_UNIT_INITIAL`

    simplex_primal_edge_weight_strategy : int {0, 1}
        Strategy for simplex primal edge weights:
        Dantzig / Devex.  Default is ``0``.
        Corresponds to the following:

            ``0``: `SIMPLEX_PRIMAL_EDGE_WEIGHT_STRATEGY_DANTZIG`

            ``1``: `SIMPLEX_PRIMAL_EDGE_WEIGHT_STRATEGY_DEVEX`

    simplex_strategy : int {0, 1, 2, 3, 4}
        Strategy for simplex solver. Default: ``1``. Corresponds
        to the following:

            ``0``: `SIMPLEX_STRATEGY_MIN`

            ``1``: `SIMPLEX_STRATEGY_DUAL`

            ``2``: `SIMPLEX_STRATEGY_DUAL_TASKS`

            ``3``: `SIMPLEX_STRATEGY_DUAL_MULTI`

            ``4``: `SIMPLEX_STRATEGY_PRIMAL`

    simplex_update_limit : int
        Limit on the number of simplex UPDATE operations.  Default
        is ``5000``.
    unknown_options : dict
        Optional arguments not used by this particular solver. If
        `unknown_options` is non-empty, a warning is issued listing all
        unused options.

    Returns
    -------
    sol : dict
        A dictionary consisting of the fields:

            x : 1D array
                The values of the decision variables that minimizes the
                objective function while satisfying the constraints.
            fun : float
                The optimal value of the objective function ``c @ x``.
            slack : 1D array
                The (nominally positive) values of the slack,
                ``b_ub - A_ub @ x``.
            con : 1D array
                The (nominally zero) residuals of the equality constraints,
                ``b_eq - A_eq @ x``.
            success : bool
                ``True`` when the algorithm succeeds in finding an optimal
                solution.
            status : int
                An integer representing the exit status of the algorithm.

                ``0`` : Optimization terminated successfully.

                ``1`` : Iteration or time limit reached.

                ``2`` : Problem appears to be infeasible.

                ``3`` : Problem appears to be unbounded.

                ``4`` : The HiGHS solver ran into a problem.

            nit : int
                The total number of iterations performed.
                For ``solver='simplex'``, this includes iterations in all
                phases. For ``solver='ipm'``, this does not include
                crossover iterations.
            message : str
                A string descriptor of the exit status of the algorithm.

    """

    _check_unknown_options(unknown_options)

    warning_message = ("Option `dual_feasibility_tolerance` is {0}, "
                       "but only positive values are allowed. Using default."
                       .format(dual_feasibility_tolerance))
    if (dual_feasibility_tolerance is not None and
            dual_feasibility_tolerance < 0):
        dual_feasibility_tolerance = None
        warn(warning_message, OptimizeWarning)

    warning_message = ("Option `primal_feasibility_tolerance` is {0}, "
                       "but only positive values are allowed. Using default."
                       .format(primal_feasibility_tolerance))
    if (primal_feasibility_tolerance is not None and
            primal_feasibility_tolerance < 0):
        primal_feasibility_tolerance = None
        warn(warning_message, OptimizeWarning)

    warning_message = ("Option `simplex_update_limit` is {0}, "
                       "but only positive values are allowed. Using default."
                       .format(simplex_update_limit))
    if (simplex_update_limit is not None and
            simplex_update_limit < 0):
        simplex_update_limit = None
        warn(warning_message, OptimizeWarning)

    message_level = (
        _check_invalid_option_values(message_level, 'message_level',
                                     {0, 1, 2, 4, 7}, 1))

    simplex_crash_strategy = (
        _check_invalid_option_values(simplex_crash_strategy,
                                     'simplex_crash_strategy',
                                     {None}.union(set(range(10))), None))

    simplex_dual_edge_weight_strategy = (
        _check_invalid_option_values(simplex_dual_edge_weight_strategy,
                                     'simplex_dual_edge_weight_strategy',
                                     {None}.union(set(range(5))), None))

    simplex_primal_edge_weight_strategy = (
        _check_invalid_option_values(simplex_primal_edge_weight_strategy,
                                     'simplex_primal_edge_weight_strategy',
                                     {None}.union(set(range(2))), None))

    simplex_strategy = (
        _check_invalid_option_values(simplex_strategy,
                                     'simplex_strategy',
                                     {None}.union(set(range(5))), None))

    statuses = {
        MODEL_STATUS_NOTSET: (4, 'HiGHS Status Code 0: HighsModelStatusNOTSET'),
        MODEL_STATUS_LOAD_ERROR: (4, 'HiGHS Status Code 1: HighsModelStatusLOAD_ERROR'),
        MODEL_STATUS_MODEL_ERROR: (4, 'HiGHS Status Code 2: HighsModelStatusMODEL_ERROR'),
        MODEL_STATUS_MODEL_EMPTY: (4, 'HiGHS Status Code 3: HighsModelStatusMODEL_EMPTY'),
        MODEL_STATUS_PRESOLVE_ERROR: (4, 'HiGHS Status Code 4: HighsModelStatusPRESOLVE_ERROR'),
        MODEL_STATUS_SOLVE_ERROR: (4, 'HiGHS Status Code 5: HighsModelStatusSOLVE_ERROR'),
        MODEL_STATUS_POSTSOLVE_ERROR: (4, 'HiGHS Status Code 6: HighsModelStatusPOSTSOLVE_ERROR'),
        MODEL_STATUS_RDOVUB: (4, 'HiGHS Status Code 10: HighsModelStatusREACHED_DUAL_OBJECTIVE_VALUE_UPPER_BOUND'),
        MODEL_STATUS_PRIMAL_INFEASIBLE: (2, "The problem is infeasible."),
        MODEL_STATUS_PRIMAL_UNBOUNDED: (3, "The problem is unbounded."),
        MODEL_STATUS_OPTIMAL: (0, "Optimization terminated successfully."),
        MODEL_STATUS_REACHED_TIME_LIMIT: (1, "Time limit reached."),
        MODEL_STATUS_REACHED_ITERATION_LIMIT: (1, "Iteration limit reached."),
    }

    c, A_ub, b_ub, A_eq, b_eq, bounds, x0 = lp

    lb, ub = bounds.T.copy()                # separate bounds, copy->C-cntgs
    # highs_wrapper solves LHS <= A*x <= RHS, not equality constraints
    lhs_ub = -np.ones_like(b_ub)*np.inf     # LHS of UB constraints is -inf
    rhs_ub = b_ub                           # RHS of UB constraints is b_ub
    lhs_eq = b_eq                           # Equality constaint is inequality
    rhs_eq = b_eq                           # constraint with LHS=RHS
    lhs = np.concatenate((lhs_ub, lhs_eq))
    rhs = np.concatenate((rhs_ub, rhs_eq))

    if issparse(A_ub) or issparse(A_eq):
        A = vstack((A_ub, A_eq))
    else:
        A = np.vstack((A_ub, A_eq))
    A = csc_matrix(A)

    options = {
        'presolve': presolve,
        'sense': 1,  # minimization
        'solver': solver,
        'time_limit': time_limit,
        'message_level': message_level*disp,
        'dual_feasibility_tolerance': dual_feasibility_tolerance,
        'dual_objective_value_upper_bound': dual_objective_value_upper_bound,
        'primal_feasibility_tolerance': primal_feasibility_tolerance,
        'simplex_crash_strategy': simplex_crash_strategy,
        'simplex_dual_edge_weight_strategy': simplex_dual_edge_weight_strategy,
        'simplex_primal_edge_weight_strategy': simplex_primal_edge_weight_strategy,
        'simplex_strategy': simplex_strategy,
        'simplex_update_limit': simplex_update_limit,
    }

    options['ipm_iteration_limit'] = maxiter
    options['simplex_iteration_limit'] = maxiter

    # np.inf doesn't work; use very large constant
    rhs = _replace_inf(rhs)
    lhs = _replace_inf(lhs)
    lb = _replace_inf(lb)
    ub = _replace_inf(ub)

    #from scipy.optimize._highs.mpswriter import mpswriter
    #mpswriter(b'test_enzo_example_c_with_infeasibility.txt', c, A, lhs, rhs, lb, ub, np.array([], dtype=np.int32))

    res = highs_wrapper(c, A.indptr, A.indices, A.data, lhs, rhs,
                        lb, ub, options)

    # HiGHS represents constraints as lhs/rhs, so
    # Ax + s = b => Ax = b - s
    # and we need to split up s by A_ub and A_eq
    slack = res.get('slack', None)
    con = None
    if slack is not None:
        con = slack[len(b_ub):]
        slack = slack[:len(b_ub)]

    sol = {'x': res.get('x', None),
           'slack': slack,
           # TODO: Add/test dual info like:
           # 'lambda': res.get('lambda', None),
           # 's': res.get('s', None),
           'fun': res.get('fun', None),
           'con': con,
           'status': statuses[res['status']][0],
           'success': res['status'] == MODEL_STATUS_OPTIMAL,
           'message': statuses[res['status']][1],
           'nit': res.get('simplex_nit', 0) or res.get('ipm_nit', 0)
           }
    if sol['x'] is not None:
        sol['x'] = np.array(sol['x'])
    return sol
