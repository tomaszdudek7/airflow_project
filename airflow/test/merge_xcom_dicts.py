import unittest

from airflow.dags.launcher.launcher import combine_xcom_values


class TestLoadXcoms(unittest.TestCase):

    def test_none_resulting_in_empty_dict(self):
        # given
        xcoms = None
        result = combine_xcom_values(xcoms)
        self.assertEqual({}, result)

    def test_empty_resulting_in_empty(self):
        # given
        xcoms = []
        result = combine_xcom_values(xcoms)
        self.assertEqual({}, result)

    def test_no_xcoms(self):
        #given
        xcoms = (None, )
        expected_result = {}
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_multiple_none_xcoms(self):
        #given
        xcoms = (None, None, None, None)
        expected_result = {}
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_multiple_none_xcoms_with_one_proper(self):
        #given
        xcoms = (None, None, {'value': 2}, None, None)
        expected_result = {'value': 2}
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_single_xcom(self):
        # given
        xcoms = (
            {
                'value': 1
            }
        )
        expected_result = {
            'value': 1
        }
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_two_xcoms_one_empty(self):
        # given
        xcoms = (
            {
                'value': 1
            },
            {}
        )
        expected_result = {
            'value': 1
        }
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_two_different_xcoms(self):
        # given
        xcoms = (
            {
                'value': 1
            },
            {
                'another_value': 2
            }
        )
        expected_result = {
            'value': 1,
            'another_value': 2
        }
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_multiple_xcoms_but_None_and_empty_should_be_filtered_out(self):
        # given
        xcoms = (
            {
                'value': 1
            },
            {},
            None,
            {
                'another_value': 2
            }
        )
        expected_result = {
            'value': 1,
            'another_value': 2
        }
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)

    def test_multiple_xcoms_last_overwriting(self):
        # given
        xcoms = (
            {
                'value': 1
            },
            {
                'value': 2
            },
            {
                'value': 3
            },
            {
                'irrelevant_value': True
            }
        )
        expected_result = {
            'value': 3,
            'irrelevant_value': True
        }
        result = combine_xcom_values(xcoms)
        self.assertEqual(expected_result, result)


if __name__ == '__main__':
    unittest.main()
