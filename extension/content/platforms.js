// Platform-specific DOM selectors for JD extraction.
// Each entry: { name, titleSelector, bodySelectors[] }
// bodySelectors are tried in order; first one with ≥50 chars of text wins.

const PLATFORMS = {
  "zhipin.com": {
    name: "BOSS直聘",
    titleSelector: ".job-detail-header .name, .name.job-name",
    bodySelectors: [
      ".job-detail-section .text",
      ".job-sec-text",
      "[class*='detail-content']",
      ".job-detail-box",
    ],
  },
  "lagou.com": {
    name: "拉勾",
    titleSelector: ".position-name, .job-name",
    bodySelectors: [
      ".job-detail",
      ".job_describe",
      "[class*='describe']",
    ],
  },
  "liepin.com": {
    name: "猎聘",
    titleSelector: ".title-info h1, .job-name",
    bodySelectors: [
      ".job-introduction",
      ".job-description",
      "[class*='description']",
    ],
  },
  "zhaopin.com": {
    name: "智联招聘",
    titleSelector: ".name__title, h1",
    bodySelectors: [
      ".describtion",
      ".job-detail",
      "[class*='detail']",
    ],
  },
  "51job.com": {
    name: "前程无忧",
    titleSelector: ".cn h1, .job-name",
    bodySelectors: [
      ".bmsg",
      ".job-detail",
      "[class*='detail']",
    ],
  },
}
