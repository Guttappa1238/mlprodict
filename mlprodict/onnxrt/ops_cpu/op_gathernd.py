"""
@file
@brief Runtime operator.
"""
import numpy
from ..shape_object import ShapeObject
from ._op import OpRun


def _gather_nd_impl(data, indices, batch_dims):
    """
    Modified version of `softmaxcrossentropy.py
    <https://github.com/onnx/onnx/blob/main/onnx/backend/
    test/case/node/gathernd.py>`_.
    """
    # Note the data rank - will be reused multiple times later
    data_rank = len(data.shape)

    # The list of data/indice shape of batch_dims.
    batch_dims_shape = []

    # The number of elements in the batch_dims for data/indice array.
    batch_dims_size = 1

    # Check the shape of indice and data are identicial for batch dims.
    for i in range(batch_dims):
        batch_dims_shape.append(indices.shape[i])
        batch_dims_size *= indices.shape[i]

    # Compute output of the op as below.
    # Compute shape of output array.
    output_shape = (
        batch_dims_shape + list(indices.shape)[batch_dims:-1]
        if (indices.shape[-1] == data_rank - batch_dims)
        else batch_dims_shape + list(indices.shape)[batch_dims:-1] +
        list(data.shape)[batch_dims + indices.shape[-1]:])

    # Placeholder for output data.
    output_data_buffer = []

    # Flatten 'indices' to 2D array.
    reshaped_indices = indices.reshape(batch_dims_size, -1, indices.shape[-1])

    # Flatten 'data' to array of shape
    # (batch_dim_size, data.shape[batch_dimes:]).
    reshaped_data = data.reshape((batch_dims_size, ) + data.shape[batch_dims:])

    # Gather each scalar value from 'data'.
    for batch_dim in range(reshaped_indices.shape[0]):
        for outer_dim in range(reshaped_indices.shape[1]):
            gather_index = tuple(reshaped_indices[batch_dim][outer_dim])
            output_data_buffer.append(
                reshaped_data[(batch_dim,) + gather_index])
    return (numpy.asarray(output_data_buffer,
                          dtype=data.dtype).reshape(output_shape), )


class GatherND(OpRun):
    """
    Python runtime for function *SoftmaxCrossEntropyLoss*.
    """

    atts = {'batch_dims': 0}

    def __init__(self, onnx_node, desc=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=GatherND.atts,
                       **options)

    def _run(self, data, indices, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        return _gather_nd_impl(data, indices, self.batch_dims)  # pylint: disable=E1101

    def _infer_shapes(self, x, target, weight=None):  # pylint: disable=W0221
        return (ShapeObject(None, dtype=x.dtype), )

    def _infer_types(self, x, target, weight=None):  # pylint: disable=W0221
        return (x.dtype, )

    def _infer_sizes(self, *args):  # pylint: disable=W0221
        res = self.run(*args)
        return (dict(temp=0), ) + res
