import unittest

from app.agents.router import AgentRouter
from app.schemas import QueryAnalysis


class DummyStore:
    chunks = [
        {"city": "成都", "title": "人民公园", "content": "人民公园、宽窄巷子、锦里适合城市漫游。"},
        {"city": "北京", "title": "故宫", "content": "故宫和天坛适合文化旅行。"},
    ]


class DummyRetriever:
    available_cities = ["成都", "北京"]
    store = DummyStore()

    def analyze_query(self, question: str) -> QueryAnalysis:
        city = "成都" if "成都" in question else "北京" if "北京" in question else None
        return QueryAnalysis(question=question, question_type="fact", city=city)


class AgentRouterTest(unittest.TestCase):
    def setUp(self):
        self.router = AgentRouter(DummyRetriever())

    def test_weather_query_routes_to_weather_tool(self):
        analysis = self.router.analyze_query("成都明天适合去人民公园吗？")
        self.assertEqual(analysis["intent"], "realtime_weather")
        self.assertEqual(self.router.route_task(analysis["intent"]), "weather_tool")

    def test_plain_suitability_query_does_not_route_to_weather(self):
        analysis = self.router.analyze_query("成都适合喜欢慢旅行的人吗？")
        self.assertEqual(analysis["intent"], "knowledge_qa")
        self.assertEqual(self.router.route_task(analysis["intent"]), "rag_tool")

    def test_itinerary_query_routes_to_map_tool(self):
        analysis = self.router.analyze_query("北京三天怎么玩？")
        self.assertEqual(analysis["intent"], "itinerary_plan")
        self.assertEqual(self.router.route_task(analysis["intent"]), "map_itinerary_tool")


if __name__ == "__main__":
    unittest.main()
