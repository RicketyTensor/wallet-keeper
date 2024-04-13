import collections


def assert_equal_dict(a: dict, b: dict):
    if not a.keys() == b.keys():
        raise AssertionError("Dictonaries don't have the same keys\na: {}\nb: {}".format(
            list(a.keys()), list(b.keys())))

    for key in a.keys():
        assert_equal(a[key], b[key])


def assert_equal_list(a: list, b: list):
    if len(a) != len(b):
        raise AssertionError("List have different lengths\na: {}\nb: {}".format(
            a, b))

    for i in range(len(a)):
        assert_equal(a[i], b[i])



def assert_equal_values(a, b):
    if a != b:
        raise AssertionError("Non equal values found\na: {}\nb: {}".format(
            a, b))


def assert_equal(a, b):
    if isinstance(a, dict):
        assert_equal_dict(a, b)
    elif isinstance(a, list):
        assert_equal_list(a, b)
    else:
        assert_equal_values(a, b)
