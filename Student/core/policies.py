from typing import Literal


Difficulty = Literal["easy", "medium", "hard"]


class AssessmentPolicy:
    """
    All hard rules for assessment & progression live here.
    """

    PASS_THRESHOLD = 0.70        # 70%
    MAX_ATTEMPTS = 3
    DIFFICULTY_ORDER = ["easy", "medium", "hard"]

    @classmethod
    def is_pass(cls, score: float) -> bool:
        return score >= cls.PASS_THRESHOLD

    @classmethod
    def can_retry(cls, attempts: int) -> bool:
        return attempts < cls.MAX_ATTEMPTS

    @classmethod
    def next_difficulty(
        cls,
        current_difficulty: Difficulty,
        score: float
    ) -> Difficulty:
        """
        Escalate difficulty only if student is performing well.
        """
        idx = cls.DIFFICULTY_ORDER.index(current_difficulty)

        if score >= 0.85 and idx < len(cls.DIFFICULTY_ORDER) - 1:
            return cls.DIFFICULTY_ORDER[idx + 1]

        return current_difficulty
