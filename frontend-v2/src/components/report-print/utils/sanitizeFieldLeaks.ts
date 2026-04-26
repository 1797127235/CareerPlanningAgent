const FIELD_NAME_LEAK_PATTERNS: Array<[RegExp, string]> = [
  [/`profile\.projects?\[\d+\]`/g, "你简历上的项目"],
  [/`profile_core\.projects?`/g, "你简历上的项目"],
  [/`profile\.work_experience(?:\[\d+\])?`/g, "你的工作经历"],
  [/`profile_core\.work_experience`/g, "你的工作经历"],
  [/`profile\.education`/g, "你的学历背景"],
  [/`profile_core\.education`/g, "你的学历背景"],
  [/`profile_core\.personal_statement`/g, "你的个人陈述"],
  [/`growth_entries?`/g, "你的成长档案"],
  [/`growth_entry:[A-Z0-9\-]+`/g, "某条成长档案记录"],
  [/`skill_deltas?`/g, "技能档案"],
  [/`skill_delta:still_claimed_only:[^`]+`/g, "这个还没证据的声明技能"],
  [/`milestones?`/g, "你的里程碑"],
  [/`milestone:[A-Z0-9\-]+`/g, "某个里程碑"],
  [/`claimed_only`/g, "仅凭简历声明"],
  [/`still_claimed_only`/g, "仍停留在简历声明"],
  [/`completed_practiced`/g, "已完成项目里出现过"],
  [/`evidence_ref`/g, "证据出处"],
  [/\bprofile\.projects?\[\d+\]/g, "你简历上的项目"],
  [/\bprofile_core\.projects?\b/g, "你简历上的项目"],
  [/\bprofile\.work_experience(?:\[\d+\])?/g, "你的工作经历"],
  [/\bprofile_core\.work_experience\b/g, "你的工作经历"],
  [/\bprofile\.education\b/g, "你的学历背景"],
  [/\bprofile_core\.education\b/g, "你的学历背景"],
  [/\bprofile_core\.personal_statement\b/g, "你的个人陈述"],
  [/\bgrowth_entries?\b/g, "你的成长档案"],
  [/\bskill_deltas?\b/g, "技能档案"],
  [/\bmilestones?\b/g, "你的里程碑"],
  [/\bclaimed_only\b/g, "仅凭简历声明"],
  [/\bstill_claimed_only\b/g, "仍停留在简历声明"],
];

export function sanitizeFieldLeaks(text: string): string {
  if (!text) return text;
  let out = text;
  for (const [pat, repl] of FIELD_NAME_LEAK_PATTERNS) {
    out = out.replace(pat, repl);
  }
  // 清理替换后可能产生的多余空格 / 标点
  out = out.replace(/\s+/g, " ").trim();
  out = out.replace(/\s*([，。、；：！？])/g, "$1");
  return out;
}
