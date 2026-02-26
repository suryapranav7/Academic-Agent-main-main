from db.supabase_client import get_supabase

class StudentRepository:

    @staticmethod
    def create_student(student_id: str, student_name: str = None, grade: str = "9"):
        supabase = get_supabase()
        data = {"student_id": student_id, "name": student_name, "grade": grade}
        # Upsert in Supabase
        supabase.table("students").upsert(data).execute()

    @staticmethod
    def get_student(student_id: str):
        supabase = get_supabase()
        response = supabase.table("students").select("*").eq("student_id", student_id).execute()
        return response.data[0] if response.data else None


    @staticmethod
    def get_module_progress(student_id: str):
        supabase = get_supabase()
        
        # 1. Fetch Status Data
        response = supabase.table("student_module_status")\
            .select("module_id, status, best_score, modules(module_order, subject_id)")\
            .eq("student_id", student_id)\
            .order("modules(module_order)")\
            .execute()
        
        # 2. Fetch Attempts Counts
        attempts_resp = supabase.table("student_attempts")\
            .select("module_id")\
            .eq("student_id", student_id)\
            .execute()
            
        attempts_map = {}
        for row in attempts_resp.data:
            mid = row["module_id"]
            attempts_map[mid] = attempts_map.get(mid, 0) + 1

        # Parse result
        result = []
        for row in response.data:
            # Flatten nested join
            mod_data = row.get("modules") or {}
            mod_order = mod_data.get("module_order") if mod_data else 999
            subject_id = mod_data.get("subject_id")
            mod_id = row["module_id"]
            
            result.append({
                "module_id": mod_id,
                "subject_id": subject_id,
                "status": row["status"],
                "best_score": row["best_score"],
                "module_order": mod_order,
                "attempts": attempts_map.get(mod_id, 0)
            })
            
        # FIX: Explicitly sort by sequence to ensure "Next Module" logic works
        result.sort(key=lambda x: x["module_order"])
            
        return result

    @staticmethod
    def update_module_status(
        student_id: str,
        module_id: str,
        status: str,
        best_score: float = 0.0
    ):
        supabase = get_supabase()
        
        # We need to handle the "MAX(best_score)" logic manually or use a procedure.
        # Or read-then-write.
        # Upsert overrides.
        
        # 1. Fetch current best
        current = supabase.table("student_module_status")\
            .select("best_score")\
            .eq("student_id", student_id)\
            .eq("module_id", module_id)\
            .execute()
            
        current_max = 0.0
        if current.data:
            current_max = float(current.data[0]["best_score"] or 0.0)
            
        new_max = max(current_max, best_score)
        
        data = {
            "student_id": student_id,
            "module_id": module_id,
            "status": status,
            "best_score": new_max,
            "updated_at": "now()"
        }
        
        supabase.table("student_module_status").upsert(data).execute()

    @staticmethod
    def log_attempt(student_id: str, module_id: str, score: float, attempt_no: int):
        supabase = get_supabase()
        import uuid
        attempt_id = str(uuid.uuid4())
        
        data = {
            "attempt_id": attempt_id,
            "student_id": student_id,
            "module_id": module_id,
            "score": score,
            "attempt_no": attempt_no
        }
        
        supabase.table("student_attempts").insert(data).execute()
        return attempt_id
