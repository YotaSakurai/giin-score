"""議員API エンドポイントのテスト"""


class TestListMembers:
    """GET /api/v1/members"""

    def test_list_all(self, client, seed_data):
        resp = client.get("/api/v1/members")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_filter_by_chamber(self, client, seed_data):
        resp = client.get("/api/v1/members?chamber=representatives")
        data = resp.json()
        assert data["total"] == 3
        assert all(m["chamber"] == "representatives" for m in data["items"])

    def test_filter_by_party(self, client, seed_data):
        resp = client.get("/api/v1/members?party=自由民主党")
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_search(self, client, seed_data):
        resp = client.get("/api/v1/members?search=田中")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "田中太郎"

    def test_filter_by_district(self, client, seed_data):
        resp = client.get("/api/v1/members?district=東京")
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_grade(self, client, seed_data):
        resp = client.get("/api/v1/members?grade=A,B")
        data = resp.json()
        assert data["total"] == 2
        grades = {m["latest_score"]["grade"] for m in data["items"] if m["latest_score"]}
        assert grades <= {"A", "B"}

    def test_filter_by_score_range(self, client, seed_data):
        resp = client.get("/api/v1/members?score_min=50&score_max=90")
        data = resp.json()
        # 田中(72), 鈴木(86), 佐藤(50) がマッチ
        assert data["total"] == 3

    def test_filter_by_axis_range(self, client, seed_data):
        resp = client.get("/api/v1/members?qq_min=80")
        data = resp.json()
        # 田中(90), 鈴木(95)
        assert data["total"] == 2

    def test_sort_by_total_desc(self, client, seed_data):
        resp = client.get("/api/v1/members?sort_by=total&sort_order=desc")
        data = resp.json()
        scores = [m["latest_score"]["total"] for m in data["items"] if m["latest_score"]]
        assert scores == sorted(scores, reverse=True)

    def test_sort_by_total_asc(self, client, seed_data):
        resp = client.get("/api/v1/members?sort_by=total&sort_order=asc")
        data = resp.json()
        items_with_score = [m for m in data["items"] if m["latest_score"]]
        scores = [m["latest_score"]["total"] for m in items_with_score]
        assert scores == sorted(scores)

    def test_pagination(self, client, seed_data):
        resp = client.get("/api/v1/members?per_page=2&page=1")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["pages"] == 3

        resp2 = client.get("/api/v1/members?per_page=2&page=3")
        data2 = resp2.json()
        assert len(data2["items"]) == 1

    def test_combined_filters(self, client, seed_data):
        resp = client.get("/api/v1/members?chamber=representatives&grade=B&score_min=70")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "田中太郎"


class TestMembersScatter:
    """GET /api/v1/members/scatter"""

    def test_scatter_all(self, client, seed_data):
        resp = client.get("/api/v1/members/scatter")
        assert resp.status_code == 200
        data = resp.json()
        # スコアなしのmember 5は除外
        assert len(data) == 4

    def test_scatter_has_fields(self, client, seed_data):
        resp = client.get("/api/v1/members/scatter")
        data = resp.json()
        point = data[0]
        assert "id" in point
        assert "name" in point
        assert "party" in point
        assert "chamber" in point
        assert "grade" in point
        assert "total" in point
        assert "legislative_activity" in point

    def test_scatter_filter_grade(self, client, seed_data):
        resp = client.get("/api/v1/members/scatter?grade=A")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "鈴木花子"

    def test_scatter_filter_chamber(self, client, seed_data):
        resp = client.get("/api/v1/members/scatter?chamber=councillors")
        data = resp.json()
        assert len(data) == 2

    def test_scatter_filter_score_range(self, client, seed_data):
        resp = client.get("/api/v1/members/scatter?score_min=50")
        data = resp.json()
        assert all(p["total"] >= 50 for p in data)

    def test_scatter_no_pagination(self, client, seed_data):
        """散布図はページングなしで全件返る"""
        resp = client.get("/api/v1/members/scatter")
        data = resp.json()
        assert isinstance(data, list)  # PaginatedResponseではない


class TestGetMember:
    """GET /api/v1/members/{id}"""

    def test_get_existing_member(self, client, seed_data):
        resp = client.get("/api/v1/members/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "田中太郎"

    def test_get_nonexistent_member(self, client, seed_data):
        resp = client.get("/api/v1/members/999")
        assert resp.status_code == 404
