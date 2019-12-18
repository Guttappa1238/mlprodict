"""
@brief      test log(time=2s)
"""
import unittest
import numpy
from pandas import DataFrame
from pyquickhelper.pycode import ExtTestCase
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import BernoulliNB
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from mlprodict.onnxrt import OnnxInference


class TestRtValidateNaive(ExtTestCase):

    def fit_classification_model(self, model, n_classes, is_int=False,
                                 pos_features=False, label_string=False):
        X, y = make_classification(n_classes=n_classes, n_features=100,
                                   n_samples=1000,
                                   random_state=42, n_informative=7)
        if label_string:
            y = numpy.array(['cl%d' % cl for cl in y])
        X = X.astype(numpy.int64) if is_int else X.astype(numpy.float32)
        if pos_features:
            X = numpy.abs(X)
        X_train, X_test, y_train, _ = train_test_split(X, y, test_size=0.5,
                                                       random_state=42)
        model.fit(X_train, y_train)
        return model, X_test

    def test_model_bernoulli_nb_binary_classification(self):
        model, X = self.fit_classification_model(BernoulliNB(), 2)
        model_onnx = convert_sklearn(
            model, "?", [("input", FloatTensorType([None, X.shape[1]]))],
            dtype=numpy.float32)
        exp1 = model.predict(X)
        exp = model.predict_proba(X)

        oinf = OnnxInference(model_onnx, runtime='python')
        got = oinf.run({'input': X})
        self.assertEqualArray(exp1, got['output_label'])
        got2 = DataFrame(got['output_probability']).values
        self.assertEqualArray(exp, got2, decimal=4)

        oinf = OnnxInference(model_onnx, runtime='onnxruntime1')
        got = oinf.run({'input': X})
        self.assertEqualArray(exp1, got['output_label'])
        got2 = DataFrame(got['output_probability']).values
        self.assertEqualArray(exp, got2, decimal=4)

        oinf = OnnxInference(model_onnx, runtime='onnxruntime2')
        got = oinf.run({'input': X})
        self.assertEqualArray(exp1, got['output_label'])
        got2 = DataFrame(got['output_probability']).values
        self.assertEqualArray(exp, got2, decimal=4)


if __name__ == "__main__":
    unittest.main()
