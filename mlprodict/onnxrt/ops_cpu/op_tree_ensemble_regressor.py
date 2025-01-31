# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
from collections import OrderedDict
import numpy
from onnx.defs import onnx_opset_version
from ._op_helper import _get_typed_class_attribute
from ._op import OpRunUnaryNum, RuntimeTypeError
from ._new_ops import OperatorSchema
from .op_tree_ensemble_regressor_ import (  # pylint: disable=E0611,E0401
    RuntimeTreeEnsembleRegressorFloat, RuntimeTreeEnsembleRegressorDouble)
from .op_tree_ensemble_regressor_p_ import (  # pylint: disable=E0611,E0401
    RuntimeTreeEnsembleRegressorPFloat, RuntimeTreeEnsembleRegressorPDouble)


class TreeEnsembleRegressorCommon(OpRunUnaryNum):

    def __init__(self, dtype, onnx_node, desc=None,
                 expected_attributes=None, runtime_version=3, **options):
        OpRunUnaryNum.__init__(
            self, onnx_node, desc=desc,
            expected_attributes=expected_attributes, **options)
        self._init(dtype=dtype, version=runtime_version)

    def _get_typed_attributes(self, k):
        return _get_typed_class_attribute(self, k, self.__class__.atts)

    def _find_custom_operator_schema(self, op_name):
        """
        Finds a custom operator defined by this runtime.
        """
        if op_name == "TreeEnsembleRegressorDouble":
            return TreeEnsembleRegressorDoubleSchema()
        raise RuntimeError(  # pragma: no cover
            "Unable to find a schema for operator '{}'.".format(op_name))

    def _init(self, dtype, version):
        atts = []
        for k in self.__class__.atts:
            v = self._get_typed_attributes(k)
            if k.endswith('_as_tensor'):
                if (v is not None and isinstance(v, numpy.ndarray) and
                        v.size > 0):
                    # replacements
                    atts[-1] = v
                    if dtype is None:
                        dtype = v.dtype
                continue
            atts.append(v)

        if dtype is None:
            dtype = numpy.float32

        if dtype == numpy.float32:
            if version == 0:
                self.rt_ = RuntimeTreeEnsembleRegressorFloat()
            elif version == 1:
                self.rt_ = RuntimeTreeEnsembleRegressorPFloat(
                    60, 20, False, False)
            elif version == 2:
                self.rt_ = RuntimeTreeEnsembleRegressorPFloat(
                    60, 20, True, False)
            elif version == 3:
                self.rt_ = RuntimeTreeEnsembleRegressorPFloat(
                    60, 20, True, True)
            else:
                raise ValueError("Unknown version '{}'.".format(version))
        elif dtype == numpy.float64:
            if version == 0:
                self.rt_ = RuntimeTreeEnsembleRegressorDouble()
            elif version == 1:
                self.rt_ = RuntimeTreeEnsembleRegressorPDouble(
                    60, 20, False, False)
            elif version == 2:
                self.rt_ = RuntimeTreeEnsembleRegressorPDouble(
                    60, 20, True, False)
            elif version == 3:
                self.rt_ = RuntimeTreeEnsembleRegressorPDouble(
                    60, 20, True, True)
            else:
                raise ValueError("Unknown version '{}'.".format(version))
        else:
            raise RuntimeTypeError(  # pragma: no cover
                "Unsupported dtype={}.".format(dtype))
        self.rt_.init(*atts)

    def _run(self, x, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        """
        This is a C++ implementation coming from
        :epkg:`onnxruntime`.
        `tree_ensemble_classifier.cc
        <https://github.com/microsoft/onnxruntime/blob/master/onnxruntime/core/providers/cpu/ml/tree_ensemble_classifier.cc>`_.
        See class :class:`RuntimeTreeEnsembleRegressorFloat
        <mlprodict.onnxrt.ops_cpu.op_tree_ensemble_regressor_.RuntimeTreeEnsembleRegressorFloat>` or
        class :class:`RuntimeTreeEnsembleRegressorDouble
        <mlprodict.onnxrt.ops_cpu.op_tree_ensemble_regressor_.RuntimeTreeEnsembleRegressorDouble>`.
        """
        if hasattr(x, 'todense'):
            x = x.todense()
        pred = self.rt_.compute(x)
        if pred.shape[0] != x.shape[0]:
            pred = pred.reshape(x.shape[0], pred.shape[0] // x.shape[0])
        return (pred, )


class TreeEnsembleRegressor_1(TreeEnsembleRegressorCommon):

    atts = OrderedDict([
        ('aggregate_function', b'SUM'),
        ('base_values', numpy.empty(0, dtype=numpy.float32)),
        ('base_values_as_tensor', []),
        ('n_targets', 1),
        ('nodes_falsenodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_featureids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_hitrates', numpy.empty(0, dtype=numpy.float32)),
        ('nodes_missing_value_tracks_true', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_modes', []),
        ('nodes_nodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_treeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_truenodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_values', numpy.empty(0, dtype=numpy.float32)),
        ('post_transform', b'NONE'),
        ('target_ids', numpy.empty(0, dtype=numpy.int64)),
        ('target_nodeids', numpy.empty(0, dtype=numpy.int64)),
        ('target_treeids', numpy.empty(0, dtype=numpy.int64)),
        ('target_weights', numpy.empty(0, dtype=numpy.float32)),
    ])

    def __init__(self, onnx_node, desc=None, runtime_version=1, **options):
        TreeEnsembleRegressorCommon.__init__(
            self, numpy.float32, onnx_node, desc=desc,
            expected_attributes=TreeEnsembleRegressor_1.atts,
            runtime_version=runtime_version, **options)


class TreeEnsembleRegressor_3(TreeEnsembleRegressorCommon):

    atts = OrderedDict([
        ('aggregate_function', b'SUM'),
        ('base_values', numpy.empty(0, dtype=numpy.float32)),
        ('base_values_as_tensor', []),
        ('n_targets', 1),
        ('nodes_falsenodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_featureids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_hitrates', numpy.empty(0, dtype=numpy.float32)),
        ('nodes_hitrates_as_tensor', []),
        ('nodes_missing_value_tracks_true', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_modes', []),
        ('nodes_nodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_treeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_truenodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_values', numpy.empty(0, dtype=numpy.float32)),
        ('nodes_values_as_tensor', []),
        ('post_transform', b'NONE'),
        ('target_ids', numpy.empty(0, dtype=numpy.int64)),
        ('target_nodeids', numpy.empty(0, dtype=numpy.int64)),
        ('target_treeids', numpy.empty(0, dtype=numpy.int64)),
        ('target_weights', numpy.empty(0, dtype=numpy.float32)),
        ('target_weights_as_tensor', []),
    ])

    def __init__(self, onnx_node, desc=None, runtime_version=1, **options):
        TreeEnsembleRegressorCommon.__init__(
            self, None, onnx_node, desc=desc,
            expected_attributes=TreeEnsembleRegressor_3.atts,
            runtime_version=runtime_version, **options)


class TreeEnsembleRegressorDouble(TreeEnsembleRegressorCommon):
    """
    Runtime for the custom operator `TreeEnsembleRegressorDouble`.
    .. exref::
        :title: How to use TreeEnsembleRegressorDouble instead of TreeEnsembleRegressor
        .. runpython::
            :showcode:
            import warnings
            import numpy
            from sklearn.datasets import make_regression
            from sklearn.ensemble import (
                RandomForestRegressor, GradientBoostingRegressor,
                HistGradientBoostingRegressor)
            from mlprodict.onnx_conv import to_onnx
            from mlprodict.onnxrt import OnnxInference
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                models = [
                    RandomForestRegressor(n_estimators=10),
                    GradientBoostingRegressor(n_estimators=10),
                    HistGradientBoostingRegressor(max_iter=10),
                ]
                X, y = make_regression(1000, n_features=5, n_targets=1)
                X = X.astype(numpy.float64)
                conv = {}
                for model in models:
                    model.fit(X[:500], y[:500])
                    onx64 = to_onnx(model, X, rewrite_ops=True, target_opset=15)
                    assert 'TreeEnsembleRegressorDouble' in str(onx64)
                    expected = model.predict(X)
                    oinf = OnnxInference(onx64)
                    got = oinf.run({'X': X})
                    diff = numpy.abs(got['variable'] - expected)
                    print("%s: max=%f mean=%f" % (
                        model.__class__.__name__, diff.max(), diff.mean()))
    """

    atts = OrderedDict([
        ('aggregate_function', b'SUM'),
        ('base_values', numpy.empty(0, dtype=numpy.float64)),
        ('n_targets', 1),
        ('nodes_falsenodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_featureids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_hitrates', numpy.empty(0, dtype=numpy.float64)),
        ('nodes_missing_value_tracks_true', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_modes', []),
        ('nodes_nodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_treeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_truenodeids', numpy.empty(0, dtype=numpy.int64)),
        ('nodes_values', numpy.empty(0, dtype=numpy.float64)),
        ('post_transform', b'NONE'),
        ('target_ids', numpy.empty(0, dtype=numpy.int64)),
        ('target_nodeids', numpy.empty(0, dtype=numpy.int64)),
        ('target_treeids', numpy.empty(0, dtype=numpy.int64)),
        ('target_weights', numpy.empty(0, dtype=numpy.float64)),
    ])

    def __init__(self, onnx_node, desc=None, runtime_version=1, **options):
        TreeEnsembleRegressorCommon.__init__(
            self, numpy.float64, onnx_node, desc=desc,
            expected_attributes=TreeEnsembleRegressorDouble.atts,
            runtime_version=runtime_version, **options)


class TreeEnsembleRegressorDoubleSchema(OperatorSchema):
    """
    Defines a schema for operators added in this package
    such as @see cl TreeEnsembleRegressorDouble.
    """

    def __init__(self):
        OperatorSchema.__init__(self, 'TreeEnsembleRegressorDouble')
        self.attributes = TreeEnsembleRegressorDouble.atts


if onnx_opset_version() >= 16:
    TreeEnsembleRegressor = TreeEnsembleRegressor_3
else:
    TreeEnsembleRegressor = TreeEnsembleRegressor_1
