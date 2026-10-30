from sqlalchemy import func, select

from app.models.problem import Problem
from app.scripts.dsa_questions import PARTS
from app.scripts.seed_problems import build_url, iter_questions, seed


def test_question_data_is_consistent():
    questions = list(iter_questions())
    assert [q.number for q in questions] == list(range(1, 251))
    assert {q.difficulty for q in questions} <= {"Easy", "Medium", "Hard"}
    assert len(PARTS) == 5
    assert all(q.title.strip() for q in questions)
    assert all(len(q.section) <= 50 and len(q.part) <= 100 for q in questions)
    assert all(len(build_url(q.title, q.leetcode_slug)) <= 500 for q in questions)


async def test_seed_adopts_old_rows_and_is_idempotent(session_factory):
    async with session_factory() as session:
        session.add_all(
            [
                Problem(slug="two-sum", title="Two Sum", difficulty="Easy",
                        topic="Arrays", url="https://leetcode.com/problems/two-sum/"),
                Problem(slug="invert-binary-tree", title="Invert Binary Tree",
                        difficulty="Easy", topic="Trees", url="https://example.com"),
            ]
        )
        await session.commit()
        old_id = await session.scalar(select(Problem.id).where(Problem.slug == "two-sum"))

        first = await seed(session)
        assert first == {"created": 249, "updated": 0, "adopted": 1, "removed": 1}
        assert await session.scalar(select(func.count(Problem.id))) == 250

        adopted = await session.scalar(select(Problem).where(Problem.number == 11))
        assert adopted.id == old_id
        assert adopted.part == "Part 1: Questions 1-50"
        assert adopted.topic == "Arrays and Prefix Sums"

        second = await seed(session)
        assert second == {"created": 0, "updated": 250, "adopted": 0, "removed": 0}
        assert await session.scalar(select(func.count(Problem.id))) == 250