export { API_BASE, rawFetch, apiFetch, apiUpload } from './client'
export {
  listApplications,
  createApplication,
  updateApplicationStatus,
  setInterviewTime,
  updateNotes,
  deleteApplication,
  updateReflection,
  submitDebrief,
} from './applications'
export {
  getCoachResult,
  listCoachResults,
  deleteCoachResult,
  postChat,
} from './coach'
export {
  fetchGraphMap,
  fetchEscapeRoutes,
  searchGraphNodes,
  fetchNodeIntro,
  setCareerGoal,
  addCareerGoal,
  patchCareerGoalGaps,
} from './graph'
export type { SetCareerGoalPayload, AddCareerGoalPayload } from './graph'
export {
  listEntries,
  createEntry,
  updateEntry,
  deleteEntry,
  aiSuggest,
} from './growthEntries'
export type { InterviewQA, InterviewData, ProjectData, AiSuggestion, GrowthEntry } from './growthEntries'
export {
  getGrowthDashboard,
  getInsights,
  getGoalJourney,
  getGoalHistory,
  getSkillsHarvest,
  getActivityPulse,
  listProjects,
  createProject,
  updateProject,
  deleteProject,
  listInterviews,
  createInterview,
  updateInterview,
  deleteInterview,
  analyzeInterview,
  listProjectLogs,
  createProjectLog,
  deleteProjectLog,
  getProjectGraph,
  saveProjectGraph,
} from './growthLog'
export type {
  ProjectRecord,
  InterviewRecord,
  GrowthDashboardData,
  InsightItem,
  StageEvent,
  GoalJourney,
  GoalHistoryItem,
  SkillTouched,
  SkillsHarvestData,
  WeeklyActivity,
  ActivityPulseData,
  ProjectLogEntry,
  GraphData,
} from './growthLog'
export {
  startInterview,
  submitInterview,
  generateFollowUp,
  fetchInterviewHistory,
  fetchInterviewSession,
} from './interview'
export type {
  Question,
  FollowUpTurn,
  Answer,
  PerQuestionEval,
  Evaluation,
  InterviewHistoryItem,
  InterviewSession,
} from './interview'
export { diagnoseJd, getJDDiagnosis, listJDDiagnoses } from './jd'
export type { JDDiagnosisDetail } from './jd'
export {
  fetchProfile,
  updateProfile,
  setProfileName,
  refineProject,
  resetProfile,
  generateSjt,
  submitSjt,
  refineProfileProject,
} from './profile'
export type { UpdateProfilePayload, SjtQuestion, SjtAnswer, SjtGenerateResult, SjtDimensionResult, SjtSubmitResult } from './profile'
export {
  parsePreview,
  saveProfile,
  fetchMyProfileV2,
} from './profiles-v2'
export type {
  V2ProfileData,
  V2Education,
  V2Skill,
  V2Internship,
  V2Project,
  V2ParsePreviewResponse,
  V2SaveProfileResponse,
} from '@/types/profile-v2'
export { fetchRecommendations, fetchMatchDetail } from './recommendations'
export type { Recommendation, RecommendationsResponse, MatchDetail } from './recommendations'
export {
  fetchReportList,
  fetchReportDetail,
  generateReport,
  deleteReport,
  editReport,
  polishReport,
  fetchPlan,
  updatePlanCheck,
  generateReportV2,
} from './report'
export type {
  ReportListItem,
  ReportNarrative,
  ReportChapter,
  ReportDetail,
  PlanActionItem,
  PlanStage,
  PlanData,
  ReportV2Data,
} from './report'
export { fetchCareerStage } from './user'
export type { CareerStage } from './user'
