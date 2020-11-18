"""
.. _l-einsum:

Compares implementation of Einsum
=================================

The following function benchmark different implementation
of function :epkg:`numpy:einsum`.
It compares *numpy* implementation to a custom implementation,
:epkg:`onnxruntime` implementation and :epkg:`opt-einsum` optimisation.
If available, :epkg:`tensorflow` and :epkg:`pytorch` are included as well.
The custom implementation does not do any transpose.
It uses parallelisation and SIMD optimization when the summation
happens on the last axis of both matrices. It only implements
matrix multiplication.

.. contents::
    :local:

Available optimisation
++++++++++++++++++++++

The code shows which optimisation is used for the custom
implementation, *AVX* or *SSE* and the number of available processors,
equal to the default number of used threads to parallelize.
"""
from mlprodict.testing.experimental_c import code_optimisation
print(code_optimisation())

###################################
# Einsum: common code
# +++++++++++++++++++

import numpy
import pandas
import matplotlib.pyplot as plt
from opt_einsum import contract
from tqdm import tqdm
from cpyquickhelper.numbers.speed_measure import measure_time
from mlprodict.testing.experimental_c import custom_einsum_float
from onnxruntime import InferenceSession
from skl2onnx.algebra.onnx_ops import OnnxEinsum
from skl2onnx.common.data_types import FloatTensorType
import onnx
try:
    from tensorflow import einsum as tf_einsum, convert_to_tensor
except ImportError:
    tf_einsum = None
try:
    from torch import einsum as torch_einsum, from_numpy
except ImportError:
    torch_einsum = None


def build_ort_einsum(equation, op_version=12):
    node = OnnxEinsum('x', 'y', equation=equation,
                      op_version=op_version,
                      output_names=['z'])
    onx = node.to_onnx(inputs=[('x', FloatTensorType()),
                               ('y', FloatTensorType())],
                       target_opset=op_version)
    sess = InferenceSession(onx.SerializeToString())
    return lambda x, y: sess.run(None, {'x': x, 'y': y})


def loop_einsum_eq(fct, equation, xs, ys):
    for x, y in zip(xs, ys):
        fct(equation, x, y)


def loop_einsum_eq_th(fct, equation, xs, ys):
    for x, y in zip(xs, ys):
        fct(equation, x, y, nthread=-1)


def loop_einsum(fct, xs, ys):
    for x, y in zip(xs, ys):
        fct(x, y)


def custom_einsum_float_tr(eq, x, y):
    if eq == "bshn,bthn->bnts":
        x = x.transpose((0, 1, 3, 2))
        y = y.transpose((0, 1, 3, 2))
        return custom_einsum_float("bsnh,btnh->bnts", x, y, nthread=-1)
    if eq == "bhsn,bhtn->bnts":
        x = x.transpose((0, 2, 3, 1))
        y = y.transpose((0, 2, 3, 1))
        return custom_einsum_float("bsnh,btnh->bnts", x, y, nthread=-1)
    return custom_einsum_float(eq, x, y, nthread=-1)


def benchmark_equation(equation):
    # equations
    ort_einsum = build_ort_einsum(equation)
    res = []
    for dim in tqdm([8, 16, 32, 64, 100, 128, 200,
                     256, 500, 512]):
        xs = [numpy.random.rand(2, dim, 12, 64).astype(numpy.float32)
              for _ in range(5)]
        ys = [numpy.random.rand(2, dim, 12, 64).astype(numpy.float32)
              for _ in range(5)]

        # numpy
        ctx = dict(equation=equation, xs=xs, ys=ys, einsum=numpy.einsum,
                   loop_einsum=loop_einsum, loop_einsum_eq=loop_einsum_eq,
                   loop_einsum_eq_th=loop_einsum_eq_th)
        obs = measure_time(
            "loop_einsum_eq(einsum, equation, xs, ys)",
            div_by_number=True, context=ctx, repeat=5, number=1)
        obs['dim'] = dim
        obs['fct'] = 'numpy.einsum'
        res.append(obs)

        # opt-einsum
        ctx['einsum'] = contract
        obs = measure_time(
            "loop_einsum_eq(einsum, equation, xs, ys)",
            div_by_number=True, context=ctx, repeat=5, number=1)
        obs['dim'] = dim
        obs['fct'] = 'opt-einsum'
        res.append(obs)

        # onnxruntime
        ctx['einsum'] = ort_einsum
        obs = measure_time(
            "loop_einsum(einsum, xs, ys)",
            div_by_number=True, context=ctx, repeat=5, number=1)
        obs['dim'] = dim
        obs['fct'] = 'ort_einsum'
        res.append(obs)
        
        # custom implementation
        ctx['einsum'] = custom_einsum_float
        obs = measure_time(
            "loop_einsum_eq_th(einsum, equation, xs, ys)",
            div_by_number=True, context=ctx, repeat=5, number=1)
        obs['dim'] = dim
        obs['fct'] = 'c_einsum'
        res.append(obs)

        # transpose + custom implementation
        ctx['einsum'] = custom_einsum_float_tr
        obs = measure_time(
            "loop_einsum_eq(einsum, equation, xs, ys)",
            div_by_number=True, context=ctx, repeat=5, number=1)
        obs['dim'] = dim
        obs['fct'] = 'c_einsum_tr'
        res.append(obs)

        if tf_einsum is not None:
            # tensorflow
            ctx['einsum'] = tf_einsum
            ctx['xs'] = [convert_to_tensor(x) for x in xs]
            ctx['ys'] = [convert_to_tensor(y) for y in ys]
            obs = measure_time(
                "loop_einsum_eq(einsum, equation, xs, ys)",
                div_by_number=True, context=ctx, repeat=5, number=1)
            obs['dim'] = dim
            obs['fct'] = 'tf_einsum'
            res.append(obs)

        if torch_einsum is not None:
            # torch
            ctx['einsum'] = torch_einsum
            ctx['xs'] = [from_numpy(x) for x in xs]
            ctx['ys'] = [from_numpy(y) for y in ys]
            obs = measure_time(
                "loop_einsum_eq(einsum, equation, xs, ys)",
                div_by_number=True, context=ctx, repeat=5, number=1)
            obs['dim'] = dim
            obs['fct'] = 'torch_einsum'
            res.append(obs)

    # Dataframes
    df = pandas.DataFrame(res)
    piv = df.pivot('dim', 'fct', 'average')

    rs = piv.copy()
    rs['c_einsum'] = rs['numpy.einsum'] / rs['c_einsum']
    rs['ort_einsum'] = rs['numpy.einsum'] / rs['ort_einsum']
    rs['opt-einsum'] = rs['numpy.einsum'] / rs['opt-einsum']
    if 'c_einsum_tr' in rs.columns:
        rs['c_einsum_tr'] = rs['numpy.einsum'] / rs['c_einsum_tr']
    if 'tf_einsum' in rs.columns:
        rs['tf_einsum'] = rs['numpy.einsum'] / rs['tf_einsum']
    if 'torch_einsum' in rs.columns:
        rs['torch_einsum'] = rs['numpy.einsum'] / rs['torch_einsum']
    rs['numpy.einsum'] = 1.

    # Graphs.
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    piv.plot(logx=True, logy=True, ax=ax[0],
             title="Einsum benchmark\n%s -- (2, N, 12, 64)" % equation)
    ax[0].legend(prop={"size":6})
    rs.plot(logx=True, logy=True, ax=ax[1],
            title="Einsum Speedup, baseline=numpy\n%s -- (2, N, 12, 64)" % equation)
    ax[1].plot([min(rs.index), max(rs.index)], [0.5, 0.5], 'g--')
    ax[1].plot([min(rs.index), max(rs.index)], [2., 2.], 'g--')
    ax[1].legend(prop={"size":6})

    return df, piv, ax


###################################
# First equation: bsnh,btnh->bnts
# +++++++++++++++++++++++++++++++

equation = "bsnh,btnh->bnts"
df, piv, ax = benchmark_equation(equation)
df.pivot("fct", "dim", "average")

####################################
# Ratios
piv.T

###################################
# Second equation: bshn,bthn->bnts
# ++++++++++++++++++++++++++++++++
#
# The summation does not happen on the last axis but
# on the previous one.
# Is it worth transposing before doing the summation...

equation = "bshn,bthn->bnts"
df, piv, ax = benchmark_equation(equation)
df.pivot("fct", "dim", "average")

####################################
# Ratios
piv.T

###################################
# Third equation: bhsn,bhtn->bnts
# +++++++++++++++++++++++++++++++
#
# The summation does not happen on the last axis but
# on the second one. It is worth transposing before multiplying.
# 

equation = "bhsn,bhtn->bnts"
df, piv, ax = benchmark_equation(equation)
df.pivot("fct", "dim", "average")

####################################
# Ratios
piv.T


####################################
# Conclusion
# ++++++++++
#

plt.show()
