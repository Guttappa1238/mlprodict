# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
import itertools
import numpy
from ..shape_object import ShapeObjectFct, ShapeObject
from ._op import OpRun


def _get_pad_shape(auto_pad, input_spatial_shape, kernel_spatial_shape,
                   strides_spatial, output_spatial_shape):
    pad_shape = [0] * len(input_spatial_shape)
    if auto_pad in ('SAME_UPPER', 'SAME_LOWER'):
        for i in range(len(input_spatial_shape)):  # pylint: disable=C0200
            pad_shape[i] = (
                (output_spatial_shape[i] - 1) * strides_spatial[i] +
                kernel_spatial_shape[i] - input_spatial_shape[i])
    elif auto_pad == 'VALID':
        pass
    if len(pad_shape) == 0:
        raise RuntimeError(  # pragma: no cover
            "Unable to compute pad shape, auto_pad=%r, "
            "input_spatial_shape=%r, kernel_spatial_shape=%r, "
            "strides_spatial=%r." % (
                auto_pad, input_spatial_shape, kernel_spatial_shape,
                strides_spatial))
    return pad_shape


def _get_output_shape_no_ceil(auto_pad, input_spatial_shape, kernel_spatial_shape,
                              strides_spatial):
    out_shape = [0] * len(input_spatial_shape)
    if auto_pad in ('SAME_UPPER', 'SAME_LOWER'):
        for i in range(len(input_spatial_shape)):  # pylint: disable=C0200
            out_shape[i] = int(
                numpy.ceil(
                    float(input_spatial_shape[i]) /
                    float(strides_spatial[i])))
    elif auto_pad == 'VALID':
        for i in range(len(input_spatial_shape)):  # pylint: disable=C0200
            out_shape[i] = int(
                numpy.ceil(
                    float(input_spatial_shape[i] -
                          (kernel_spatial_shape[i] - 1)) /
                    float(strides_spatial[i])))
    return out_shape


def _get_output_shape(auto_pad, input_spatial_shape, kernel_spatial_shape,
                      strides_spatial, pad_shape=None, ceil_mode=0):
    if not ceil_mode:
        out_shape = _get_output_shape_no_ceil(
            auto_pad, input_spatial_shape, kernel_spatial_shape,
            strides_spatial)
    else:
        round_fct = numpy.ceil if ceil_mode else numpy.floor
        out_shape = [0] * len(input_spatial_shape)
        if auto_pad in ('SAME_UPPER', 'SAME_LOWER'):
            for i in range(len(input_spatial_shape)):  # pylint: disable=C0200
                out_shape[i] = int(
                    round_fct(float(input_spatial_shape[i]) / float(strides_spatial[i])))
        elif auto_pad == 'VALID':
            if pad_shape is None:
                raise ValueError(  # pragma: no cover
                    "pad_shape cannot be None if auto_pad is "
                    "'VALID' and ceil_mode is 1.")
            for i in range(len(input_spatial_shape)):  # pylint: disable=C0200
                out_shape[i] = int(
                    round_fct(
                        float(input_spatial_shape[i] + pad_shape[i] - kernel_spatial_shape[i]) /
                        float(strides_spatial[i]) + 1))
    if len(out_shape) == 0:
        raise RuntimeError(  # pragma: no cover
            "Unable to compute output shape, auto_pad=%r, "
            "input_spatial_shape=%r, kernel_spatial_shape=%r, "
            "strides_spatial=%r, ceil_mode=%r." % (
                auto_pad, input_spatial_shape, kernel_spatial_shape,
                strides_spatial, ceil_mode))
    if min(out_shape) <= 0:
        raise RuntimeError(  # pragma: no cover
            "output shape cannot be null or negative, out_shape=%r, "
            "auto_pad=%r, input_spatial_shape=%r, "
            "kernel_spatial_shape=%r, strides_spatial=%r, ceil_mode=%r." % (
                out_shape, auto_pad, input_spatial_shape,
                kernel_spatial_shape, strides_spatial, ceil_mode))
    return out_shape


def _pool(padded, x_shape, kernel_shape, strides_shape,
          out_shape, pad_shape, pooling_type, count_include_pad=0, ceil_mode=0):
    if pooling_type == 'AVG':
        fpool = numpy.average
    elif pooling_type == 'MAX':
        fpool = numpy.max
    else:
        raise NotImplementedError(  # pragma: no cover
            'Pooling type {} does not support. Should be AVG, MAX.'
            ''.format(pooling_type))
    spatial_size = len(x_shape) - 2
    y = numpy.zeros([x_shape[0], x_shape[1]] + list(out_shape))
    round_fct = numpy.ceil if ceil_mode else numpy.floor

    def loop_range():
        return [range(int(round_fct(
                float(x_shape[i + 2] + pad_shape[i] - kernel_shape[i]) /
                float(strides_shape[i]) + 1))) for i in range(spatial_size)]

    for shape in itertools.product(range(x_shape[0]), range(x_shape[1]), *loop_range()):
        window = padded[shape[0], shape[1]]
        listi = [range(strides_shape[i] * shape[i + 2],
                       strides_shape[i] * shape[i + 2] + kernel_shape[i])
                 for i in range(spatial_size)]
        listi2 = list(itertools.product(*listi))
        values = []
        for i in listi2:
            try:
                values.append(window[i])
            except IndexError:
                continue
        window_vals = numpy.array(values)

        if count_include_pad == 1 and pooling_type == 'AVG':
            y[shape] = fpool(window_vals)
        else:
            y[shape] = fpool(
                window_vals[numpy.where(~numpy.isnan(window_vals))])
    return y.astype(numpy.float32)


class AveragePool(OpRun):

    atts = {'auto_pad': b'NOTSET',
            'ceil_mode': 0,
            'count_include_pad': 0,
            'kernel_shape': [],
            'pads': [],
            'strides': []}

    def __init__(self, onnx_node, desc=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=AveragePool.atts,
                       **options)

    def _run(self, x, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        if len(self.strides) == 0:
            strides = [1] * (len(x.shape) - 2)
        else:
            strides = self.strides
        kernel_shape = list(self.kernel_shape)
        auto_pad = (
            'VALID' if self.auto_pad == b'NOTSET'
            else self.auto_pad.decode('ascii'))

        if len(self.pads) == 0:
            pad_shape = [0] * (len(x.shape) - 2)
            x_shape = x.shape[2:]
            padded = x
        elif len(self.pads) == 4:
            pad_top, pad_bottom, pad_left, pad_right = self.pads
            pad_shape = [pad_top + pad_bottom, pad_left + pad_right]
            x_shape = numpy.array(x.shape[2:]) + numpy.array(pad_shape)
            const = numpy.nan if self.count_include_pad == 0 else 0
            padded = numpy.pad(
                x, ((0, 0), (0, 0),
                    (pad_top, pad_bottom), (pad_left, pad_right)),
                mode='constant', constant_values=const)
        else:
            pad_shape = self.pads
            x_shape = x.shape[2:]
            padded = x

        if auto_pad in ('SAME_LOWER', 'SAME_UPPER'):
            const = numpy.nan if self.count_include_pad == 0 else 0
            out_shape = _get_output_shape(
                auto_pad, x_shape, kernel_shape, strides, pad_shape, self.ceil_mode)
            pad_shape = _get_pad_shape(
                auto_pad, x_shape, kernel_shape, strides, out_shape)
            if auto_pad == 'SAME_LOWER':
                pad_bottom = pad_shape[0] // 2
                pad_top = pad_shape[0] - pad_bottom
                pad_right = pad_shape[1] // 2
                pad_left = pad_shape[1] - pad_right
            else:
                pad_top = pad_shape[0] // 2
                pad_bottom = pad_shape[0] - pad_top
                pad_left = pad_shape[1] // 2
                pad_right = pad_shape[1] - pad_left
            padded = numpy.pad(
                padded, ((0, 0), (0, 0), (pad_top, pad_bottom),
                         (pad_left, pad_right)),
                mode='constant', constant_values=const)
        else:
            out_shape = _get_output_shape(
                auto_pad, x_shape, kernel_shape, strides, pad_shape, self.ceil_mode)

        pooling_type = 'AVG'
        res = _pool(padded, x.shape, kernel_shape, strides,
                    out_shape, pad_shape, pooling_type,
                    count_include_pad=self.count_include_pad,
                    ceil_mode=self.ceil_mode)
        return (res, )

    def _infer_shapes(self, x):  # pylint: disable=W0221
        kernel_shape = list(self.kernel_shape)
        auto_pad = 'VALID' if self.auto_pad == 'NOTSET' else self.auto_pad
        if len(self.pads) == 0:
            if x.shape is None:
                return (ShapeObject(None, dtype=x.dtype), )
            pad_shape = [0] * (len(x.shape) - 2)
        elif len(self.pads) == 4:
            pad_top, pad_bottom, pad_left, pad_right = self.pads
            pad_shape = [pad_top + pad_bottom, pad_left + pad_right]

        def compute_shape(xshape):
            if len(self.strides) == 0:
                strides = [1] * (len(xshape) - 2)
            else:
                strides = self.strides
            out_shape = _get_output_shape(
                auto_pad, xshape[2:], kernel_shape, strides, pad_shape, self.ceil_mode)
            return out_shape

        return (ShapeObjectFct(
            compute_shape, x, name="AveragePool", dtype=x.dtype), )

    def _infer_types(self, x):  # pylint: disable=W0221
        return (x, )

    def _infer_sizes(self, *args):  # pylint: disable=W0221
        res = self.run(*args)
        return (dict(temp=0), ) + res
