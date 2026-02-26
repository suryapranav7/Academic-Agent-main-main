from typing import Dict, List

from db.repositories.curriculum_repo import CurriculumRepository


class CurriculumTool:
    """
    Provides curriculum data to agents.
    Backed by SQLite via CurriculumRepository.
    """

    @staticmethod
    def get_curriculum(course_id: str) -> Dict:
        """
        Returns full curriculum structure for a course.
        """

        modules = CurriculumRepository.get_modules_for_course(course_id)

        curriculum = {
            "course_id": course_id,
            "modules": []
        }

        for module in modules:
            lessons = CurriculumRepository.get_lessons_for_module(
                module["module_id"]
            )

            module_data = {
                "module_id": module["module_id"],
                "module_name": module["module_name"],
                "description": module.get("description"),
                "lessons": []
            }

            for lesson in lessons:
                objectives = CurriculumRepository.get_objectives_for_lesson(
                    lesson["lesson_id"]
                )

                module_data["lessons"].append({
                    "lesson_id": lesson["lesson_id"],
                    "lesson_name": lesson["lesson_name"],
                    "objectives": objectives
                })

            curriculum["modules"].append(module_data)

        return curriculum
