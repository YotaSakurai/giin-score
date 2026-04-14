"""スコアAPI エンドポイントのテスト"""


class TestPartyStats:
    """GET /api/v1/scores/by-party"""

    def test_party_stats_all(self, client, seed_data):
        resp = client.get("/api/v1/scores/by-party")
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        # 3政党 (自由民主党, 立憲民主党, 日本維新の会)
        assert len(items) >= 3
        parties = {i["party"] for i in items}
        assert "自由民主党" in parties
        assert "立憲民主党" in parties
        assert "日本維新の会" in parties

    def test_party_stats_has_grade_distribution(self, client, seed_data):
        resp = client.get("/api/v1/scores/by-party")
        data = resp.json()
        for item in data["items"]:
            assert "grade_distribution" in item
            gd = item["grade_distribution"]
            assert all(g in gd for g in ["A", "B", "C", "D", "F"])
            # grade_distribution の合計 == member_count
            assert sum(gd.values()) == item["member_count"]

    def test_party_stats_filter_chamber(self, client, seed_data):
        resp = client.get("/api/v1/scores/by-party?chamber=councillors")
        data = resp.json()
        assert data["chamber"] == "councillors"
        # 参議院には鈴木(立憲)と佐藤(維新)
        parties = {i["party"] for i in data["items"]}
        assert "立憲民主党" in parties
        assert "日本維新の会" in parties
        assert "自由民主党" not in parties

    def test_party_stats_sorted_by_average_score_desc(self, client, seed_data):
        resp = client.get("/api/v1/scores/by-party")
        data = resp.json()
        scores = [i["average_score"] for i in data["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_party_stats_score_values(self, client, seed_data):
        resp = client.get("/api/v1/scores/by-party")
        data = resp.json()
        ldp = next(i for i in data["items"] if i["party"] == "自由民主党")
        # 田中(72) + 山田(22) → 平均 47.0
        assert ldp["average_score"] == 47.0
        assert ldp["member_count"] == 2
        assert ldp["max_score"] == 72.0
        assert ldp["min_score"] == 22.0


class TestStats:
    """GET /api/v1/scores/stats"""

    def test_stats_all(self, client, seed_data):
        resp = client.get("/api/v1/scores/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_members"] == 4  # 5人中4人にスコアあり
        assert data["average_score"] > 0
        assert data["median_score"] > 0
        assert len(data["distribution"]) == 5

    def test_stats_filter_chamber(self, client, seed_data):
        resp = client.get("/api/v1/scores/stats?chamber=representatives")
        data = resp.json()
        # 衆議院: 田中(72), 山田(22) = 2人
        assert data["total_members"] == 2

    def test_stats_distribution_sums(self, client, seed_data):
        resp = client.get("/api/v1/scores/stats")
        data = resp.json()
        total_from_dist = sum(d["count"] for d in data["distribution"])
        assert total_from_dist == data["total_members"]

    def test_stats_empty(self, client):
        """スコアが存在しない場合"""
        resp = client.get("/api/v1/scores/stats")
        data = resp.json()
        assert data["total_members"] == 0
        assert data["average_score"] == 0.0


class TestRanking:
    """GET /api/v1/scores/ranking"""

    def test_ranking_default(self, client, seed_data):
        resp = client.get("/api/v1/scores/ranking")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        # ランク1は最高スコア
        assert data["items"][0]["rank"] == 1
        assert data["items"][0]["score"]["total"] >= data["items"][1]["score"]["total"]

    def test_ranking_sort_by_axis(self, client, seed_data):
        resp = client.get("/api/v1/scores/ranking?sort_by=question_quality")
        data = resp.json()
        qqs = [i["score"]["question_quality"] for i in data["items"]]
        assert qqs == sorted(qqs, reverse=True)

    def test_ranking_filter_party(self, client, seed_data):
        resp = client.get("/api/v1/scores/ranking?party=自由民主党")
        data = resp.json()
        assert data["total"] == 2
        assert all(i["member"]["party"] == "自由民主党" for i in data["items"])

    def test_ranking_pagination(self, client, seed_data):
        resp = client.get("/api/v1/scores/ranking?limit=2&offset=0")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["rank"] == 1

        resp2 = client.get("/api/v1/scores/ranking?limit=2&offset=2")
        data2 = resp2.json()
        assert data2["items"][0]["rank"] == 3


class TestPartiesList:
    """GET /api/v1/scores/parties"""

    def test_parties_all(self, client, seed_data):
        resp = client.get("/api/v1/scores/parties")
        assert resp.status_code == 200
        parties = resp.json()
        assert isinstance(parties, list)
        assert "自由民主党" in parties
        assert "立憲民主党" in parties

    def test_parties_filter_chamber(self, client, seed_data):
        resp = client.get("/api/v1/scores/parties?chamber=councillors")
        parties = resp.json()
        assert "立憲民主党" in parties
        assert "日本維新の会" in parties
        # 自由民主党は衆議院のみ
        assert "自由民主党" not in parties
