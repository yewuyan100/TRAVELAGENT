import unittest

from app.rag.retriever import QueryAnalyzer


class QueryAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = QueryAnalyzer(
            available_cities=["成都", "杭州", "西安", "重庆", "厦门"],
            available_tags=["美食", "慢生活", "休闲", "海滨", "历史", "古都"],
        )

    def test_recommendation_question_extracts_city_and_tags(self):
        analysis = self.analyzer.analyze("成都适合慢节奏旅行吗")

        self.assertEqual(analysis.question_type, "recommendation")
        self.assertEqual(analysis.city, "成都")
        self.assertIn("audience", analysis.categories)
        self.assertIn("慢生活", analysis.tags)
        self.assertFalse(analysis.needs_realtime)

    def test_realtime_question_is_detected_before_local_rag(self):
        analysis = self.analyzer.analyze("东京迪士尼今天几点开门")

        self.assertEqual(analysis.question_type, "realtime")
        self.assertTrue(analysis.needs_realtime)
        self.assertIn("东京", analysis.entities)
        self.assertIn("迪士尼", analysis.entities)

    def test_empty_question_is_missing(self):
        analysis = self.analyzer.analyze("   ")

        self.assertEqual(analysis.question_type, "missing")


if __name__ == "__main__":
    unittest.main()

