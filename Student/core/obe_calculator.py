import os
import sys
from typing import Dict, List, Any
from Student.db.supabase_client import get_supabase

class OBECalculator:
    """
    Core engine for calculating Outcome-Based Education (OBE) metrics.
    Focus: Student-Level Attainment.
    """
    
    def __init__(self):
        self.supabase = get_supabase()

    def calculate_student_co_journey(self, student_id: str, subject_id: str) -> List[Dict[str, Any]]:
        """
        Calculate CO Attainment for a single student in a subject.
        Returns detailed journey including module-wise contribution.
        """
        # 1. Fetch all COs for Subject
        cos_res = self.supabase.table("course_outcomes")\
            .select("co_id, co_code, description, target_threshold")\
            .eq("subject_id", subject_id)\
            .execute()
        
        if not cos_res.data:
            return []
            
        cos = {co['co_id']: co for co in cos_res.data}
        co_ids = list(cos.keys())

        # 2. Fetch Module-CO Mappings
        map_res = self.supabase.table("module_co_mapping")\
            .select("module_id, co_id, contribution")\
            .in_("co_id", co_ids)\
            .execute()
            
        if not map_res.data:
            # No mappings -> No OBE result
            return [self._format_empty_co(co) for co in cos.values()]
            
        # Organize Mappings: CO -> List[Modules]
        co_to_modules = {cid: [] for cid in co_ids}
        module_ids = set()
        
        for m in map_res.data:
            co_to_modules[m['co_id']].append({
                "module_id": m['module_id'],
                "weight": float(m['contribution'])
            })
            module_ids.add(m['module_id'])

        # 3. Fetch Student Scores (Attempts) for these Modules
        # Get BEST score for each module
        # Note: We need max_score to normalize. Assuming Score is Percentage for now?
        # If score is raw (e.g. 8/10), we need max.
        # FIX: Let's normalize by assuming the stored 'score' in student_module_status is PERCENTAGE or 
        # let's look at `student_attempts`.
        # `student_module_status` has `best_score`. Is it 0-100 or 0-1?
        # Let's assume 0-100 based on UI code `format="%.1f%%"`.
        
        attempts_res = self.supabase.table("student_module_status")\
            .select("module_id, best_score, status")\
            .eq("student_id", student_id)\
            .in_("module_id", list(module_ids))\
            .execute()
            
        student_scores = {rec['module_id']: rec['best_score'] for rec in attempts_res.data}
        
        # 4. Calculate CO Attainment
        co_results = []
        
        for co_id, co_data in cos.items():
            mapped_modules = co_to_modules[co_id]
            
            total_weighted_score = 0.0
            total_weight = 0.0
            attempted_weight = 0.0
            
            evidence_details = []
            
            for mod in mapped_modules:
                mid = mod['module_id']
                w = mod['weight']
                
                score = student_scores.get(mid, 0.0) # Default 0 if not attempted
                
                # Check if attempted
                is_attempted = mid in student_scores
                
                # Contribution Logic
                total_weight += w
                if is_attempted:
                    total_weighted_score += (score * w)
                    attempted_weight += w
                    
                evidence_details.append({
                    "module": mid,
                    "weight": w,
                    "score": score,
                    "status": "Attempted" if is_attempted else "Pending"
                })
            
            # Final formula
            # Attainment = Weighted Score / Total Possible Weight
            # But we might want "Attainment So Far" vs "Final Attainment"
            # Let's show "Current Attainment" (normalized by attempted weight) 
            # AND "Projected" (normalized by total weight)?
            # Best practice: Show Attainment based on Total Weight (so it starts low and grows).
            # "You have achieved 20% of CO1" (even if you got 100% in first quiz).
            # This incentivizes completing all modules.
            
            if total_weight > 0:
                attainment = total_weighted_score / total_weight
            else:
                attainment = 0.0
                
            status = "In Progress"
            if attempted_weight == total_weight:
                # All assessments done
                if attainment >= co_data['target_threshold']:
                    status = "Achieved"
                else:
                    status = "Not Achieved"
            elif attempted_weight == 0:
                status = "Not Started"

            co_results.append({
                "co_code": co_data['co_code'],
                "description": co_data['description'],
                "attainment": round(attainment, 1), # 0-100 scale
                "target": co_data['target_threshold'],
                "status": status,
                "progress": f"{int(attempted_weight/total_weight*100)}%" if total_weight else "0%",
                "evidence": evidence_details
            })
            
        # Sort by CO Code
        co_results.sort(key=lambda x: x['co_code'])
        return co_results

    def calculate_student_po_profile(self, subject_id: str, co_results: List[Dict]) -> List[Dict]:
        """
        Derive PO Attainment from CO Results for a specific subject.
        """
        if not co_results:
            return []
            
        # 1. Map CO Code -> Attainment Score & ID
        # We need CO IDs to look up mappings.
        # We'll fetch the COs for this subject again to get IDs map
        cos_res = self.supabase.table("course_outcomes")\
            .select("co_id, co_code")\
            .eq("subject_id", subject_id)\
            .execute()
            
        if not cos_res.data:
            return []
            
        co_map = {c['co_code']: c['co_id'] for c in cos_res.data}
        co_score_map = {c['co_code']: res['attainment'] for c in cos_res.data for res in co_results if res['co_code'] == c['co_code']}

        # 2. Fetch CO-PO Mappings for these COs
        co_ids = list(co_map.values())
        if not co_ids:
            return []
            
        map_res = self.supabase.table("co_po_mapping")\
            .select("po_id, co_id, weight")\
            .in_("co_id", co_ids)\
            .execute()
            
        if not map_res.data:
            return []
            
        # 3. Aggregate by PO
        # PO -> {weighted_sum: float, total_weight: float}
        po_agg = {}
        
        for m in map_res.data:
            pid = m['po_id']
            cid = m['co_id']
            w = m['weight']
            
            # Find Code for this ID (Reverse lookup)
            # Efficient: build ID->Code map
            # But we just need Score.
            # ID -> Score lookup
            # Build id_score_map
            
            # Find code:
            code = next((k for k,v in co_map.items() if v == cid), None)
            score = co_score_map.get(code, 0.0)
            
            if pid not in po_agg:
                po_agg[pid] = {"w_sum": 0.0, "tot_w": 0.0, "sources": []}
            
            po_agg[pid]["w_sum"] += (score * w)
            po_agg[pid]["tot_w"] += w
            po_agg[pid]["sources"].append(code)

        # 4. Format Result
        po_results = []
        for pid, data in po_agg.items():
            final_score = data["w_sum"] / data["tot_w"] if data["tot_w"] > 0 else 0.0
            po_results.append({
                "po_id": pid,
                "attainment": round(final_score, 1),
                "contributing_cos": data["sources"]
            })
            
        # Optional: Sort by PO ID (PO1, PO10 numeric sort is tricky with strings, but alpha is ok)
        po_results.sort(key=lambda x: int(x['po_id'].replace("PO", "")) if x['po_id'][2:].isdigit() else 99)
        
        return po_results

    def calculate_class_co_attainment(self, subject_id: str) -> Dict[str, Any]:
        """
        Calculate Aggregate CO Attainment for the entire class/cohort in a subject.
        Returns: { 'CO1': { 'avg_attainment': 65.4, 'target': 60 }, ... }
        """
        # 1. Fetch all students who have attempted modules in this subject
        # optimization: fetch all student_module_status for this subject's modules
        
        # Get modules for subject first? 
        # Easier: Get all COs and their mapped modules
        cos_res = self.supabase.table("course_outcomes")\
            .select("co_id, co_code, target_threshold")\
            .eq("subject_id", subject_id)\
            .execute()
        
        if not cos_res.data:
            return {}
            
        co_map = {c['co_id']: c for c in cos_res.data}
        co_ids = list(co_map.keys())
        
        # Get Mappings
        map_res = self.supabase.table("module_co_mapping")\
            .select("module_id, co_id, contribution")\
            .in_("co_id", co_ids)\
            .execute()
            
        # Module -> List of (CO, Weight)
        mod_to_co = {} 
        relevant_modules = set()
        for m in map_res.data:
            mid = m['module_id']
            relevant_modules.add(mid)
            if mid not in mod_to_co:
                mod_to_co[mid] = []
            mod_to_co[mid].append({
                "co_id": m['co_id'],
                "weight": float(m['contribution'])
            })
            
        if not relevant_modules:
            return {}

        # 2. Fetch ALL student scores for these modules
        # This could be heavy, but for POC it's fine.
        scores_res = self.supabase.table("student_module_status")\
            .select("student_id, module_id, best_score")\
            .in_("module_id", list(relevant_modules))\
            .execute()
            
        # Organize: Student -> Module -> Score
        student_data = {}
        for row in scores_res.data:
            uid = row['student_id']
            if uid not in student_data:
                student_data[uid] = {}
            student_data[uid][row['module_id']] = row['best_score']
            
        # 3. Calculate CO Attainment per Student per CO
        # and then Average it.
        
        # CO -> List of student attainments
        co_stats = {cid: {"sum": 0.0, "count": 0, "code": co_map[cid]['co_code'], "target": co_map[cid]['target_threshold']} 
                   for cid in co_ids}
        
        for uid, scores in student_data.items():
            # For this student, calculate each CO
            for cid in co_ids:
                # Find mapped modules for this CO
                # Inverse look up: mod_to_co is Module->COs. need CO->Modules
                # Let's rebuild CO->Modules map or iterate efficient
                pass 
                
        # Re-approach: Iterate COs, then Students
        # Better: Pre-compute total weight per CO
        co_total_weights = {cid: 0.0 for cid in co_ids}
        co_modules = {cid: [] for cid in co_ids} # List of (mod_id, weight)
        
        for m in map_res.data:
            cid = m['co_id']
            w = float(m['contribution'])
            co_total_weights[cid] += w
            co_modules[cid].append( (m['module_id'], w) )
            
        # Now Compute
        for cid in co_ids:
            tot_w = co_total_weights[cid]
            if tot_w == 0: continue
            
            # For each student who has ANY data for this subject (or all students?)
            # Usually strict OBE uses "All Enrolled Students".
            # For POC, use "All Students with at least 1 attempt in relevant modules" (student_data keys)
            
            for uid, s_scores in student_data.items():
                w_score = 0.0
                # Sum mapped modules
                for mid, weight in co_modules[cid]:
                    score = s_scores.get(mid, 0.0) # 0 if not attempted
                    w_score += (score * weight)
                
                attainment = w_score / tot_w
                
                co_stats[cid]["sum"] += attainment
                co_stats[cid]["count"] += 1
                
        # 4. Average
        results = {}
        for cid, stats in co_stats.items():
            # Scale by 100 if DB stores decimals (0-1) -> Percentage (0-100)
            avg = ((stats["sum"] / stats["count"]) * 100.0) if stats["count"] > 0 else 0.0
            results[stats["code"]] = {
                "avg_attainment": round(avg, 1),
                "target": stats["target"],
                "student_count": stats["count"]
            }
            
        return results

        return results

    def calculate_class_po_attainment(self, subject_id: str, class_co_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate Aggregate PO Attainment for the class based on Class CO Attainment.
        Formula: Weighted Average of CO Averages.
        """
        if not class_co_results:
            return []

        # 1. Fetch CO IDs for these CO Codes (to link with mapping)
        # We assume class_co_results keys are CO Codes (CO1, CO2...)
        # We need to resolve them to CO IDs to use the mapping table.
        # Efficient way: Fetch COs for subject again.
        cos_res = self.supabase.table("course_outcomes")\
            .select("co_id, co_code")\
            .eq("subject_id", subject_id)\
            .execute()
            
        if not cos_res.data:
            return []
            
        co_map = {c['co_code']: c['co_id'] for c in cos_res.data} # Code -> ID
        
        # 2. Fetch Mappings
        co_ids = list(co_map.values())
        map_res = self.supabase.table("co_po_mapping")\
            .select("po_id, co_id, weight")\
            .in_("co_id", co_ids)\
            .execute()
            
        if not map_res.data:
            return []
            
        # 3. Aggregate
        po_agg = {} # PO_ID -> {w_sum: 0, tot_w: 0}
        
        for m in map_res.data:
            pid = m['po_id']
            cid = m['co_id']
            weight = m['weight']
            
            # Find CO Code for this CID
            code = next((k for k,v in co_map.items() if v == cid), None)
            
            if code and code in class_co_results:
                # Get Class Average for this CO
                co_avg = class_co_results[code]['avg_attainment']
                
                if pid not in po_agg:
                    po_agg[pid] = {"w_sum": 0.0, "tot_w": 0.0}
                    
                po_agg[pid]["w_sum"] += (co_avg * weight)
                po_agg[pid]["tot_w"] += weight
                
        # 4. Result
        results = []
        for pid, stats in po_agg.items():
            val = stats["w_sum"] / stats["tot_w"] if stats["tot_w"] > 0 else 0.0
            results.append({
                "po_id": pid,
                "attainment": round(val, 1)
            })
            
        # Sort numeric-ish
        results.sort(key=lambda x: int(x['po_id'].replace("PO", "")) if x['po_id'].startswith("PO") and x['po_id'][2:].isdigit() else 99)
        
        return results

    def _format_empty_co(self, co):
        return {
            "co_code": co['co_code'],
            "description": co['description'],
            "attainment": 0.0,
            "status": "No Assessments",
            "progress": "0%",
            "evidence": []
        }
