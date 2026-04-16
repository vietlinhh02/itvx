export type BilingualText = {
  vi: string
  en: string
}

export type RequirementStatus = "met" | "not_met" | "unclear"
export type ScreeningRecommendation = "advance" | "review" | "reject"
export type RiskSeverity = "low" | "medium" | "high"

export type CandidateSummary = {
  full_name: string | null
  current_title: string | null
  location: string | null
  total_years_experience: number | null
  seniority_signal: "intern" | "junior" | "mid" | "senior" | "lead" | "manager" | "unknown"
  professional_summary: BilingualText | null
}

export type WorkExperienceItem = {
  company: string
  role: string
  start_date_text: string | null
  end_date_text: string | null
  duration_text: string | null
  responsibilities: string[]
  achievements: string[]
  technologies: string[]
  evidence_excerpts: string[]
  ambiguity_notes: string[]
}

export type ProjectItem = {
  name: string | null
  role: string | null
  summary: string
  technologies: string[]
  domain_context: string | null
  evidence_excerpts: string[]
}

export type SkillEvidenceItem = {
  skill_name: string
  proficiency_signal: string | null
  evidence_excerpts: string[]
  source_section: "experience" | "project" | "summary" | "skills" | "other"
}

export type EducationItem = {
  institution: string
  degree: string | null
  field_of_study: string | null
  graduation_text: string | null
  evidence_excerpts: string[]
}

export type CertificationItem = {
  name: string
  issuer: string | null
  date_text: string | null
  evidence_excerpts: string[]
}

export type LanguageItem = {
  language_name: string
  proficiency_signal: string | null
  evidence_excerpts: string[]
}

export type ProfileUncertainty = {
  title: BilingualText
  reason: BilingualText
  impact: BilingualText
}

export type CandidateProfile = {
  candidate_summary: CandidateSummary
  work_experience: WorkExperienceItem[]
  projects: ProjectItem[]
  skills_inventory: SkillEvidenceItem[]
  education: EducationItem[]
  certifications: CertificationItem[]
  languages: LanguageItem[]
  profile_uncertainties: ProfileUncertainty[]
}

export type RequirementAssessment = {
  criterion: BilingualText
  status: RequirementStatus
  reason: BilingualText
  evidence: BilingualText[]
}

export type DimensionScore = {
  dimension_name: BilingualText
  priority: "must_have" | "important" | "nice_to_have"
  weight: number
  score: number
  reason: BilingualText
  evidence: BilingualText[]
  confidence_note: BilingualText | null
}

export type ScreeningInsight = {
  title: BilingualText
  reason: BilingualText
  evidence: BilingualText[]
}

export type ScreeningUncertainty = {
  title: BilingualText
  reason: BilingualText
  follow_up_suggestion: BilingualText
}

export type FollowUpQuestion = {
  question: BilingualText
  purpose: BilingualText
  linked_dimension: BilingualText | null
}

export type RiskFlag = {
  title: BilingualText
  reason: BilingualText
  severity: RiskSeverity
}

export type AuditMetadata = {
  extraction_model: string
  screening_model: string
  profile_schema_version: string
  screening_schema_version: string
  generated_at: string
  reconciliation_notes: string[]
  consistency_flags: string[]
}

export type CVScreeningHistoryItem = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  created_at: string
  recommendation: ScreeningRecommendation
  match_score: number
}

export type CVScreeningHistoryResponse = {
  items: CVScreeningHistoryItem[]
}

export type CVScreeningResponse = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  status: "completed"
  created_at: string
  candidate_profile: CandidateProfile
  result: {
    match_score: number
    recommendation: ScreeningRecommendation
    decision_reason: BilingualText
    screening_summary: BilingualText
    knockout_assessments: RequirementAssessment[]
    minimum_requirement_checks: RequirementAssessment[]
    dimension_scores: DimensionScore[]
    strengths: ScreeningInsight[]
    gaps: ScreeningInsight[]
    uncertainties: ScreeningUncertainty[]
    follow_up_questions: FollowUpQuestion[]
    risk_flags: RiskFlag[]
  }
  audit: AuditMetadata
}
