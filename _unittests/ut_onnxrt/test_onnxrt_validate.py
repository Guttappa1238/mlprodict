"""
@brief      test log(time=40s)
"""
import os
import unittest
from logging import getLogger
from pandas import DataFrame, read_csv
from onnx.defs import onnx_opset_version
from pyquickhelper.loghelper import fLOG
from pyquickhelper.pycode import (
    get_temp_folder, ExtTestCase, skipif_circleci, unittest_require_at_least
)
from sklearn.exceptions import ConvergenceWarning
try:
    from sklearn.utils._testing import ignore_warnings
except ImportError:
    from sklearn.utils.testing import ignore_warnings
import skl2onnx
from mlprodict.onnxrt.validate import enumerate_validated_operator_opsets, summary_report


class TestOnnxrtValidate(ExtTestCase):

    @unittest_require_at_least(skl2onnx, '1.5.9999')
    @skipif_circleci("too long")
    @ignore_warnings(category=(UserWarning, ConvergenceWarning, RuntimeWarning))
    def test_validate_sklearn_operators_all(self):
        fLOG(__file__, self._testMethodName, OutputPrint=__name__ == "__main__")
        logger = getLogger('skl2onnx')
        logger.disabled = True
        verbose = 1 if __name__ == "__main__" else 0
        temp = get_temp_folder(__file__, "temp_validate_sklearn_operators_all")
        if False:  # pylint: disable=W0125
            rows = list(enumerate_validated_operator_opsets(
                verbose, models={"ExtraTreeClassifier"},
                opset_min=onnx_opset_version(),
                debug=True, fLOG=fLOG))
        else:
            rows = list(enumerate_validated_operator_opsets(
                verbose, debug=None, fLOG=fLOG, dump_folder=temp,
                opset_min=onnx_opset_version(),
                time_kwargs={onnx_opset_version(): dict(number=2, repeat=2)},
                n_features=[None]))
        self.assertGreater(len(rows), 1)
        df = DataFrame(rows)
        self.assertGreater(df.shape[1], 1)
        fLOG("output results")
        df.to_csv(os.path.join(temp, "sklearn_opsets_report.csv"), index=False)
        df.to_excel(os.path.join(
            temp, "sklearn_opsets_report.xlsx"), index=False)

    def test_validate_summary(self):
        this = os.path.abspath(os.path.dirname(__file__))
        data = os.path.join(this, "data", "sklearn_opsets_report.csv")
        df = read_csv(data)
        piv = summary_report(df)
        self.assertGreater(piv.shape[0], 1)
        self.assertGreater(piv.shape[1], 10)
        self.assertIn('LogisticRegression', set(piv['name']))
        temp = get_temp_folder(__file__, "temp_validate_summary")
        fLOG("output results")
        piv.to_csv(os.path.join(
            temp, "sklearn_opsets_summary.csv"), index=False)
        piv.to_excel(os.path.join(
            temp, "sklearn_opsets_summary.xlsx"), index=False)


if __name__ == "__main__":
    unittest.main()
