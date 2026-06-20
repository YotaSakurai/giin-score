"""CLAUDE.md 設計思想準拠チェッカー

GiinScoreの根本理念に反するコードパターンを静的に検出する。
CIに組み込むことで、設計思想からの逸脱を防ぐ。

検出対象:
1. スコアリングにおけるイデオロギーバイアス (政党名ハードコード)
2. スキャンダル・品性がスコアに影響するロジック
3. LLMプロンプトから設計思想キーワードが欠落
4. スコアリング重みの合計値ズレ
5. レート制限の欠如
6. セキュリティ上の問題
"""

import ast
import pathlib
import re

# プロジェクトルート
BACKEND_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
APP_DIR = BACKEND_ROOT / "app"


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _read_python_files(
    directory: pathlib.Path,
    exclude_dirs: set[str] | None = None,
) -> list[tuple[pathlib.Path, str]]:
    """指定ディレクトリ配下の .py ファイルを読み込む。"""
    exclude = exclude_dirs or {"__pycache__", ".git", "alembic"}
    results = []
    for path in directory.rglob("*.py"):
        if any(ex in path.parts for ex in exclude):
            continue
        try:
            results.append((path, path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# 1. イデオロギーバイアス検出
# ---------------------------------------------------------------------------

# スコアリングロジック内で特定政党名を条件分岐に使っていないか
_PARTY_NAMES = [
    "自民党", "自由民主党", "立憲民主", "公明党", "日本維新", "国民民主",
    "共産党", "れいわ", "社民党", "NHK", "参政党",
]
_PARTY_PATTERN = re.compile("|".join(re.escape(p) for p in _PARTY_NAMES))

# スコア計算に関わるファイル
_SCORING_FILES = {"scoring.py", "speech_quality.py"}


class TestIdeologyNeutrality:
    """スコアリングロジックがイデオロギー中立であることを検証。"""

    def test_no_party_names_in_scoring_logic(self):
        """スコアリング関連ファイルに政党名ハードコードがないこと。"""
        violations = []
        for path, content in _read_python_files(APP_DIR):
            if path.name not in _SCORING_FILES:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                # コメント行はスキップ
                stripped = line.lstrip()
                is_comment = (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'")
                )
                if is_comment:
                    continue
                match = _PARTY_PATTERN.search(line)
                if match:
                    violations.append(
                        f"{path.name}:{i} — 政党名 "
                        f"'{match.group()}' がスコアリングロジックに含まれています"
                    )
        assert not violations, (
            "イデオロギー中立の原則違反: スコアリングロジックに政党名が含まれています\n"
            + "\n".join(violations)
        )

    def test_no_party_conditional_in_scoring(self):
        """スコアリングファイルのif文で政党名を条件にしていないこと。"""
        violations = []
        for path, content in _read_python_files(APP_DIR):
            if path.name not in _SCORING_FILES:
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.IfExp)):
                    # if文のソースを取得
                    segment = ast.get_source_segment(content, node.test) or ""
                    if _PARTY_PATTERN.search(segment):
                        violations.append(
                            f"{path.name}:{node.lineno} — 政党名を条件分岐に使用"
                        )
        assert not violations, (
            "イデオロギー中立の原則違反: 政党名による条件分岐\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# 2. スキャンダル・品性の影響排除
# ---------------------------------------------------------------------------

_SCANDAL_KEYWORDS = [
    "スキャンダル", "不倫", "裏金", "逮捕", "起訴", "品性",
    "scandal", "arrest", "indictment",
]
_SCANDAL_PATTERN = re.compile("|".join(re.escape(k) for k in _SCANDAL_KEYWORDS), re.IGNORECASE)


class TestMeritocracy:
    """能力至上主義: スキャンダル・品性が能力スコアに影響しないことを検証。"""

    def test_no_scandal_factor_in_scoring(self):
        """scoring.pyにスキャンダル関連の変数・キーワードがないこと。

        speech_quality.pyのプロンプト文字列内は除外（LLMへの指示として正当な使用）。
        """
        violations = []
        for path, content in _read_python_files(APP_DIR):
            # scoring.pyのみをチェック（speech_quality.pyはプロンプト内で正当に使用）
            if path.name != "scoring.py":
                continue
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                match = _SCANDAL_PATTERN.search(line)
                if match:
                    violations.append(f"{path.name}:{i} — '{match.group()}'")
        assert not violations, (
            "能力至上主義の原則違反: スコアリングロジックにスキャンダル関連要素が含まれています\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# 3. LLMプロンプトの設計思想準拠
# ---------------------------------------------------------------------------

# プロンプトに必ず含まれるべきキーワード
_REQUIRED_PROMPT_KEYWORDS = [
    "イデオロギー",
    "与野党",
    "能力",
    "policy_relevance",
    "constructiveness",
    "expertise",
    "national_interest",
]


class TestLLMPromptCompliance:
    """LLMプロンプトが設計思想を正しく埋め込んでいることを検証。"""

    def test_system_prompt_contains_philosophy(self):
        """SYSTEM_PROMPTに必須キーワードが全て含まれていること。"""
        prompt_file = APP_DIR / "pipeline" / "speech_quality.py"
        content = prompt_file.read_text(encoding="utf-8")

        # SYSTEM_PROMPT変数を抽出
        match = re.search(r'SYSTEM_PROMPT\s*=\s*"""\\?\s*\n(.*?)"""', content, re.DOTALL)
        assert match, "SYSTEM_PROMPTが見つかりません"
        prompt_text = match.group(1)

        missing = [kw for kw in _REQUIRED_PROMPT_KEYWORDS if kw not in prompt_text]
        assert not missing, (
            f"LLMプロンプトに設計思想の必須キーワードが欠落: {missing}\n"
            "CLAUDE.mdの評価原則がプロンプトに反映されていることを確認してください"
        )

    def test_prompt_has_low_score_examples(self):
        """プロンプトに非生産的な質問の定義が含まれていること。"""
        prompt_file = APP_DIR / "pipeline" / "speech_quality.py"
        content = prompt_file.read_text(encoding="utf-8")

        required = ["スキャンダル追及", "パフォーマンス", "繰り返し"]
        match = re.search(r'SYSTEM_PROMPT\s*=\s*"""\\?\s*\n(.*?)"""', content, re.DOTALL)
        prompt_text = match.group(1) if match else ""

        missing = [kw for kw in required if kw not in prompt_text]
        assert not missing, (
            f"非生産的な質問の定義が欠落: {missing}\n"
            "CLAUDE.mdの「質疑時間の生産性」セクションを参照してください"
        )

    def test_prompt_has_high_score_examples(self):
        """プロンプトに生産的な質問の定義が含まれていること。"""
        prompt_file = APP_DIR / "pipeline" / "speech_quality.py"
        content = prompt_file.read_text(encoding="utf-8")

        required = ["改善提案", "独自の調査"]
        match = re.search(r'SYSTEM_PROMPT\s*=\s*"""\\?\s*\n(.*?)"""', content, re.DOTALL)
        prompt_text = match.group(1) if match else ""

        missing = [kw for kw in required if kw not in prompt_text]
        assert not missing, (
            f"生産的な質問の定義が欠落: {missing}\n"
            "CLAUDE.mdの「生産的な質問の定義」セクションを参照してください"
        )


# ---------------------------------------------------------------------------
# 4. スコアリング重みの整合性
# ---------------------------------------------------------------------------


class TestScoringWeightIntegrity:
    """スコアリング重みが不正に変更されていないことを検証。"""

    def test_weights_sum_to_one(self):
        """DEFAULT_WEIGHTSの合計が1.0であること。"""
        from app.services.scoring import DEFAULT_WEIGHTS

        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, (
            f"重みの合計が1.0ではありません: {total}\n"
            "重みを変更する場合は理由を記録してください"
        )

    def test_five_axes_present(self):
        """5軸が全て存在すること。"""
        from app.services.scoring import DEFAULT_WEIGHTS

        required_axes = {
            "legislative_activity",
            "voting_behavior",
            "policy_influence",
            "transparency",
            "question_quality",
        }
        assert set(DEFAULT_WEIGHTS.keys()) == required_axes, (
            f"5軸が揃っていません。期待: {required_axes}, 実際: {set(DEFAULT_WEIGHTS.keys())}"
        )

    def test_no_axis_is_zero(self):
        """どの軸も重み0ではないこと（全軸が評価に貢献すべき）。"""
        from app.services.scoring import DEFAULT_WEIGHTS

        zeros = [k for k, v in DEFAULT_WEIGHTS.items() if v <= 0]
        assert not zeros, f"重み0の軸があります: {zeros}"

    def test_no_single_axis_dominates(self):
        """単一軸の重みが50%を超えないこと。"""
        from app.services.scoring import DEFAULT_WEIGHTS

        for axis, weight in DEFAULT_WEIGHTS.items():
            assert weight <= 0.5, (
                f"{axis}の重み({weight})が50%を超えています。"
                "単一軸が支配的だとバランスの取れた評価になりません"
            )

    def test_weight_version_model_matches_default(self):
        """WeightVersionモデルの軸がDEFAULT_WEIGHTSと一致すること。"""
        from app.models.weight_version import WeightVersion
        from app.services.scoring import DEFAULT_WEIGHTS

        model_axes = {
            col.name for col in WeightVersion.__table__.columns
            if col.name in DEFAULT_WEIGHTS
        }
        assert model_axes == set(DEFAULT_WEIGHTS.keys()), (
            f"WeightVersionの軸がDEFAULT_WEIGHTSと不一致。"
            f"モデル: {model_axes}, DEFAULT: {set(DEFAULT_WEIGHTS.keys())}"
        )


# ---------------------------------------------------------------------------
# 5. APIセキュリティ
# ---------------------------------------------------------------------------


class TestAPISecurityPatterns:
    """APIエンドポイントのセキュリティパターンを検証。"""

    def test_write_endpoints_have_rate_limit(self):
        """POST/PUT/DELETEエンドポイントにレート制限があること。"""
        api_dir = APP_DIR / "api"
        violations = []
        for path, content in _read_python_files(api_dir):
            lines = content.splitlines()
            for i, line in enumerate(lines):
                # @router.post / put / delete を検出
                if re.match(r'\s*@router\.(post|put|delete)\(', line):
                    # 前後5行にlimiter.limitがあるか確認
                    surrounding = "\n".join(lines[max(0, i - 5) : min(len(lines), i + 5)])
                    if "limiter.limit" not in surrounding:
                        violations.append(
                            f"{path.name}:{i + 1} — 書き込みエンドポイントにレート制限がありません"
                        )
        assert not violations, (
            "セキュリティ違反: 書き込みエンドポイントにレート制限が必要です\n"
            + "\n".join(violations)
        )

    def test_no_raw_sql_in_api(self):
        """APIレイヤーに生SQLがないこと（SQLインジェクション防止）。"""
        api_dir = APP_DIR / "api"
        violations = []
        raw_sql_pattern = re.compile(
            r'\.execute\(\s*["\'](?:SELECT|INSERT|UPDATE|DELETE)',
            re.IGNORECASE,
        )
        for path, content in _read_python_files(api_dir):
            for i, line in enumerate(content.splitlines(), 1):
                if raw_sql_pattern.search(line):
                    violations.append(f"{path.name}:{i}")
        assert not violations, (
            "セキュリティ違反: APIレイヤーに生SQLが含まれています\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# 6. スコアリングロジックの一貫性
# ---------------------------------------------------------------------------


class TestScoringConsistency:
    """スコアリングロジックが設計原則と一貫していることを検証。"""

    def test_fallback_scores_are_neutral(self):
        """LLMフォールバック値が中立値(50)であること。"""
        path = APP_DIR / "pipeline" / "speech_quality.py"
        content = path.read_text(encoding="utf-8")

        # フォールバック値を検出
        fallback_matches = re.findall(r'result\[.+?\]\s*=\s*(\d+\.?\d*)', content)
        for val in fallback_matches:
            assert float(val) == 50.0, (
                f"LLMフォールバック値が50.0ではありません: {val}\n"
                "フォールバック時は中立値を使用すべきです"
            )

    def test_grade_boundaries_correct(self):
        """グレード境界値が正しいこと。"""
        from app.services.scoring import compute_grade

        # 境界値テスト
        assert compute_grade(80.0) == "A"
        assert compute_grade(79.9) == "B"
        assert compute_grade(60.0) == "B"
        assert compute_grade(59.9) == "C"
        assert compute_grade(40.0) == "C"
        assert compute_grade(39.9) == "D"
        assert compute_grade(20.0) == "D"
        assert compute_grade(19.9) == "F"

    def test_procedural_speech_filtering_exists(self):
        """議事進行発言のフィルタリングが実装されていること。"""
        path = APP_DIR / "pipeline" / "speech_quality.py"
        content = path.read_text(encoding="utf-8")

        assert "_is_procedural" in content, "議事進行発言フィルタリング関数が見つかりません"
        assert "SKIP_ROLE_CATEGORIES" in content, "スキップ対象role_categoryの定義が見つかりません"
        assert '"cabinet"' in content, "cabinet (閣僚) がスキップ対象に含まれていません"
        assert '"chair"' in content, "chair (議長) がスキップ対象に含まれていません"
