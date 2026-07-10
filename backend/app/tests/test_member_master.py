"""議員マスタ (member_master.py) テスト

名前正規化・政党推定・役職推定・議員検索/作成のテスト。
"""

from sqlalchemy.orm import Session

from app.pipeline.member_master import (
    FACTION_PARTY_MAP,
    find_or_create_member,
    guess_party,
    guess_role_category,
    normalize_name,
)

# =====================================================================
# normalize_name
# =====================================================================


class TestNormalizeName:
    def test_basic(self):
        assert normalize_name("田中太郎") == "田中太郎"

    def test_fullwidth_space(self):
        assert normalize_name("田中\u3000太郎") == "田中 太郎"

    def test_multiple_spaces(self):
        assert normalize_name("田中   太郎") == "田中 太郎"

    def test_old_kanji(self):
        assert normalize_name("齋藤健") == "斎藤健"
        assert normalize_name("髙橋太郎") == "高橋太郎"
        assert normalize_name("廣田次郎") == "広田次郎"

    def test_nfkc_normalization(self):
        # 全角数字→半角数字
        assert normalize_name("田中１太郎") == "田中1太郎"

    def test_strip_whitespace(self):
        assert normalize_name("  田中太郎  ") == "田中太郎"

    def test_multiple_old_kanji(self):
        assert normalize_name("齋藤櫻子") == "斎藤桜子"


# =====================================================================
# guess_party
# =====================================================================


class TestGuessParty:
    def test_exact_match(self):
        assert guess_party("自由民主党") == "自由民主党"

    def test_abbreviation(self):
        assert guess_party("自民") == "自由民主党"
        assert guess_party("立憲") == "立憲民主党"
        assert guess_party("維新") == "日本維新の会"

    def test_mixed_faction_kept_as_is(self):
        # 混合会派からは個人の政党を導出できないため会派名をそのまま返す
        assert guess_party("自由民主党・国民の声") == "自由民主党・国民の声"
        assert guess_party("立憲民主・社民・無所属") == "立憲民主・社民・無所属"

    def test_unknown_faction(self):
        # マッピングにない会派はそのまま返す
        assert guess_party("新党X") == "新党X"

    def test_empty(self):
        assert guess_party("") is None

    def test_none(self):
        assert guess_party(None) is None

    def test_all_mappings_exist(self):
        """FACTION_PARTY_MAP の全エントリが動作する。"""
        for faction, party in FACTION_PARTY_MAP.items():
            assert guess_party(faction) == party


# =====================================================================
# guess_role_category
# =====================================================================


class TestGuessRoleCategory:
    def test_cabinet(self):
        assert guess_role_category("内閣総理大臣", "自由民主党") == "cabinet"
        assert guess_role_category("厚生労働大臣", "自由民主党") == "cabinet"
        assert guess_role_category("官房長官", "自由民主党") == "cabinet"

    def test_chair(self):
        assert guess_role_category("予算委員長", None) == "chair"
        assert guess_role_category("議長", None) == "chair"

    def test_ruling_junior(self):
        assert guess_role_category("", "自由民主党") == "ruling_junior"
        assert guess_role_category("", "公明党") == "ruling_junior"

    def test_opposition_senior(self):
        assert (
            guess_role_category("幹事長", "立憲民主党")
            == "opposition_senior"
        )
        assert (
            guess_role_category("代表", "日本維新の会")
            == "opposition_senior"
        )

    def test_opposition_junior(self):
        assert (
            guess_role_category("", "立憲民主党")
            == "opposition_junior"
        )
        assert (
            guess_role_category("", "日本共産党")
            == "opposition_junior"
        )

    def test_no_role_no_party(self):
        assert guess_role_category("", None) == "opposition_junior"

    def test_no_role_string(self):
        result = guess_role_category(None, "立憲民主党")
        assert result == "opposition_junior"


# =====================================================================
# find_or_create_member
# =====================================================================


class TestFindOrCreateMember:
    def test_create_new(self, db: Session):
        member = find_or_create_member(
            db, "田中太郎", "representatives",
            party="自由民主党", role=None,
        )
        assert member.id is not None
        assert member.name == "田中太郎"
        assert member.party == "自由民主党"
        assert member.role_category == "ruling_junior"

    def test_find_existing(self, db: Session):
        m1 = find_or_create_member(
            db, "田中太郎", "representatives",
        )
        m2 = find_or_create_member(
            db, "田中太郎", "representatives",
        )
        assert m1.id == m2.id

    def test_name_normalization(self, db: Session):
        """旧字体で作成し、新字体で検索できる。"""
        m1 = find_or_create_member(
            db, "齋藤健", "representatives",
        )
        m2 = find_or_create_member(
            db, "斎藤健", "representatives",
        )
        assert m1.id == m2.id

    def test_update_party(self, db: Session):
        """party が空だった議員に後から情報を追加。"""
        m1 = find_or_create_member(
            db, "無名太郎", "representatives",
        )
        assert m1.party is None

        m2 = find_or_create_member(
            db, "無名太郎", "representatives",
            party="自民",
        )
        assert m2.party == "自由民主党"

    def test_update_role(self, db: Session):
        """role_category が後から更新される。"""
        m1 = find_or_create_member(
            db, "田中太郎", "representatives",
            party="自由民主党",
        )
        assert m1.role_category == "ruling_junior"

        find_or_create_member(
            db, "田中太郎", "representatives",
            role="内閣総理大臣",
        )
        assert m1.role_category == "cabinet"

    def test_different_chamber_creates_separate(
        self, db: Session
    ):
        """同名でも院が異なれば別議員。"""
        m1 = find_or_create_member(
            db, "鈴木花子", "representatives",
        )
        m2 = find_or_create_member(
            db, "鈴木花子", "councillors",
        )
        assert m1.id != m2.id

    def test_faction_stored(self, db: Session):
        m = find_or_create_member(
            db, "山田太郎", "representatives",
            party="自由民主党・国民の声",
        )
        assert m.party == "自由民主党・国民の声"
        assert m.faction == "自由民主党・国民の声"
