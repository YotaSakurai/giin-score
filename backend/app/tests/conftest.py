"""テスト用の共通フィクスチャ"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.reviews import limiter as reviews_limiter
from app.database import Base, get_db
from app.main import app, limiter
from app.models.member import Member
from app.models.score import MemberScore
from app.models.session import DietSession

TEST_DATABASE_URL = "sqlite:///test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """テストごとにDBをリセット"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """テストごとにslowAPIのレート制限カウンタをリセット"""
    yield
    limiter.reset()
    reviews_limiter.reset()


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_data(db):
    """テスト用の議員・スコアデータ"""
    session = DietSession(id=1, session_number=215, kind="通常")
    db.add(session)

    members = [
        Member(
            id=1, name="田中太郎", chamber="representatives",
            party="自由民主党", district="東京1区",
        ),
        Member(
            id=2, name="鈴木花子", chamber="councillors",
            party="立憲民主党", district="東京都",
        ),
        Member(
            id=3, name="山田一郎", chamber="representatives",
            party="自由民主党", district="大阪1区",
        ),
        Member(
            id=4, name="佐藤次郎", chamber="councillors",
            party="日本維新の会", district="大阪府",
        ),
        Member(
            id=5, name="高橋三郎", chamber="representatives",
            party="立憲民主党",
        ),
    ]
    db.add_all(members)

    scores = [
        MemberScore(
            member_id=1, session_id=1,
            legislative_activity=80, voting_behavior=70, policy_influence=60,
            transparency=50, question_quality=90, total=72, grade="B",
        ),
        MemberScore(
            member_id=2, session_id=1,
            legislative_activity=90, voting_behavior=85, policy_influence=80,
            transparency=75, question_quality=95, total=86, grade="A",
        ),
        MemberScore(
            member_id=3, session_id=1,
            legislative_activity=30, voting_behavior=25, policy_influence=20,
            transparency=15, question_quality=10, total=22, grade="D",
        ),
        MemberScore(
            member_id=4, session_id=1,
            legislative_activity=50, voting_behavior=55, policy_influence=45,
            transparency=40, question_quality=60, total=50, grade="C",
        ),
        # member 5 にはスコアなし
    ]
    db.add_all(scores)
    db.commit()
    return members, scores
