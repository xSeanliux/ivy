# global
import math
from hypothesis import strategies as st, assume

# local
import ivy
import ivy_tests.test_ivy.helpers as helpers
from ivy_tests.test_ivy.helpers import handle_frontend_test
from ivy_tests.test_ivy.test_functional.test_nn.test_layers import (
    _assume_tf_dilation_gt_1,
)


@st.composite
def x_and_filters(draw, dim: int = 2, transpose: bool = False):
    if not isinstance(dim, int):
        dim = draw(dim)
    strides = draw(
        st.one_of(
            st.lists(st.integers(min_value=1, max_value=3), min_size=dim, max_size=dim),
            st.integers(min_value=1, max_value=3),
        )
    )
    if not transpose:
        padding = draw(
            st.one_of(
                st.sampled_from(["same", "valid"])
                if strides == 1
                else st.just("valid"),
                st.integers(min_value=1, max_value=3),
                st.lists(
                    st.integers(min_value=1, max_value=2), min_size=dim, max_size=dim
                ),
            )
        )
    else:
        padding = draw(
            st.one_of(
                st.integers(min_value=1, max_value=3),
                st.lists(
                    st.integers(min_value=1, max_value=2), min_size=dim, max_size=dim
                ),
            )
        )
    batch_size = draw(st.integers(1, 5))
    filter_shape = draw(
        helpers.get_shape(
            min_num_dims=dim, max_num_dims=dim, min_dim_size=1, max_dim_size=5
        )
    )
    dtype = draw(helpers.get_dtypes("float", full=False))
    input_channels = draw(st.integers(1, 3))
    output_channels = draw(st.integers(1, 3))
    group_list = [i for i in range(1, 3)]
    if not transpose:
        group_list = list(filter(lambda x: (input_channels % x == 0), group_list))
    else:
        group_list = list(filter(lambda x: (output_channels % x**2 == 0), group_list))
    fc = draw(st.sampled_from(group_list))
    dilations = draw(
        st.one_of(
            st.lists(st.integers(min_value=1, max_value=3), min_size=dim, max_size=dim),
            st.integers(min_value=1, max_value=3),
        )
    )
    full_dilations = [dilations] * dim if isinstance(dilations, int) else dilations
    if transpose:
        x_dim = draw(
            helpers.get_shape(
                min_num_dims=dim, max_num_dims=dim, min_dim_size=2, max_dim_size=5
            )
        )
    else:
        x_dim = []
        for i in range(dim):
            min_x = filter_shape[i] + (filter_shape[i] - 1) * (full_dilations[i] - 1)
            x_dim.append(draw(st.integers(min_x, 15)))
        x_dim = tuple(x_dim)
    if not transpose:
        output_channels = output_channels * fc
        filter_shape = (output_channels, input_channels // fc) + filter_shape
    else:
        input_channels = input_channels * fc
        filter_shape = (input_channels, output_channels // fc) + filter_shape
    x_shape = (batch_size, input_channels) + x_dim
    vals = draw(
        helpers.array_values(
            dtype=dtype[0],
            shape=x_shape,
            min_value=0.0,
            max_value=1.0,
        )
    )
    filters = draw(
        helpers.array_values(
            dtype=dtype[0],
            shape=filter_shape,
            min_value=0.0,
            max_value=1.0,
        )
    )
    bias = draw(
        helpers.array_values(
            dtype=dtype[0],
            shape=(output_channels,),
            min_value=0.0,
            max_value=1.0,
        )
    )
    if transpose:
        full_strides = [strides] * dim if isinstance(strides, int) else strides
        output_padding = draw(
            st.lists(st.integers(min_value=1, max_value=2), min_size=dim, max_size=dim)
        )
        padding = [padding] * dim if isinstance(padding, int) else padding
        for i in range(len(output_padding)):
            # ToDo: remove this when support for output_padding > padding is added
            output_padding[i] = min(padding[i], output_padding[i])
            m = min(full_strides[i], full_dilations[i])
            output_padding[i] = min(output_padding[i], m - 1)
        if draw(st.booleans()):
            output_padding = min(output_padding)
        return (
            dtype,
            vals,
            filters,
            bias,
            dilations,
            strides,
            padding,
            output_padding,
            fc,
        )
    else:
        return dtype, vals, filters, bias, dilations, strides, padding, fc


@handle_frontend_test(
    fn_tree="torch.nn.functional.conv1d",
    dtype_vals=x_and_filters(dim=1),
)
def test_torch_conv1d(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, weight, bias, dilations, strides, padding, fc = dtype_vals
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        weight=weight,
        bias=bias,
        stride=strides,
        padding=padding,
        dilation=dilations,
        groups=fc,
    )


@handle_frontend_test(
    fn_tree="torch.nn.functional.conv2d",
    dtype_vals=x_and_filters(dim=2),
)
def test_torch_conv2d(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, weight, bias, dilations, strides, padding, fc = dtype_vals
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        weight=weight,
        bias=bias,
        stride=strides,
        padding=padding,
        dilation=dilations,
        groups=fc,
    )


@handle_frontend_test(
    fn_tree="torch.nn.functional.conv3d",
    dtype_vals=x_and_filters(dim=3),
)
def test_torch_conv3d(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, weight, bias, dilations, strides, padding, fc = dtype_vals
    # ToDo: Enable gradient tests for dilations > 1 when tensorflow supports it.
    _assume_tf_dilation_gt_1(ivy.current_backend_str(), on_device, dilations)
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        weight=weight,
        bias=bias,
        stride=strides,
        padding=padding,
        dilation=dilations,
        groups=fc,
    )


def _output_shape(
        dims, dilation, stride, padding, output_padding, input_shape, weight_shape
):
    dilation, stride, padding, output_padding = map(
        lambda x: [x] * dims if isinstance(x, int) else x,
        [dilation, stride, padding, output_padding]
    )
    return [
        (input_shape[2 + i] - 1) * stride[i] - 2 * padding[i] +
        dilation[i] * (weight_shape[2 + i] - 1) + output_padding[i] + 1
        for i in range(dims)
    ]


@handle_frontend_test(
    fn_tree="torch.nn.functional.conv_transpose1d",
    dtype_vals=x_and_filters(dim=1, transpose=True),
)
def test_torch_conv_tranpose1d(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, weight, bias, dilations, strides, padding, output_pad, fc = dtype_vals
    dilations = 1   # ToDo: remove this when support for dilation > 1 is added
    assume(all(x > 0 for x in _output_shape(
        1, dilations, strides, padding, output_pad, vals.shape, weight.shape
    )))
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        weight=weight,
        bias=bias,
        stride=strides,
        padding=padding,
        output_padding=output_pad,
        groups=fc,
        dilation=dilations,
    )


@handle_frontend_test(
    fn_tree="torch.nn.functional.conv_transpose2d",
    dtype_vals=x_and_filters(dim=2, transpose=True),
)
def test_torch_conv_tranpose2d(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, weight, bias, dilations, strides, padding, output_pad, fc = dtype_vals
    dilations = 1   # ToDo: remove this when support for dilation > 1 is added
    assume(all(x > 0 for x in _output_shape(
        2, dilations, strides, padding, output_pad, vals.shape, weight.shape
    )))
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        weight=weight,
        bias=bias,
        stride=strides,
        padding=padding,
        output_padding=output_pad,
        groups=fc,
        dilation=dilations,
    )


@handle_frontend_test(
    fn_tree="torch.nn.functional.conv_transpose3d",
    dtype_vals=x_and_filters(dim=3, transpose=True),
)
def test_torch_conv_tranpose3d(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, weight, bias, dilations, strides, padding, output_pad, fc = dtype_vals
    dilations = 1   # ToDo: remove this when support for dilation > 1 is added
    assume(all(x > 0 for x in _output_shape(
        3, dilations, strides, padding, output_pad, vals.shape, weight.shape
    )))
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        weight=weight,
        bias=bias,
        stride=strides,
        padding=padding,
        output_padding=output_pad,
        groups=fc,
        dilation=dilations,
    )


@st.composite
def _fold_unfold_helper(draw, dim):
    stride = draw(
        st.one_of(
            st.lists(st.integers(min_value=1, max_value=3), min_size=dim, max_size=dim),
            st.integers(min_value=1, max_value=3),
        )
    )
    padding = draw(
        st.one_of(
            st.integers(min_value=1, max_value=3),
            st.lists(st.integers(min_value=1, max_value=2), min_size=dim, max_size=dim),
        )
    )
    dilation = draw(
        st.one_of(
            st.lists(st.integers(min_value=1, max_value=3), min_size=dim, max_size=dim),
            st.integers(min_value=1, max_value=3),
        )
    )
    kernel_size = draw(
        st.one_of(
            st.integers(min_value=1, max_value=5),
            helpers.get_shape(
                min_num_dims=dim, max_num_dims=dim, min_dim_size=1, max_dim_size=5
            ),
        )
    )
    return stride, padding, dilation, kernel_size


@st.composite
def _unfold_helper(draw, dim=2):
    stride, padding, dilation, kernel_size = draw(_fold_unfold_helper(dim))
    dilations = [dilation] * dim if isinstance(dilation, int) else dilation
    kernel_sizes = [kernel_size] * dim if isinstance(kernel_size, int) else kernel_size
    x_dim = []
    for i in range(dim):
        min_x = kernel_sizes[i] + (kernel_sizes[i] - 1) * (dilations[i] - 1)
        x_dim.append(draw(st.integers(min_x, 15)))
    batch_size = draw(st.integers(1, 5))
    input_channels = draw(st.integers(1, 3))
    x_shape = (batch_size, input_channels) + tuple(x_dim)
    dtype, [vals] = draw(
        helpers.dtype_and_values(
            available_dtypes=helpers.get_dtypes("float"),
            shape=x_shape,
            min_value=0.0,
            max_value=1.0,
        )
    )
    return dtype, vals, kernel_size, dilation, stride, padding


@handle_frontend_test(
    fn_tree="torch.nn.functional.unfold",
    dtype_vals=_unfold_helper(),
)
def test_torch_unfold(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, kernel_shape, dilations, strides, padding = dtype_vals
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        kernel_size=kernel_shape,
        dilation=dilations,
        padding=padding,
        stride=strides,
    )


@st.composite
def _fold_helper(draw, dim=2):
    stride, padding, dilation, kernel_size = draw(_fold_unfold_helper(dim))
    strides = [stride] * dim if isinstance(stride, int) else stride
    paddings = [padding] * dim if isinstance(padding, int) else padding
    dilations = [dilation] * dim if isinstance(dilation, int) else dilation
    kernel_sizes = [kernel_size] * dim if isinstance(kernel_size, int) else kernel_size
    output_shape = ()
    for i in range(dim):
        min_dim = kernel_sizes[i] + (kernel_sizes[i] - 1) * (dilations[i] - 1)
        output_shape = output_shape + (draw(st.integers(min_dim, 15)),)
    batch_size = draw(st.integers(1, 5))
    n_channels = draw(st.integers(1, 3))
    x_shape = [
        (output_shape[i] + 2 * paddings[i] - dilations[i] * (kernel_sizes[i] - 1) - 1)
        // strides[i]
        + 1
        for i in range(2)
    ]
    x_shape = (batch_size, n_channels * math.prod(kernel_sizes), math.prod(x_shape))
    dtype, [vals] = draw(
        helpers.dtype_and_values(
            available_dtypes=helpers.get_dtypes("float"),
            shape=x_shape,
            min_value=0.0,
            max_value=1.0,
        )
    )
    if vals.shape[0] == 1:  # un-batched inputs are also supported
        vals = draw(st.one_of(st.just(vals), st.just(ivy.squeeze(vals, axis=0))))
    return dtype, vals, kernel_size, output_shape, dilation, stride, padding


@handle_frontend_test(
    fn_tree="torch.nn.functional.fold",
    dtype_vals=_fold_helper(),
)
def test_torch_fold(
    *,
    dtype_vals,
    on_device,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, vals, kernel_shape, output_shape, dilations, strides, padding = dtype_vals
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=vals,
        output_size=output_shape,
        kernel_size=kernel_shape,
        dilation=dilations,
        padding=padding,
        stride=strides,
    )
