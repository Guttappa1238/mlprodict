"""
@brief      test log(time=2s)
"""
import unittest
import platform
import numpy
import pandas
from pyquickhelper.pycode import ExtTestCase
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.datasets import load_iris
from mlprodict.testing import iris_data, check_model_representation
from mlprodict.grammar.grammar_sklearn import sklearn2graph, identify_interpreter
from mlprodict.grammar.grammar_sklearn.grammar.exc import Float32InfError
from mlprodict.grammar.cc import compile_c_function
from mlprodict.grammar.cc.c_compilation import CompilationError


class TestGrammarSklearnLinear(ExtTestCase):

    def test_sklearn_lr(self):
        lr = LogisticRegression()
        gr = identify_interpreter(lr)
        self.assertCallable(gr)

    def test_sklearn_train_lr(self):
        iris = load_iris()
        X = iris.data[:, :2]
        y = iris.target
        y[y == 2] = 1
        lr = LogisticRegression()
        lr.fit(X, y)
        gr = sklearn2graph(lr, output_names=['Prediction', 'Score'])

        X = numpy.array([[numpy.float32(1), numpy.float32(2)]])
        e1 = lr.predict(X)
        p1 = lr.decision_function(X)
        e2 = gr.execute(Features=X[0, :])
        self.assertEqual(e1[0], e2[0])
        self.assertEqualFloat(p1, e2[1])

        ser = gr.export(lang="json", hook={'array': lambda v: v.tolist()})
        self.maxDiff = None
        self.assertEqual(6, len(ser))
        # import json
        # print(json.dumps(ser, sort_keys=True, indent=2))
        # self.assertEqual(ser, exp) # training not always the same

    @unittest.skipIf(platform.system().lower() == "darwin",
                     reason="compilation issue with CFFI")
    def test_sklearn_train_lr_into_c_float(self):
        iris = load_iris()
        X = iris.data[:, :2]
        y = iris.target
        y[y == 2] = 1
        lr = LogisticRegression()
        lr.fit(X, y)
        gr = sklearn2graph(lr, output_names=['Prediction', 'Score'])

        code_c = gr.export(lang="c")['code']
        if code_c is None:
            raise ValueError("cannot be None")

        X = numpy.array([[numpy.float32(1), numpy.float32(2)]])
        try:
            fct = compile_c_function(
                code_c, 2, additional_paths=['ggg'], suffix='_float')
        except (CompilationError, RuntimeError) as e:
            if "Visual Studio is not installed" in str(e):
                return
            raise AssertionError(  # pylint: disable=W0707
                "Issue type %r exc %r." % (type(e), e))

        e2 = fct(X[0, :])
        e1 = lr.predict(X)
        p1 = lr.decision_function(X)
        self.assertEqual(e1[0], e2[0])
        self.assertEqualFloat(p1, e2[1])

    @unittest.skipIf(platform.system().lower() == "darwin",
                     reason="compilation issue with CFFI")
    def test_sklearn_train_lr_into_c_double(self):
        iris = load_iris()
        X = iris.data[:, :2]
        y = iris.target
        y[y == 2] = 1
        lr = LogisticRegression()
        lr.fit(X, y)
        gr = sklearn2graph(lr, output_names=['Prediction', 'Score'],
                           dtype=numpy.float64)

        code_c = gr.export(lang="c")['code']
        if code_c is None:
            raise ValueError("cannot be None")

        X = numpy.array([[numpy.float64(1), numpy.float64(2)]])
        try:
            fct = compile_c_function(code_c, 2, additional_paths=['ggg'],
                                     dtype=numpy.float64, suffix='_double')
        except (CompilationError, RuntimeError) as e:
            if "Visual Studio is not installed" in str(e):
                return
            raise AssertionError(  # pylint: disable=W0707
                "Issue type %r exc %r." % (type(e), e))

        e2 = fct(X[0, :])
        e1 = lr.predict(X)
        p1 = lr.decision_function(X)
        self.assertEqual(e1[0], e2[0])
        self.assertEqualFloat(p1, e2[1])

    @unittest.skipIf(platform.system().lower() == "darwin", reason="compilation issue with CFFI")
    def test_sklearn_linear_regression_verbose(self):
        X, y = iris_data()
        rows = []

        def myprint(*args, **kwargs):
            rows.append(' '.join(map(str, args)))

        try:
            check_model_representation(
                LinearRegression, X, y, verbose=True, fLOG=myprint, suffix='A')
        except (RuntimeError, CompilationError) as e:
            if "Visual Studio is not installed" in str(e):
                return
            raise AssertionError(  # pylint: disable=W0707
                "Issue type %r exc %r." % (type(e), e))
        check_model_representation(
            LinearRegression, X.tolist(), y.tolist(), verbose=True,
            fLOG=myprint, suffix='B')
        self.assertGreater(len(rows), 2)
        xdf = pandas.DataFrame(X)
        try:
            check_model_representation(
                LinearRegression, xdf, y.tolist(), verbose=True,
                fLOG=myprint, suffix='B')
        except TypeError as e:
            self.assertIn("value is not a numpy.array but", str(e))
            return
        self.assertGreater(len(rows), 2)

    def test_sklearn_train_lr_into_c(self):
        iris = load_iris()
        X = iris.data[:, :2]
        y = iris.target
        y[y == 2] = 1
        lr = LogisticRegression()
        lr.fit(X, y)

        # We replace by double too big for floats.
        lr.coef_ = numpy.array([[2.45, -3e250]])
        self.assertRaise(lambda: sklearn2graph(
            lr, output_names=['Prediction', 'Score']), Float32InfError)


if __name__ == "__main__":
    unittest.main()
