from os.path import join
import pathlib
from zipfile import ZipFile
from time import time


def configuration(parent_package='', top_path=None):
    from numpy.distutils.system_info import get_info, NotFoundError
    from numpy.distutils.misc_util import Configuration
    config = Configuration('_propack', parent_package, top_path)
    lapack_opt = get_info('lapack_opt')
    if not lapack_opt:
        raise NotFoundError('no lapack/blas resources found')

    # PROPACK sources are zipped to save on space, so make sure
    # they are unzipped before we try to use them
    _curdir = pathlib.Path(__file__).parent
    if not (_curdir / 'PROPACK').exists():
        print('[propack] PROPACK directory not found, unzipping...')
        zipfile = _curdir / 'PROPACK.zip'
        t0 = time()
        ZipFile(zipfile).extractall(path=_curdir / 'PROPACK')
        print(f'[propack] Took {time() - t0} seconds to extract PROPACK')
    else:
        print('[propack] PROPACK directory found!')

    #------------------------------------------------------------
    # Set up the libraries.
    #  We need a different python extension file for each, because
    #  names resue between functions in the LAPACK extensions.  This
    #  could probably be remedied with some work.
    type_dict = dict(s='single',
                     d='double',
                     c='complex8',
                     z='complex16')

    for prefix, directory in type_dict.items():
        lapack_lib = f'sp_{prefix}lapack_util'
        propack_lib = f'_{prefix}propack'

        lapack_sources = join('PROPACK', directory, 'Lapack_Util', '*.f')
        propack_sources = join('PROPACK', directory, '*.F')

        config.add_library(lapack_lib, sources=lapack_sources)
        config.add_library(propack_lib, sources=propack_sources)
        config.add_extension(f'_{prefix}propack',
                             sources=f'{prefix}propack.pyf',
                             libraries=[lapack_lib, propack_lib],
                             extra_info=lapack_opt)

    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())
