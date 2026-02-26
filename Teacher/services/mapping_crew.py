from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import os
import json

class MappingCrew:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    def create_crew(self, modules_list, cos_list):
        # 1. Define Agent
        aligner = Agent(
            role='Academic Quality Assurance Specialist',
            goal='Map teaching modules to relevant Course Outcomes (COs) strictly based on content alignment.',
            backstory="""You are an expert in Outcome-Based Education (OBE). 
            Your job is to ensure that every teaching module contributes to specific, measurable learning outcomes.
            You analyze the content of modules and the descriptions of COs to propose semantic alignments.
            You are precise and avoid over-mapping. You strictly adhere to the provided IDs.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # 2. Define Task
        mapping_task = Task(
            description=f"""
            Analyze the following Modules and Course Outcomes (COs) to create a mapping.

            MODULES:
            {json.dumps(modules_list, indent=2)}

            COURSE OUTCOMES:
            {json.dumps(cos_list, indent=2)}

            TASKS:
            1. For each Module, identify which COs it contributes to.
            2. Match based on the 'unit_title'/'topics' of the Module and the 'description' of the CO.
            3. A Module can map to MULTIPLE COs (Max 3).
            4. A CO can be mapped to MULTIPLE Modules.
            5. If a Module has no clear CO alignment, return an empty list for it.

            OUTPUT FORMAT:
            Return a valid JSON object where keys are 'module_id' and values are lists of 'co_id'.
            Example:
            {{
                "DS-U1": ["CO1", "CO2"],
                "DS-U2": ["CO2"]
            }}
            
            IMPORTANT: Return ONLY the JSON object. Do not include markdown formatting or explanations.
            """,
            expected_output="A JSON object mapping module_ids to lists of co_ids.",
            agent=aligner
        )

        # 3. Create Crew
        crew = Crew(
            agents=[aligner],
            tasks=[mapping_task],
            verbose=True,
            process=Process.sequential
        )

        return crew

    def run(self, modules, cos):
        crew = self.create_crew(modules, cos)
        result = crew.kickoff()
        
        # Clean up result if it contains markdown formatting
        raw_output = str(result)
        if hasattr(result, 'raw'):
            raw_output = result.raw
            
        cleaned_output = raw_output.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned_output)
        except json.JSONDecodeError:
            print(f"❌ JSON Decode Error in Mapping Crew: {cleaned_output}")
            return {}
