# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
import numpy
from ...onnx_tools.onnx2py_helper import guess_numpy_type_from_dtype
from ._op import OpRun
from ..shape_object import ShapeObject


class _CommonQuantizeLinear(OpRun):

    def __init__(self, onnx_node, desc=None,
                 expected_attributes=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=expected_attributes,
                       **options)

    def common_run(self, x, y_scale, zero_point=None, axis=1):  # pylint: disable=W0221
        if len(y_scale.shape) > 1:
            raise RuntimeError(  # pragma: no cover
                "Input 2 must be a vector or a number.")
        if len(y_scale.shape) > 0 and y_scale.size == 1:
            y_scale = y_scale[0]
        if len(y_scale.shape) > 0:
            new_shape = [1 for s in x.shape]
            new_shape[axis] = len(y_scale)
            x = x / y_scale.reshape(new_shape)
        else:
            x = x / y_scale
        if zero_point is not None:
            dtype = zero_point.dtype
            if len(y_scale.shape) > 0:
                x += zero_point.reshape(new_shape)
            else:
                x += zero_point
            numpy.around(x, 1, out=x)
            if dtype == numpy.uint8:
                numpy.clip(x, 0, 255, out=x)
            elif dtype == numpy.int8:
                numpy.clip(x, -128, 127, out=x)
            else:
                raise RuntimeError(  # pragma no cover
                    "Unexpected dtype for input 2 {}.".format(dtype))
            return (x.astype(dtype), )

        dtype = numpy.uint8
        numpy.around(x, 1, out=x)
        numpy.clip(x, 0, 255, out=x)
        return (x.astype(dtype), )

    def _infer_sizes(self, *args):  # pylint: disable=W0221
        res = self.run(*args)
        return (dict(temp=0), ) + res


class QuantizeLinear(_CommonQuantizeLinear):

    atts = {'axis': 1}
    python_inputs = ['*inputs']

    def __init__(self, onnx_node, desc=None, **options):
        _CommonQuantizeLinear.__init__(
            self, onnx_node, desc=desc,
            expected_attributes=QuantizeLinear.atts,
            **options)

    def _run(self, *args, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        # args: x, y_scale, zero_point
        return self.common_run(*args, axis=self.axis)

    def _infer_shapes(self, *args):  # pylint: disable=W0221
        if len(args) > 2:
            dtype = args[2].dtype
        else:
            dtype = numpy.uint8
        return (ShapeObject(args[0].shape, dtype=dtype), )

    def _infer_types(self, *args):  # pylint: disable=W0221
        if len(args) > 2:
            if isinstance(args[2], numpy.ndarray):
                dtype = args[2].dtype
            dtype = guess_numpy_type_from_dtype(args[2])
        else:
            dtype = numpy.uint8
        return (dtype, )


class DynamicQuantizeLinear(OpRun):

    def __init__(self, onnx_node, desc=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       **options)
        self.dtype = numpy.uint8

    def _run(self, x, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        # args: x, y_scale, zero_point
        qmin, qmax = 0, 255
        minx = numpy.min(x)
        y_scale = (numpy.max(x) - minx) / (qmax - qmin)
        intermediate_zero_point = qmin - minx / y_scale
        y_zero_point = numpy.round(
            numpy.clip(intermediate_zero_point, qmin, qmax)).astype(self.dtype)
        y = numpy.clip(numpy.round(x / y_scale) + y_zero_point, qmin, qmax)
        return (y.astype(self.dtype),
                y_scale.astype(x.dtype),
                y_zero_point.astype(self.dtype))

    def _infer_shapes(self, *args):  # pylint: disable=W0221
        return (ShapeObject(args[0].shape, dtype=self.dtype),
                ShapeObject(None, dtype=args[0].dtype),
                ShapeObject(None, dtype=self.dtype))

    def _infer_types(self, *args):  # pylint: disable=W0221
        return (self.dtype, args[0], self.dtype)
