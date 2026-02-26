import os
import json
import logging
from typing import List, Dict, Any, Optional
from services.curriculum_enricher import enricher

# Try to import Supabase client from Student module
try:
    from Student.db.supabase_client import get_supabase
except ImportError:
    # Fallback if running from a different context
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
    from Student.db.supabase_client import get_supabase

class AnalyticsService:
    def __init__(self):
        self.supabase = get_supabase()

    def _fetch_all_student_scores(self, subject_id: str = None) -> List[Dict]:
        """
        Helper:  Fetch and aggregate all student scores from module status.
        Returns list of { 'student_id': str, 'avg_score': float, 'completed_count': int }
        """
        try:
            # 1. Determine Scope (Filter by Subject)
            valid_module_ids = None
            if subject_id:
                try:
                    m_res = self.supabase.table("modules").select("module_id").eq("subject_id", subject_id).execute()
                    if m_res.data:
                        valid_module_ids = {m['module_id'] for m in m_res.data}
                except Exception as e:
                    print(f"⚠️ Failed to filter modules by subject: {e}")

            # 2. Fetch Scores
            query = self.supabase.table("student_module_status").select("student_id, best_score, status, module_id")
            res = query.execute()
            data = res.data or []
            
            students = {}
            for row in data:
                # FILTER: strict subject check
                if valid_module_ids is not None:
                    if row['module_id'] not in valid_module_ids:
                        continue

                sid = row['student_id']
                if sid not in students:
                    students[sid] = {'total_score': 0, 'attempts': 0, 'completed': 0, 'modules': []}
                
                s = students[sid]
                if row['status'] in ['completed', 'in_progress']:
                    score = row['best_score']
                    if 0 < score <= 1.0: score *= 100
                    s['total_score'] += score
                    s['attempts'] += 1
                
                if row['status'] == 'completed':
                    s['completed'] += 1
                    
                s['modules'].append(row['module_id'])

            results = []
            for sid, stats in students.items():
                avg = round(stats['total_score'] / stats['attempts'], 1) if stats['attempts'] > 0 else 0
                results.append({
                    "student_id": sid,
                    "average_score": avg,
                    "completed_count": stats['completed']
                })
            return results
        except Exception as e:
            print(f"⚠️ Fetch Scores Error: {e}")
            return []

    def get_class_overview(self, subject_id: str = None) -> Dict[str, Any]:
        """
        V2: Aggregate metrics from raw module data (Robust).
        """
        try:
            # 1. Fetch Student Aggregates
            students = self._fetch_all_student_scores(subject_id)
            total_students = len(students)
            
            if total_students == 0:
                 return {"class_average": 0, "total_students": 0, "module_progress": [], "common_weak_areas": []}

            # 2. Class Average
            class_avg = round(sum(s['average_score'] for s in students) / total_students, 1)

            # 3. Module Progress & Weakness Aggregation
            mod_res = self.supabase.table("student_module_status")\
                .select("status, module_id, best_score, modules(module_name)")\
                .execute()
            
            mod_stats = {}
            module_perf = {} 
            
            # Fetch valid IDs again for filtering
            valid_ids = None
            if subject_id:
                 try:
                     m_res = self.supabase.table("modules").select("module_id").eq("subject_id", subject_id).execute()
                     if m_res.data:
                         valid_ids = {m['module_id'] for m in m_res.data}
                 except: pass

            for row in mod_res.data:
                mid = row['module_id']
                if valid_ids and mid not in valid_ids:
                    continue
                    
                status = row.get('status')
                score = row.get('best_score', 0)
                
                m_obj = row.get('modules')
                m_name = m_obj.get('module_name') if m_obj and isinstance(m_obj, dict) else mid

                # A. Progress Stats
                if mid not in mod_stats: mod_stats[mid] = {"completed": 0, "in_progress": 0}
                if status == 'completed': mod_stats[mid]['completed'] += 1
                elif status == 'in_progress': mod_stats[mid]['in_progress'] += 1
                
                # B. Performance Stats
                if status in ['completed', 'in_progress']:
                    if 0 < score <= 1.0: score *= 100
                    if mid not in module_perf: 
                        module_perf[mid] = {'sum': 0, 'count': 0, 'name': m_name}
                    module_perf[mid]['sum'] += score
                    module_perf[mid]['count'] += 1
            
            # Format Progress Chart
            chart_data = [{"module": m, "completed": s["completed"], "in_progress": s["in_progress"]} for m, s in mod_stats.items()]

            # Format Weak Areas (Avg < 60%)
            weak_areas = []
            for mid, metrics in module_perf.items():
                avg = round(metrics['sum'] / metrics['count'], 1) if metrics['count'] > 0 else 0
                if avg < 65: # Threshold for weakness
                    weak_areas.append({
                        "module_name": metrics['name'],
                        "cohort_average": avg,
                        "students_attempted": metrics['count']
                    })
            
            weak_areas.sort(key=lambda x: x['cohort_average'])

            return {
                "total_students": total_students,
                "class_average": class_avg,
                "module_progress": chart_data,
                "common_weak_areas": weak_areas
            }
        except Exception as e:
            print(f"❌ Analytics V2 Error: {e}")
            return {}

    def get_weak_area_analytics(self, subject_id: str) -> Dict[str, Any]:
        """
        Generate detailed weak area analytics for Teacher Agent using 'student_analytics' table.
        """
        try:
            # 1. Fetch Weak Areas from 'student_analytics'
            # Table Schema: student_id, weak_areas (jsonb: {uuid: {name: str, count: int}})
            res = self.supabase.table("student_analytics").select("weak_areas").execute()
            rows = res.data or []
            
            # 2. Aggregation Logic
            topic_stats = {}
            
            # Helper to normalize subject_id for matching
            # subject_id e.g. "btech_data_structures_y2" -> "Data Structures"?
            # Safe way: iterate known subjects in enricher and see which one matches subject_id string.
            # Or pass specific subject name if available.
            # Let's clean the subject_id:
            # "btech_data_structures_y2" -> search for "Data Structures"
            
            target_subject_name = None
            if "data_structures" in subject_id.lower(): target_subject_name = "Data Structures"
            elif "discrete_mat" in subject_id.lower(): target_subject_name = "Discrete Mathematics"
            
            # If we assume standard naming, we can do this.
            
            for row in rows:
                wa_map = row.get("weak_areas") or {}
                
                # Iterate each tracked weak area
                for t_uuid, details in wa_map.items():
                    try:
                        t_name = details.get("name")
                        count = details.get("count", 0)
                        
                        if not t_name or count == 0: continue

                        # 3. Check Subject Ownership
                        subj = enricher.get_subject_for_topic(t_name)
                        
                        # Match Logic
                        is_match = False
                        if target_subject_name and subj == target_subject_name:
                            is_match = True
                        elif not target_subject_name and subj:
                             # Fallback fuzzy match
                             slug = subj.lower().replace(" ", "_")
                             if slug in subject_id.lower():
                                 is_match = True
                        
                        if not is_match: continue
                        
                        # 4. Determine Severity (Based on Count as per User Instruction)
                        # Count 1 = Mild
                        # Count 2-3 = Moderate
                        # Count >= 4 = Critical
                        severity = "mild"
                        if count >= 4: severity = "critical"
                        elif count >= 2: severity = "moderate"
                        
                        # 5. Aggregate
                        # Use enriched name or raw name as key? T_Name is better for display.
                        # We need a stable ID. Let's use t_name as ID for aggregation to merge duplicate UUIDs if any.
                        
                        unique_id = t_name 
                        
                        if unique_id not in topic_stats:
                            # Re-enrich just in case
                            t_details = enricher.get_topic_details(t_uuid) 
                            
                            # FALLBACK: Try Name-based lookup if UUID failed (Crucial for Assessment compatibility)
                            if not t_details:
                                t_details = enricher.get_details_by_topic_name(t_name)

                            u_title = t_details['unit'] if t_details else "General"
                            
                            topic_stats[unique_id] = {
                                "topic_name": t_name,
                                "unit_title": u_title, 
                                "mild": 0, "moderate": 0, "critical": 0,
                                "total_affected": 0
                            }
                        
                        topic_stats[unique_id][severity] += 1
                        topic_stats[unique_id]["total_affected"] += 1
                        
                    except Exception as e:
                         # Skip malformed entries
                         continue

            # 6. Formatting & Priority
            formatted_results = []
            
            for mid, stats in topic_stats.items():
                p_score = (stats['critical'] * 3) + (stats['moderate'] * 2) + (stats['mild'] * 1)
                
                formatted_results.append({
                    "topic_id": mid,
                    "topic_name": stats['topic_name'],
                    "unit_title": stats['unit_title'],
                    "affected_students": stats['total_affected'],
                    "breakdown": {
                        "critical": stats['critical'],
                        "moderate": stats['moderate'],
                        "mild": stats['mild']
                    },
                    "priority_score": p_score
                })
            
            formatted_results.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # --- STAGE 2: CO Aggregation (New V3) ---
            co_risk_map = {} # {co_code: {desc, severity_score, affected_students_max}}
            
            # We need to map Topic/Unit -> Module ID -> CO ID
            # This is tricky because `student_analytics` table stores Topic Name, not Module ID directly.
            # But we can approximate using `enricher` or `modules` table if we have Module ID.
            # `enricher` has weak reverse mapping.
            
            # STRATEGY: 
            # 1. Get all Module IDs for the current Subject
            # 2. Map Topic -> Module (Fuzzy or Exact)
            # 3. Fetch COs for those Modules
            
            # Fetch Subject Modules + Topics + Mappings (Complex Join? Keep it simple)
            # Or just fetch ALL module_co_mappings for the subject?
            # Yes: join module_co_mapping with modules filtered by subject.
            
            try:
                # 1. Get all modules for subject
                m_res = self.supabase.table("modules").select("module_id, module_name").eq("subject_id", subject_id).execute()
                mod_lut = {m['module_name'].lower(): m['module_id'] for m in m_res.data}
                
                # 2. Get all CO mappings for these modules
                all_mod_ids = list(mod_lut.values())
                if all_mod_ids:
                    co_map_res = self.supabase.table("module_co_mapping").select("module_id, co_id").in_("module_id", all_mod_ids).execute()
                    
                    # 3. Get CO Details
                    co_ids = list({x['co_id'] for x in co_map_res.data})
                    if co_ids:
                        co_details_res = self.supabase.table("course_outcomes").select("co_id, co_code, description").in_("co_id", co_ids).execute()
                        co_info_lut = {c['co_id']: c for c in co_details_res.data}
                        
                        # Build Mod -> [CO_Objects] map
                        mod_to_cos = {}
                        for link in co_map_res.data:
                             mid = link['module_id']
                             cid = link['co_id']
                             if mid not in mod_to_cos: mod_to_cos[mid] = []
                             if cid in co_info_lut:
                                 mod_to_cos[mid].append(co_info_lut[cid])

                        # 4. Integrate with Weak Topics
                        for topic_res in formatted_results:
                            # Try to find corresponding module
                            # Topic Name or Unit Title can clue us in.
                            # Best bet: match Unit Title or check if Topic Name is a Module Name?
                            # Our `enricher` maps Topic -> Unit. 
                            # Let's assume Unit Title maps roughly to Module Name or use Topic->Module mapping if available.
                            
                            # For B.Tech, "Unit 1" is likely the Module Name.
                            u_title = topic_res.get('unit_title', '').lower()
                            t_name = topic_res.get('topic_name', '').lower()
                            
                            # Try matching Unit first
                            matched_mod_id = None
                            for m_name_key, m_id in mod_lut.items():
                                if u_title in m_name_key or m_name_key in u_title:
                                    matched_mod_id = m_id
                                    break
                            
                            if matched_mod_id and matched_mod_id in mod_to_cos:
                                affected_cos = mod_to_cos[matched_mod_id]
                                p_score = topic_res['priority_score']
                                students = topic_res['affected_students']
                                
                                for co in affected_cos:
                                    code = co['co_code']
                                    if code not in co_risk_map:
                                        co_risk_map[code] = {
                                            "total_severity_score": 0,
                                            "affected_topics_count": 0,
                                            "description": co['description'],
                                            "max_students": 0
                                        }
                                    
                                    co_risk_map[code]["total_severity_score"] += p_score
                                    co_risk_map[code]["affected_topics_count"] += 1
                                    co_risk_map[code]["max_students"] = max(co_risk_map[code]["max_students"], students)

            except Exception as e:
                print(f"⚠️ CO Mapping Failed: {e}")

            # Format CO Risks
            at_risk_cos = []
            for code, stats in co_risk_map.items():
                at_risk_cos.append({
                    "co_code": code,
                    "risk_score": stats['total_severity_score'],
                    "description": stats['description'],
                    "affected_topics": stats['affected_topics_count'],
                    "students_impacted": stats['max_students']
                })
            
            at_risk_cos.sort(key=lambda x: x['risk_score'], reverse=True)

            return {
                "subject": subject_id,
                "topics": formatted_results,
                "at_risk_cos": at_risk_cos # NEW FIELD
            }
            
        except Exception as e:
            print(f"❌ Weak Area Error: {e}")
            return {}

    def _fetch_module_performance_raw(self, subject_id: str):
        """Fetch all module statuses for valid subject modules"""
        # 1. Get Modules
        try:
             m_res = self.supabase.table("modules").select("module_id").eq("subject_id", subject_id).execute()
             valid_ids = {m['module_id'] for m in m_res.data} if m_res.data else set()
        except: return []

        if not valid_ids: return []

        # 2. Get Statuses
        res = self.supabase.table("student_module_status").select("student_id, module_id, best_score").execute()
        return [r for r in res.data if r['module_id'] in valid_ids]

    def get_performance_distribution(self, subject_id: str = None) -> Dict[str, int]:
        """Histogram Buckets: Needs Support, Average, High"""
        students = self._fetch_all_student_scores(subject_id)
        dist = {"Needs Support (<50%)": 0, "Average (50-75%)": 0, "High Performers (>75%)": 0}
        
        for s in students:
            sc = s['average_score']
            if sc < 50: dist["Needs Support (<50%)"] += 1
            elif sc < 75: dist["Average (50-75%)"] += 1
            else: dist["High Performers (>75%)"] += 1
        return dist

    def get_student_leaderboard(self, subject_id: str = None) -> Dict[str, List[Dict]]:
        """Top 5 and Bottom 5"""
        students = self._fetch_all_student_scores(subject_id)
        # Fetch names
        try:
            name_map = {s['student_id']: s['name'] for s in self.supabase.table("students").select("student_id, name").execute().data}
        except: name_map = {}

        # Sort
        sorted_s = sorted(students, key=lambda x: x['average_score'], reverse=True)
        
        def fmt(s_list):
            return [{"name": name_map.get(s['student_id'], s['student_id']), "score": s['average_score']} for s in s_list]

        return {
            "top_5": fmt(sorted_s[:5]),
            "bottom_5": fmt(sorted_s[-5:])
        }
    
    def get_cohort_distribution(self, subject_id: str = None) -> Dict[str, int]:
        """Count of students by # of completed modules (Velocity proxy)"""
        students = self._fetch_all_student_scores(subject_id)
        # Bin by completed count (0, 1, 2, 3, 4, 5+)
        bins = {}
        for s in students:
            c = s['completed_count']
            label = f"{c} Modules Done"
            bins[label] = bins.get(label, 0) + 1
        return bins

    def get_student_list(self) -> List[Dict]:
        """Fetch list of all students for dropdown"""
        try:
            res = self.supabase.table("students").select("student_id, name, grade").execute()
            return res.data or []
        except Exception as e:
            return []

    def get_student_details(self, student_id: str) -> Dict[str, Any]:
        """Get detailed stats (Hybrid V2)"""
        try:
            # 1. Module Status (Source of Truth)
            mod_res = self.supabase.table("student_module_status")\
                .select("status, best_score, modules(module_name)")\
                .eq("student_id", student_id)\
                .execute()
            
            modules_list = []
            total_score = 0
            attempts = 0
            completed = 0
            
            for m in mod_res.data:
                m_name = m.get("modules", {}).get("module_name", "Unknown") if m.get("modules") else m.get("module_id")
                score = m.get("best_score", 0)
                
                # Normalize if decimal
                if 0 < score <= 1.0: 
                    score *= 100
                score = round(score, 1)

                modules_list.append({
                    "module": m_name,
                    "status": m.get("status"),
                    "score": score
                })
                if m['status'] in ['completed', 'in_progress']:
                    total_score += score
                    attempts += 1
                if m['status'] == 'completed':
                    completed += 1
            
            avg = round(total_score/attempts, 1) if attempts else 0
            
            return {
                "student_id": student_id,
                "average_score": avg,
                "overall_progress": completed * 20, # Approx 5 modules = 100%
                "weak_areas": {}, # Fallback empty if table missing
                "modules": modules_list
            }
        except Exception as e:
            print(f"❌ Student Detail Error: {e}")
            return {}

    def get_exam_analytics(self, subject_id: str) -> Dict[str, Any]:
        """
        Get analytics specifically for the Final Exam module.
        Module ID convention: {subject_id}_final_exam
        """
        try:
            final_mod_id = f"{subject_id}_final_exam"
            
            res = self.supabase.table("student_module_status")\
                .select("student_id, status, best_score")\
                .eq("module_id", final_mod_id)\
                .execute()
                
            data = res.data or []
            
            try:
                all_students = self.supabase.table("students").select("student_id, name").execute().data or []
                total_students = len(all_students)
            except:
                total_students = len(data)
                all_students = []

            submitted_count = 0
            passed_count = 0
            total_score_sum = 0
            score_counts = 0
            
            student_details = []
            
            data_map = {row['student_id']: row for row in data}
            
            for s in all_students:
                sid = s['student_id']
                s_name = s['name']
                
                row = data_map.get(sid, {})
                status = row.get("status", "not_started") 
                score = row.get("best_score", 0.0)
                
                if 0 < score <= 1.0: score *= 100
                score = round(score, 1)
                
                if status in ['completed']:
                    submitted_count += 1
                    total_score_sum += score
                    score_counts += 1
                    if score >= 60: 
                        passed_count += 1
                
                student_details.append({
                    "student_id": sid,
                    "name": s_name,
                    "status": status,
                    "score": score
                })

            avg_score = round(total_score_sum / score_counts, 1) if score_counts > 0 else 0
            pass_rate = round((passed_count / score_counts) * 100, 1) if score_counts > 0 else 0
            
            student_details.sort(key=lambda x: x['score'], reverse=True)

            return {
                "total_assigned": total_students,
                "submitted_count": submitted_count,
                "average_score": avg_score,
                "pass_rate": pass_rate,
                "student_details": student_details
            }

        except Exception as e:
            print(f"❌ Exam Analytics Error: {e}")
            return {}

analytics_service = AnalyticsService()
