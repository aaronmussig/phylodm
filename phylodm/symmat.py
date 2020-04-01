###############################################################################
#                                                                             #
#    This program is free software: you can redistribute it and/or modify     #
#    it under the terms of the GNU General Public License as published by     #
#    the Free Software Foundation, either version 3 of the License, or        #
#    (at your option) any later version.                                      #
#                                                                             #
#    This program is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program. If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from typing import Collection, Tuple, List

import h5py
import numpy as np

from phylodm.common import row_idx_from_mat_coords, create_mat, mat_shape_from_row_shape
from phylodm.indices import Indices


class SymMat(object):

    def __init__(self):
        self._d_type = None  # https://docs.scipy.org/doc/numpy/reference/generated/numpy.dtype.html?highlight=dtype#numpy.dtype
        self._arr_default = None
        self._indices = None
        self._data = None

    def __eq__(self, other) -> bool:
        if isinstance(other, SymMat):
            return self._d_type == other._d_type and \
                   self._indices == other._indices and \
                   np.array_equal(self._data, other._data)
        return False

    def _n_indices(self) -> int:
        return mat_shape_from_row_shape(self._data.shape[0])

    def _idx_from_key(self, key_i: str, key_j: str) -> int:
        i = self._indices.get_key_idx(key_i)
        j = self._indices.get_key_idx(key_j)
        return row_idx_from_mat_coords(self._n_indices(), i, j)

    @staticmethod
    def get_from_path(path: str) -> 'SymMat':
        return SymMat()._get_from_path(path)

    def _get_from_path(self, path: str) -> 'SymMat':
        self._indices = Indices()
        with h5py.File(path, 'r') as hf:
            self._arr_default = hf['arr_default'][()]
            self._data = hf['data'][()]
            for idx, key in enumerate(hf['indices'][()]):
                self._indices.add_key(key.decode('utf-8'))
        self._d_type = self._data.dtype
        return self

    def save_to_path(self, path: str):
        with h5py.File(path, 'w') as f:
            f.create_dataset('indices',
                             data=[t.encode('ascii') for t in self._indices.get_keys()],
                             dtype=h5py.string_dtype(encoding='ascii'))
            f.create_dataset('data', data=self._data, chunks=True, dtype=self._d_type)
            f.create_dataset('arr_default', data=self._arr_default, dtype=self._d_type)

    @staticmethod
    def get_from_shape(n_indices: int, d_type: np.dtype, arr_default=0) -> 'SymMat':
        return SymMat()._get_from_shape(n_indices, d_type, arr_default)

    def _get_from_shape(self, n_indices: int, d_type: np.dtype, arr_default=0) -> 'SymMat':
        self._d_type = d_type
        self._arr_default = arr_default
        self._indices = Indices()
        self._data = create_mat(n_indices, arr_default)
        return self

    def get_from_indices(self, indices: Collection[str], d_type: np.dtype, arr_default=0) -> 'SymMat':
        self._d_type = d_type
        self._arr_default = arr_default
        self._indices = Indices()
        self._indices.add_keys(indices)
        self._data = create_mat(len(indices), arr_default)
        return self

    def get_value(self, key_i: str, key_j: str):
        data_idx = self._idx_from_key(key_i, key_j)
        return self._data[data_idx]

    def set_value(self, key_i: str, key_j: str, value):
        if not self._indices.contains(key_i):
            self._indices.add_key(key_i)
        if not self._indices.contains(key_j):
            self._indices.add_key(key_j)
        self._data[self._idx_from_key(key_i, key_j)] = value

    def as_matrix(self) -> Tuple[List[str], np.array]:
        n_indices = self._n_indices()
        mat = np.full((n_indices, n_indices), 0, dtype=self._d_type)
        # mat[np.triu_indices_from(mat)] = self._data
        # mat[np.tril_indices_from(mat, -1)] = mat[np.triu_indices_from(mat, 1)]
        mat[np.triu_indices_from(mat)] = self._data
        diag = mat[np.diag_indices_from(mat)]
        mat = mat + mat.T
        mat[np.diag_indices_from(mat)] = mat[np.diag_indices_from(mat)] - diag
        return self._indices.get_keys(), mat
