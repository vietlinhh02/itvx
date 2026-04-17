export type BilingualText = {
  vi: string
  en: string
}

export type HumanReadableText = string | BilingualText

export type BackgroundJobResponse = {
  job_id: string
  job_type: string
  status: string
  resource_type: string
  resource_id: string
  error_message: string | null
  started_at: string | null
  completed_at: string | null
}

export type JDAnalysisEnqueueResponse = {
  job_id: string
  jd_id: string
  file_name: string
  status: "processing"
}

export type JDAnalysisResponse = {
  jd_id: string
  file_name: string
  status: "completed"
  created_at: string
  analysis: {
    job_overview: {
      job_title: BilingualText
      department: BilingualText
      seniority_level: string
      location: BilingualText
      work_mode: string
      role_summary: BilingualText
      company_benefits: BilingualText[]
    }
    requirements: {
      required_skills: string[]
      preferred_skills: string[]
      tools_and_technologies: string[]
      experience_requirements: {
        minimum_years: number | null
        relevant_roles: HumanReadableText[]
        preferred_domains: HumanReadableText[]
      }
      education_and_certifications: HumanReadableText[]
      language_requirements: HumanReadableText[]
      key_responsibilities: BilingualText[]
      screening_knockout_criteria: HumanReadableText[]
    }
    rubric_seed: {
      evaluation_dimensions: Array<{
        name: BilingualText
        description: BilingualText
        priority: string
        weight: number
        evidence_signals: BilingualText[]
      }>
      screening_rules: {
        minimum_requirements: HumanReadableText[]
        scoring_principle: HumanReadableText
      }
      ambiguities_for_human_review: BilingualText[]
    }
  }
}
