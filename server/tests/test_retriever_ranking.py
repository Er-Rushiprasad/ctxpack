"""Regression tests for a real ranking bug (see PLAN.md / ARCHI.md §4.3):
BM25 stopword contamination, phantom ranking from tied-zero BM25 scores,
and snake_case/camelCase identifiers never matching their constituent
words. Uses a hermetic fixture (not the shared E:/test-repo one) so the
content is controlled and doesn't include adversarial self-referential text
that trips up negation-blind retrieval (see the session's written report for
that separate, unfixed-by-design finding).

These are integration tests, not pure unit tests — they call index_repo,
which runs the real embedding model and hits the shared Chroma/SQLite store
under server/.data/. Each test cleans up its own repo_id afterward.
"""

from pathlib import Path

import pytest

from app.services.indexer import _connect_sqlite, get_chroma_collection, index_repo
from app.services.retriever import hybrid_search


def _write(root: Path, rel_path: str, content: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def ranking_fixture_repo_id(tmp_path: Path):
    _write(
        tmp_path,
        "auth/auth.py",
        '"""Login and session handling."""\n'
        "def login(username, password):\n"
        "    user = find_user(username)\n"
        "    if not verify_password(user, password):\n"
        "        raise InvalidCredentialsError\n"
        "    return start_session(user)\n",
    )
    _write(
        tmp_path,
        "auth/models.py",
        '"""User model with login credentials."""\n'
        "class User:\n"
        "    def __init__(self, email, password_hash):\n"
        "        self.email = email\n"
        "        self.password_hash = password_hash\n",
    )
    _write(
        tmp_path,
        "frontend/LoginForm.tsx",
        "// React login form component\n"
        "export function LoginForm() {\n"
        "  const [username, setUsername] = useState('');\n"
        "  const [password, setPassword] = useState('');\n"
        "  return <form>{/* login fields */}</form>;\n"
        "}\n",
    )
    _write(
        tmp_path,
        "tests/test_auth.py",
        "def test_login_rejects_wrong_password():\n"
        "    with pytest.raises(InvalidCredentialsError):\n"
        "        login('user@example.com', 'wrong')\n",
    )
    _write(
        tmp_path,
        "backend/payments.py",
        '"""Stripe checkout and refund handling."""\n'
        "def create_checkout_session(plan, amount_cents):\n"
        "    return {'session_id': generate_id(), 'plan': plan}\n"
        "\n"
        "def refund(session_id, reason):\n"
        "    return {'session_id': session_id, 'status': 'refunded'}\n",
    )
    _write(
        tmp_path,
        "frontend/Dashboard.tsx",
        "// Revenue chart dashboard, unrelated to login\n"
        "export function Dashboard() {\n"
        "  return <LineChart data={monthlyRevenue} />;\n"
        "}\n",
    )
    _write(
        tmp_path,
        "config/settings.py",
        '"""App settings loaded from environment."""\n'
        "import os\n"
        'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")\n'
        'JWT_SECRET = os.getenv("JWT_SECRET", "unset")\n',
    )
    _write(tmp_path, ".gitignore", "__pycache__/\n*.pyc\n.env\n")

    result = index_repo(str(tmp_path))
    yield result.repo_id

    # Teardown: remove this test's chunks/repo row so repeated runs don't
    # accumulate stale entries in the shared dev store.
    get_chroma_collection().delete(where={"repo_id": result.repo_id})
    conn = _connect_sqlite()
    with conn:
        conn.execute("DELETE FROM chunks WHERE repo_id = ?", (result.repo_id,))
        conn.execute("DELETE FROM repos WHERE repo_id = ?", (result.repo_id,))
    conn.close()


def _max_score_by_file(repo_id: str, query: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for chunk in hybrid_search(repo_id, query).chunks:
        scores[chunk.file_path] = max(scores.get(chunk.file_path, 0.0), chunk.score)
    return scores


def test_gitignore_never_appears_in_results(ranking_fixture_repo_id):
    for query in ["optimize the database query performance", "fix the auth bug in login flow"]:
        result = hybrid_search(ranking_fixture_repo_id, query)
        assert not any(c.file_path.endswith(".gitignore") for c in result.chunks)


def test_database_query_ranks_settings_above_payments(ranking_fixture_repo_id):
    scores = _max_score_by_file(ranking_fixture_repo_id, "optimize the database query performance")
    assert scores["config/settings.py"] > scores["backend/payments.py"]


def test_auth_cluster_outranks_unrelated_files(ranking_fixture_repo_id):
    scores = _max_score_by_file(ranking_fixture_repo_id, "fix the auth bug in login flow")
    auth_cluster = ["auth/auth.py", "auth/models.py", "frontend/LoginForm.tsx", "tests/test_auth.py"]
    unrelated = ["backend/payments.py", "frontend/Dashboard.tsx"]

    min_auth_score = min(scores[f] for f in auth_cluster)
    max_unrelated_score = max(scores[f] for f in unrelated)
    assert min_auth_score > max_unrelated_score


def test_confidence_is_normal_for_a_real_match(ranking_fixture_repo_id):
    result = hybrid_search(ranking_fixture_repo_id, "fix the auth bug in login flow")
    assert result.confidence == "normal"


def test_confidence_is_low_for_a_query_with_no_real_match(ranking_fixture_repo_id):
    result = hybrid_search(ranking_fixture_repo_id, "refactor the CSS grid for mobile responsiveness")
    assert result.confidence == "low"
