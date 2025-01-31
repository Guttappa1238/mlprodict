"""
@file
@brief Class ShapeResult
"""
from enum import Enum
import numpy
from .shape_excs import ShapeInferenceException


class OnnxKind(Enum):
    """
    Describes a result type.
    """
    Tensor = 0
    Sequence = 1
    Map = 2


class ShapeConstraint:
    """
    One constraint.

    :param name: variable name
    :param values: set of possible values
    """

    def __init__(self, name, values):
        if name == '?':
            raise ValueError(  # pragma: no cover
                "Name cannot be '?'.")
        if not isinstance(values, set):
            raise TypeError(  # pragma: no cover
                "values must be a set not %r." % type(values))
        self.name = name
        self.values = values

    def __eq__(self, other):
        "usual"
        if self.name != other.name:
            return False
        if self.values != other.values:
            return False
        return True

    def __repr__(self):
        "usual"
        return "%s(%r, %r)" % (
            self.__class__.__name__, self.name, self.values)

    def merge(self, cst):
        """
        Merges this constraint with *cst* into this one.
        """
        if isinstance(cst, list):
            for c in cst:
                self.merge(c)
            return
        self.values = self.values.intersection(cst.values)

    def copy(self, deep=False):
        """
        Makes a copy of the object.
        """
        return ShapeConstraint(self.name, self.values.copy())


class ShapeConstraintList:
    """
    A list of ShapeConstraint.
    """

    def __init__(self):
        self.csts = []

    def __contains__(self, cst):
        for a in self.csts:
            if cst == a:
                return True
        return False

    def append(self, cst):
        "Appends a new constraint to the list."
        self.csts.append(cst)

    def __repr__(self):
        return "ShapeConstraintList(%r)" % self.csts

    def __iter__(self):
        for c in self.csts:
            yield c

    def __len__(self):
        return len(self.csts)

    def copy(self, deep=False):
        """
        Copies the object.
        """
        cp = ShapeConstraintList()
        if deep:
            cp.csts = [v.copy(deep=deep) for v in self]
        else:
            cp.csts = self.csts.copy()
        return cp


class ShapeResult:
    """
    Contains information about shape and type of a result
    in an onnx graph.

    :param name: result name
    :param shape: shape if the result is a tensor
    :param dtype: element type if the result is a tensor
    :param sparse: is the tensor sparse
    :param mtype: kind of the result (see class @see cl OnnxKind)
    :param constraints: list of constraints applying on variables
    """

    def __init__(self, name, shape=None, dtype=None, sparse=False,
                 mtype=OnnxKind.Tensor, constraints=None):
        if not isinstance(name, str):
            raise TypeError(  # pragma: no cover
                "name must be a string not %r." % type(name))
        if not isinstance(sparse, bool):
            raise TypeError(  # pragma: no cover
                "sparse must be a boolean not %r." % sparse)
        if not isinstance(mtype, OnnxKind):
            raise TypeError(  # pragma: no cover
                "mtype must be of type OnnxKind not %r." % type(mtype))
        self.shape = list(shape)
        for i in range(0, len(self.shape)):  # pylint: disable=C0200
            if shape[i] in ('', None, '?'):
                raise ValueError(  # pragma: no cover
                    "All dimensions must an int or a variable name, "
                    "%s is not." % (shape, ))
        self.name = name
        self.mtype = mtype
        self.dtype = dtype
        self.sparse = sparse
        if constraints is None:
            self.constraints = ShapeConstraintList()
        elif isinstance(constraints, ShapeConstraintList):
            self.constraints = constraints
        else:
            raise TypeError(  # pragma: no cover
                "constraints must be of type(ShapeConstraintList).")

    def is_compatible(self, shape):
        """
        Tells if this shape is compatible with the given tuple.

        :param shape: tuple
        :return: boolean
        """
        if isinstance(shape, numpy.ndarray):
            shape = shape.shape
        if all(map(lambda x: isinstance(x, int), self.shape)):
            return tuple(self.shape) == tuple(shape)
        raise NotImplementedError("%r ? %r" % (self, shape))

    def copy(self, deep=False):
        """
        Returns a copy for the result.
        """
        return ShapeResult(self.name, self.shape, self.dtype, self.sparse,
                           self.mtype, self.constraints.copy(deep=deep))

    def __repr__(self):
        """
        Usual
        """
        if len(self.constraints) > 0:
            return "%s(%r, %r, %r, sparse=%r, mtype=%r, constraints=%r)" % (
                self.__class__.__name__, self.name, self.shape, self.dtype,
                self.sparse, self.mtype, self.constraints)
        if self.mtype != OnnxKind.Tensor:
            return "%s(%r, %r, %r, sparse=%r, mtype=%r)" % (
                self.__class__.__name__, self.name, self.shape, self.dtype,
                self.sparse, self.mtype)
        if self.sparse:
            return "%s(%r, %r, %r,sparse=%r)" % (
                self.__class__.__name__, self.name, self.shape, self.dtype,
                self.sparse)
        return "%s(%r, %r, %r)" % (
            self.__class__.__name__, self.name, self.shape, self.dtype)

    def __eq__(self, shape):
        """
        Tells if two shapes are identical.
        """
        return (self.mtype == shape.mtype and self.shape == shape.shape and
                self.dtype == shape.dtype and self.sparse == shape.sparse)

    def n_dims(self):
        """
        Returns the number of dimensions if it is a tensor.
        Raises an exception otherwise.
        """
        if self.mtype != OnnxKind.Tensor:
            raise ShapeInferenceException(  # pragma: no cover
                "This shape is not a tensor %r." % self)
        return len(self.shape)

    def merge(self, other_result):
        """
        Merges constraints from *other_results* into *self*.
        """
        if self.mtype != other_result.mtype:
            raise RuntimeError(  # pragma: no cover
                "Unable to merge %r and %r." % (self, other_result))
        if (len(self.shape) != 0 and len(other_result.shape) != 0 and
                len(self.shape) != len(other_result.shape)):
            raise RuntimeError(  # pragma: no cover
                "Length mismatch, unable to merge %r and %r." % (
                    self, other_result))
        updated = False
        if other_result.constraints is not None:
            for c in other_result.constraints:
                if c not in self.constraints:
                    self.constraints.append(c)
                    updated = True

        if len(self.shape) == 0 and len(other_result.shape) > 0:
            # Then self.shape is unknown and the other one is.
            self.shape = other_result.shape.copy()
            return True

        for a, b in zip(self.shape, other_result.shape):
            if a == b:
                continue
            if isinstance(a, int) and isinstance(b, int):
                raise RuntimeError(
                    "Inconsistancy between %r and %r." % (
                        self, other_result))
            elif isinstance(a, str):
                c = ShapeConstraint(a, {b})
                if c not in self.constraints:
                    updated = True
                    self.constraints.append(c)
            elif isinstance(b, str):
                c = ShapeConstraint(b, {a})
                if c not in self.constraints:
                    updated = True
                    self.constraints.append(c)
            else:
                raise NotImplementedError(  # pragma: no cover
                    "Merge not implemented between %r and %r." % (
                        self, other_result))
        return updated

    def resolve(self, variables):
        """
        Results variables in a shape using values stored
        in *variables*. It does not copy any constraints.

        :param variables: dictionary `{ name: values }`
        :return: new ShapeResult
        """
        res = ShapeResult(self.name, shape=self.shape, dtype=self.dtype,
                          sparse=self.sparse, mtype=self.mtype)
        for i in range(len(res.shape)):  # pylint: disable=C0200
            v = res.shape[i]
            if isinstance(v, str):
                if v in variables:
                    vals = variables[v]
                    if vals is None:
                        # size unknown
                        continue
                    if len(vals) == 1:
                        res.shape[i] = list(vals)[0]
                    else:
                        res.shape[i] = set(vals)
                else:
                    raise RuntimeError(  # pragma: no cover
                        "Unable to resolve shape %r due to missing "
                        "%r." % (self, v))
        return res

    @staticmethod
    def broadcast(sh1, sh2, name=None):
        """
        Broadcasts dimensions for an element wise operator.

        :param sh1: ShapeResult
        :param sh2: ShapeResult
        :param name: name of the output ShapeResult
        :return: ShapeResult
        """
        if not isinstance(sh1, ShapeResult):
            raise TypeError(  # pragma: no cover
                "Unexpected type for sh1 %r." % type(sh1))
        if not isinstance(sh2, ShapeResult):
            raise TypeError(  # pragma: no cover
                "Unexpected type for sh2 %r." % type(sh2))
        if sh1.mtype != OnnxKind.Tensor:
            raise TypeError(  # pragma: no cover
                "sh1 must be a tensor not %r." % sh1.mtype)
        if sh2.mtype != OnnxKind.Tensor:
            raise TypeError(  # pragma: no cover
                "sh2 must be a tensor not %r." % sh2.mtype)
        if sh1.n_dims() != sh2.n_dims():
            if sh1.n_dims() == 1 and sh1.shape[0] == 1:
                return ShapeResult(
                    name, sh2.shape, sh2.dtype, sh2.sparse, sh2.mtype)
            if sh2.n_dims() == 1 and sh2.shape[0] == 1:
                return ShapeResult(
                    name, sh1.shape, sh1.dtype, sh1.sparse, sh1.mtype)
            raise ShapeInferenceException(  # pragma: no cover
                "Broadcasting is only implemented for shape of the same "
                "size, shapes are %r and %r." % (sh1, sh2))
        if sh1.dtype != sh2.dtype:
            raise ShapeInferenceException(  # pragma: no cover
                "Cannot broadcast shapes %r and %r (dtypes)."
                "" % (sh1, sh2))

        constraints = ShapeConstraintList()
        shape = []
        for a, b in zip(sh1.shape, sh2.shape):
            if isinstance(a, int) and isinstance(b, int):
                if a != b:
                    if min(a, b) == 1:
                        d = max(a, b)
                    else:
                        raise ShapeInferenceException(  # pragma: no cover
                            "Cannot broadcast shapes %r and %r (dimensions)."
                            "" % (sh1, sh2))
                else:
                    d = a
            elif isinstance(a, int):
                if a != 1:
                    d = a
                    constraints.append(ShapeConstraint(b, {1, a}))
                else:
                    d = b
            elif isinstance(b, int):
                if b != 1:
                    d = b
                    constraints.append(ShapeConstraint(a, {1, b}))
                else:
                    d = a
            elif a == b:
                d = a
            else:
                raise ShapeInferenceException(  # pragma: no cover
                    "Cannot broadcast shapes %r and %r." % (sh1, sh2))
            shape.append(d)
        if name in (None, ''):
            raise ValueError(  # pragma: no cover
                "name cannot be empty.")
        res = ShapeResult(name, shape, sh1.dtype, sh1.sparse or sh2.sparse,
                          sh1.mtype, constraints)
        return res
