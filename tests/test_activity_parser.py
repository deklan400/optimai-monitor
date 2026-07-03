import unittest

from utils.activity_parser import parse_assignment_activity


class AssignmentParserTest(unittest.TestCase):
    def test_unique_assignment_states(self):
        logs = """
        successfully crawled data for assignment 019f2658-f1ac-7670-9788-d78d36ee03a9
        assignment 019f2658-f1ac-7670-9788-d78d36ee03a9 submitted successfully
        assignment 019f2672-1954-75a3-9441-06694b06752e failed
        assignment 019f2678-9329-7f58-9c5f-9b16061979af submit error
        assignment 019f2678-9329-7f58-9c5f-9b16061979af submitted successfully
        successfully crawled data for assignment 019f2677-7428-7719-b6f8-bf4d966b6051
        """

        result = parse_assignment_activity(logs)

        self.assertEqual(result["assignments"], 4)
        self.assertEqual(result["submitted"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["retried"], 1)


if __name__ == "__main__":
    unittest.main()
