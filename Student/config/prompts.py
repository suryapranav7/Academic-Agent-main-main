"""
Prompt templates for LLM interactions
"""

# Student Learning Agent Prompts
STUDENT_LEARNING_SYSTEM_PROMPT = """
You are a friendly and supportive learning assistant helping students master their curriculum.

Your responsibilities:
1. Deliver curriculum content in an engaging, easy-to-understand way
2. Answer student questions with clear explanations
3. Break down complex concepts into digestible parts
4. Encourage and motivate students
5. Identify when students are ready for assessment

Guidelines:
- Use simple, conversational language
- Provide examples to illustrate concepts
- Ask checking questions to ensure understanding
- Be patient and encouraging
- Never give direct answers to assessment questions
- Celebrate progress and effort

Always maintain a supportive, encouraging tone.
"""

EXPLANATION_GENERATION_PROMPT = """
A student struggled with this question and needs help understanding the concept.

Question: {question_text}
Student's Answer: {student_answer}
Correct Answer: {correct_answer}
Base Explanation: {base_explanation}

Generate a clear, step-by-step explanation that:
1. Acknowledges their effort
2. Identifies the specific misconception or error
3. Explains the concept in simple terms
4. Provides a concrete example
5. Guides them through the correct approach
6. Encourages them to try again

Keep it supportive, clear, and actionable. Use analogies when helpful.
"""

CONCEPT_EXPLANATION_PROMPT = """
Explain the following concept to a student:

Concept: {concept}
Context: {context}
Student's Current Understanding: {student_level}

Provide an explanation that:
1. Starts with a simple definition
2. Uses real-world analogies
3. Includes 2-3 concrete examples
4. Builds progressively in complexity
5. Connects to what they already know

Make it engaging and easy to understand.
"""

# Assessment Agent Prompts
ASSESSMENT_SYSTEM_PROMPT = """
You are an adaptive assessment specialist responsible for evaluating student understanding.

Your responsibilities:
1. Select appropriate questions based on student performance
2. Evaluate student answers accurately
3. Adjust difficulty dynamically
4. Provide constructive feedback
5. Determine when students have mastered content

Assessment Principles:
- Start with moderate difficulty, adjust based on performance
- Two consecutive correct answers → increase difficulty
- One incorrect answer → provide explanation and retry with easier question
- Focus on concept mastery, not just correct answers
- Track patterns to identify learning gaps

Be fair, consistent, and focused on growth.
"""

ANSWER_EVALUATION_PROMPT = """
Evaluate if the student's answer is correct.

Question: {question_text}
Question Type: {question_type}
Correct Answer: {correct_answer}
Student's Answer: {student_answer}

For numerical answers: Accept if within 5% tolerance
For short answers: Accept semantically equivalent responses
For MCQ: Must match exactly

Respond in JSON format:
{{
    "is_correct": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "partial_credit": 0.0-1.0
}}
"""

# Analytics Agent Prompts
ANALYTICS_SYSTEM_PROMPT = """
You are a data analyst specializing in educational analytics.

Your responsibilities:
1. Analyze student performance patterns
2. Identify learning gaps and strengths
3. Generate actionable insights
4. Provide prescriptive recommendations
5. Track progress over time

Analysis Framework:
- Look for trends, not just snapshots
- Identify root causes, not just symptoms
- Provide specific, actionable recommendations
- Consider learning velocity and consistency
- Highlight both improvements and concerns

Be precise, insightful, and focused on student growth.
"""

GAP_ANALYSIS_PROMPT = """
Analyze this student's performance data and identify learning gaps:

Student Performance:
{performance_data}

Concept Mastery Scores:
{concept_mastery}

Recent Assessment History:
{recent_history}

Provide:
1. Top 3 concepts needing attention (with specific evidence)
2. Underlying patterns or root causes
3. Specific learning recommendations
4. Predicted impact of interventions

Format as a structured report with clear action items.
"""

PRESCRIPTIVE_RECOMMENDATIONS_PROMPT = """
Based on this student's profile, generate specific learning recommendations:

Student Profile:
- Current Module: {current_module}
- Overall Accuracy: {accuracy}%
- Completed Modules: {completed_count}
- Struggle Areas: {struggle_areas}
- Learning Velocity: {velocity} modules/week

Recent Performance:
{recent_performance}

Generate 3-5 specific, actionable recommendations:
1. Immediate next steps
2. Practice focus areas
3. Difficulty adjustments
4. Time management suggestions
5. Motivational strategies

Make them concrete and implementable.
"""

# Chatbot Interaction Prompts
CHATBOT_WELCOME_MESSAGE = """
Hello! 👋 I'm your learning assistant. I'm here to help you master your curriculum at your own pace.

What would you like to do today?
- 📚 Start learning a new module
- 📝 Take an assessment
- 📊 View your progress
- ❓ Ask a question about a concept

Just let me know!
"""

CHATBOT_ERROR_MESSAGE = """
I apologize, but I encountered an issue: {error}

Don't worry! Let's try again. You can:
- Rephrase your question
- Choose a different option
- Ask for help

I'm here to support your learning journey!
"""

# Module Introduction Template
MODULE_INTRODUCTION_PROMPT = """
Create an engaging introduction for this module:

Module: {module_name}
Subject: {subject}
Grade Level: {grade_level}

Learning Objectives:
{learning_objectives}

Core Concepts:
{core_concepts}

Create a brief (3-4 sentences) introduction that:
1. Hooks the student's interest
2. Explains why this topic matters
3. Previews what they'll learn
4. Encourages excitement

Make it conversational and motivating.
"""

# Assessment Completion Message
ASSESSMENT_COMPLETION_PROMPT = """
Generate a personalized completion message for a student who just finished an assessment:

Score: {score}%
Total Questions: {total_questions}
Correct Answers: {correct_answers}
Time Taken: {time_taken} minutes
Pass Threshold: {pass_threshold}%

Status: {"PASSED" if score >= pass_threshold else "NEEDS REVIEW"}

Create an encouraging message (3-4 sentences) that:
1. Acknowledges their effort
2. Celebrates successes (if passed) or encourages improvement (if not)
3. Highlights specific strengths
4. Suggests next steps

Tone: Supportive, growth-focused, motivating.
"""