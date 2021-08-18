"""
@file
@brief Templates to export an ONNX graph in a way it can we created again
with a python script.

.. versionadded:: 0.7
"""
from textwrap import dedent

_onnx_templates = dedent("""
    import numpy
    from onnx import numpy_helper, TensorProto
    from onnx.helper import (
        make_model, make_node, set_model_props, make_tensor, make_graph,
        make_tensor_value_info)


    def create_model():
        '''
        Converted ``{{ name }}``.

        * producer: {{ producer_name }}
        * version: {{ model_version }}
        * description: {{ doc_string }}
        {%- for key, val in sorted(metadata.items()): -%}
        * {{ key }}: {{ val }}
        {%- endfor %}
        '''
        # containers
        print('[containers]')   # verbose
        initializers = []
        nodes = []
        inputs = []
        outputs = []

        # opsets
        print('[opsets]')   # verbose
        opsets = {{ opsets }}
        target_opset = {{ target_opset }}

        # initializers
        print('[initializers]')   # verbose
        {% for name, value in initializers: %}
        {% if len(value.shape) == 0: %}
        value = numpy.array({{ value }}, dtype=numpy.{{ value.dtype }})
        {% else %}
        list_value = {{ value.ravel().tolist() }}
        value = numpy.array(list_value, dtype=numpy.{{ value.dtype }}){% if len(value.shape) > 1: %}.reshape({{ value.shape }}){% endif %}
        {% endif %}
        tensor = numpy_helper.from_array(value, name='{{ name }}')
        initializers.append(tensor)
        {% endfor %}

        # inputs
        print('[inputs]')   # verbose
        {% for name, type, shape in inputs: %}
        value = make_tensor_value_info('{{ name }}', {{ type }}, {{ shape }})
        inputs.append(value)
        {% endfor %}

        # outputs
        print('[outputs]')   # verbose
        {% for name, type, shape in outputs: %}
        value = make_tensor_value_info('{{ name }}', {{ type }}, {{ shape }})
        outputs.append(value)
        {% endfor %}

        # nodes
        print('[nodes]')   # verbose
        {% for node in nodes: %}
        node = make_node(
            '{{ node['op_type'] }}',
            {{ node['inputs'] }},
            {{ node['outputs'] }},
            {% if node['name']: %}name='{{ node['name'] }}',{% endif %}
            {%- for name, value in node['attributes']: -%}
            {{ name }}={{ value }},
            {%- endfor -%}
            domain='{{ node['domain'] }}')
        nodes.append(node)
        {% endfor %}

        # graph
        print('[graph]')   # verbose
        graph = make_graph(nodes, '{{ name }}', inputs, outputs, initializers)
        onnx_model = make_model(graph)
        onnx_model.ir_version = {{ ir_version }}
        onnx_model.producer_name = '{{ producer_name }}'
        onnx_model.producer_version = '{{ producer_version }}'
        onnx_model.domain = '{{ domain }}'
        onnx_model.model_version = {{ model_version }}
        onnx_model.doc_string = '{{ doc_string }}'
        set_model_props(onnx_model, {{ metadata }})

        # opsets
        print('[opset]')   # verbose
        del onnx_model.opset_import[:]  # pylint: disable=E1101
        for dom, value in opsets.items():
            op_set = onnx_model.opset_import.add()
            op_set.domain = dom
            op_set.version = value

        return onnx_model


    onnx_model = create_model()
""")


_tf2onnx_templates = dedent("""
    import inspect
    import collections
    import numpy
    from onnx import AttributeProto, TensorProto
    from onnx.helper import (
        make_model, make_node, set_model_props, make_tensor, make_graph,
        make_tensor_value_info)
    # from tf2onnx.utils import make_name, make_sure, map_onnx_to_numpy_type
    from mlprodict.onnx_tools.exports.tf2onnx_helper import (
        make_name, make_sure, map_onnx_to_numpy_type)
    # from tf2onnx.handler import tf_op
    # from tf2onnx.graph_builder import GraphBuilder
    from mlprodict.onnx_tools.exports.tf2onnx_helper import (
        tf_op, Tf2OnnxConvert, GraphBuilder)


    @tf_op("{{ name }}")
    class Convert{{ name }}Op:

        supported_dtypes = [
            numpy.float32,
        ]

        @classmethod
        def any_version(cls, opset, ctx, node, **kwargs):
            '''
            Converter for ``{{ name }}``.

            * producer: {{ producer_name }}
            * version: {{ model_version }}
            * description: {{ doc_string }}
            {%- for key, val in sorted(metadata.items()): -%}
            * {{ key }}: {{ val }}
            {%- endfor %}
            '''
            oldnode = node
            input_name = node.input[0]
            onnx_dtype = ctx.get_dtype(input_name)
            np_dtype = map_onnx_to_numpy_type(onnx_dtype)
            make_sure(np_dtype in Convert{{ name }}Op.supported_dtypes, "Unsupported input type.")
            shape = ctx.get_shape(input_name)
            varx = {x: x for x in node.input}

            # initializers
            if getattr(ctx, 'verbose', False):
                print('[initializers] %r' % cls)
            {% for name, value in initializers: %}
            {% if len(value.shape) == 0: -%}
            value = numpy.array({{ value }}, dtype=numpy.{{ value.dtype }})
            {%- else -%}
            {% if value.size > 5: -%}
            list_value = {{ value.ravel().tolist() }}
            value = numpy.array(list_value, dtype=numpy.{{ value.dtype }}){% if len(value.shape) > 1: %}.reshape({{ value.shape }}){% endif %}
            {%- else -%}
            value = numpy.array({{ value.ravel().tolist() }}, dtype=numpy.{{ value.dtype }}){%-
                if len(value.shape) > 1: %}.reshape({{ value.shape }}){% endif %}
            {%- endif -%}{%- endif %}
            varx['{{ name }}'] = ctx.make_const(name=make_name('init_{{ name }}'), np_val=value).name
            {% endfor %}

            # nodes
            if getattr(ctx, 'verbose', False):
                print('[nodes] %r' % cls)
            {% for node in nodes: %}
            {{ make_tf2onnx_code(target_opset, **node) }}
            {% endfor %}

            # finalize
            if getattr(ctx, 'verbose', False):
                print('[replace_all_inputs] %r' % cls)
            ctx.replace_all_inputs(oldnode.output[0], node.output[0])
            ctx.remove_node(oldnode.name)

        @classmethod
        def version_13(cls, ctx, node, **kwargs):
            return cls.any_version(13, ctx, node, **kwargs)


    def create_model():
        inputs = []
        outputs = []

        # inputs
        print('[inputs]')   # verbose
        {% for name, type, shape in inputs: %}
        value = make_tensor_value_info('{{ name }}', {{ type }}, {{ shape }})
        inputs.append(value)
        {% endfor %}

        # outputs
        print('[outputs]')   # verbose
        {% for name, type, shape in outputs: %}
        value = make_tensor_value_info('{{ name }}', {{ type }}, {{ shape }})
        outputs.append(value)
        {% endfor %}

        inames = [i.name for i in inputs]
        onames = [i.name for i in outputs]
        node = make_node('{{ name }}', inames, onames, name='{{ name }}')

        # graph
        print('[graph]')   # verbose
        graph = make_graph([node], '{{ name }}', inputs, outputs)
        onnx_model = make_model(graph)
        onnx_model.ir_version = {{ ir_version }}
        onnx_model.producer_name = '{{ producer_name }}'
        onnx_model.producer_version = '{{ producer_version }}'
        onnx_model.domain = '{{ domain }}'
        onnx_model.model_version = {{ model_version }}
        onnx_model.doc_string = '{{ doc_string }}'
        set_model_props(onnx_model, {{ metadata }})

        # opsets
        print('[opset]')   # verbose
        opsets = {{ opsets }}
        del onnx_model.opset_import[:]  # pylint: disable=E1101
        for dom, value in opsets.items():
            op_set = onnx_model.opset_import.add()
            op_set.domain = dom
            op_set.version = value

        return onnx_model


    onnx_raw = create_model()
    onnx_model = Tf2OnnxConvert(onnx_raw, tf_op, target_opset={{ opsets }}).run()
""")


_numpy_templates = dedent("""
    import numpy
    from mlprodict.onnx_tools.exports.numpy_helper import (
        argmin_use_numpy_select_last_index,
        make_slice)

    def numpy_{{name}}({{ inputs[0][0] }}{% for i in inputs[1:]: %}, {{ i[0] }}{% endfor %}):
        '''
        Numpy function for ``{{ name }}``.

        * producer: {{ producer_name }}
        * version: {{ model_version }}
        * description: {{ doc_string }}
        {%- for key, val in sorted(metadata.items()): -%}
        * {{ key }}: {{ val }}
        {%- endfor %}
        '''
        # initializers
        {% for name, value in initializers: -%}
        {% if name not in skip_inits: -%}
        {% if len(value.shape) == 0: -%}
        {{ name }} = numpy.array({{ value }}, dtype=numpy.{{ value.dtype }})
        {%- else %}{% if value.size < 10: %}
        {{ name }} = numpy.array({{ value.ravel().tolist() }}, dtype=numpy.{{ value.dtype }})
        {%- if len(value.shape) > 1: -%}.reshape({{ value.shape }}){%- endif %}
        {% else %}
        list_value = {{ value.ravel().tolist() }}
        {{ name }} = numpy.array(list_value, dtype=numpy.{{ value.dtype }}){% if len(value.shape) > 1: %}.reshape({{ value.shape }}){% endif %}
        {% endif %}{% endif %}{% endif %}
        {%- endfor %}

        # nodes
        {% for node in nodes: %}
        {{ make_numpy_code(target_opset, **node) }}{% endfor %}

        return {{ outputs[0][0] }}{% for o in outputs[1:]: %}, {{ o[0] }}{% endfor %}
""")
