import unittest

import main


class AgentTests(unittest.TestCase):
    def test_intents(self):
        self.assertEqual(main.classify("Where is my order 10234?"), "order_status")
        self.assertEqual(main.classify("I'm not happy, wrong item"), "complaint")
        self.assertEqual(main.classify("How much are bags?"), "price")

    def test_order_lookup(self):
        r = main.handle({"from": "x", "text": "status of order 10234"})
        self.assertIn("out for delivery", r["reply"])
        self.assertFalse(r["handover"])

    def test_handover(self):
        self.assertTrue(main.handle({"from": "x", "text": "corporate gift cards?"})["handover"])


if __name__ == "__main__":
    unittest.main()
