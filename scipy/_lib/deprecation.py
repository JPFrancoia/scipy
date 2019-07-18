import functools
import warnings

__all__ = ["_deprecated"]


def _deprecated(msg):
    """Deprecate a function by emitting a warning on use."""
    def wrap(fun):
        @functools.wraps(fun)
        def call(*args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return fun(*args, **kwargs)
        call.__doc__ = msg
        return call

    return wrap
