export interface AvailabilityData {
  months?: Record<string, number | null>;
  avg_billed?: number | null;
  avg_available?: number | null;
}

export interface ConsultantHit {
  user_id?: string;
  cv_id?: string;
  name?: string | null;
  email?: string | null;
  title?: string | null;
  office_name?: string | null;
  country_code?: string | null;
  matching_skills?: string[];
  matching_skill_ids?: string[];
  total_skills?: number;
  deactivated?: boolean;
  availability?: AvailabilityData | null;
}

export interface FindUsersBySkillData {
  scope?: string;
  match_mode?: string;
  match_all?: boolean;
  requested_skills?: string[];
  resolved_skill_ids?: string[];
  resolution_by_input?: {
    input: string;
    resolved_count: number;
    resolved_names: string[];
  }[];
  unresolved_inputs?: string[];
  total_matches?: number;
  returned?: number;
  users?: ConsultantHit[];
}

export interface SearchUsersData {
  count?: number;
  from?: number;
  size?: number;
  has_more?: boolean;
  next_from?: number | null;
  users?: ConsultantHit[];
}

export interface AvailabilityResultData extends AvailabilityData {
  name?: string | null;
  user_id?: string | null;
  cv_id?: string | null;
}

export interface SkillItem {
  skill_id: string;
  name: string;
  category_ids?: string[];
}

export interface ListSkillsData {
  total?: number;
  count?: number;
  offset?: number;
  limit?: number;
  has_more?: boolean;
  next_offset?: number | null;
  skills?: SkillItem[];
}

export interface OfficeItem {
  office_id: string;
  office_name: string;
  num_users?: number | null;
}

export interface CountryOffices {
  country_id: string;
  country_code: string;
  offices: OfficeItem[];
}

export type ListOfficesData = CountryOffices[];

export interface RegionSummary {
  region: string;
  matched_offices: {
    region: string;
    office_name: string;
    office_id: string;
    num_users?: number | null;
  }[];
  missing_offices: { region: string; office_name: string }[];
  num_offices: number;
  num_users: number;
}

export interface ListRegionsData {
  country?: string;
  regions?: RegionSummary[];
}

export interface CvProjectItem {
  customer?: string;
  industry?: string;
  from?: string;
  to?: string;
  description?: string;
  roles?: string[];
  skills?: string[];
}

export interface CvTechItem {
  category?: string;
  skills?: string[];
}

export interface CvData {
  user_id?: string | null;
  cv_id?: string | null;
  name?: string | null;
  title?: string | null;
  email?: string | null;
  telephone?: string | null;
  place_of_residence?: string | null;
  language_code?: string | null;
  updated_at?: string | null;
  key_qualifications?: { label?: string; summary?: string }[];
  technologies?: CvTechItem[];
  recent_projects?: CvProjectItem[];
  certifications?: {
    name?: string;
    organiser?: string;
    year?: string | null;
    month?: string | null;
  }[];
  languages?: { name?: string; level?: string }[];
  educations?: {
    degree?: string;
    school?: string;
    from?: string | null;
    to?: string | null;
  }[];
  work_experiences?: {
    employer?: string;
    description?: string;
    from_year?: string | null;
  }[];
  courses?: { name?: string; year?: string | null }[];
}

export interface FindUserData {
  user_id?: string | null;
  default_cv_id?: string | null;
  name?: string | null;
  title?: string | null;
  email?: string | null;
  external_unique_id?: string | null;
  role?: string | null;
  office_name?: string | null;
  country_code?: string | null;
  deactivated?: boolean;
  updated_at?: string | null;
}
