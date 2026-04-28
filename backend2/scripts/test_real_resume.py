"""真实简历解析验收脚本 — 单文件测试。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend2.schemas.profile import ResumeFile
from backend2.services.profile.parser.pipeline import ParserPipeline


def main(filepath: str) -> None:
    path = Path(filepath)
    if not path.exists():
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    file_bytes = path.read_bytes()
    resume_file = ResumeFile(
        filename=path.name,
        content_type="application/pdf",
        file_bytes=file_bytes,
    )

    pipeline = ParserPipeline()
    result = pipeline.parse(resume_file)

    print("=" * 60)
    print("解析结果")
    print("=" * 60)

    print("\n--- ProfileData ---")
    profile_dict = result.profile.model_dump(mode="json")
    print(json.dumps(profile_dict, ensure_ascii=False, indent=2))

    print("\n--- ResumeDocument ---")
    doc_dict = result.document.model_dump(mode="json")
    raw_preview = doc_dict["raw_text"][:500] + "..." if len(doc_dict["raw_text"]) > 500 else doc_dict["raw_text"]
    doc_dict["raw_text"] = raw_preview
    print(json.dumps(doc_dict, ensure_ascii=False, indent=2))

    print("\n--- ParseMeta ---")
    meta_dict = result.meta.model_dump(mode="json")
    print(json.dumps(meta_dict, ensure_ascii=False, indent=2))

    print("\n--- 质量评估 ---")
    p = result.profile
    checks = {
        "有姓名": bool(p.name.strip()),
        "有求职意向": bool(p.job_target_text.strip()),
        "有教育": len(p.education) > 0,
        "有技能": len(p.skills) > 0,
        "有项目": len(p.projects) > 0,
        "有实习": len(p.internships) > 0,
        "有奖项或证书": len(p.awards) > 0 or len(p.certificates) > 0,
        "raw_text 非空": len(p.raw_text) > 0,
    }
    for k, v in checks.items():
        print(f"  {k}: {'✅' if v else '❌'}")
    print(f"\n  quality_score: {result.meta.quality_score}")
    print(f"  warnings: {result.meta.warnings or '无'}")

    print("\n--- 提取方法 ---")
    print(f"  extraction_method: {result.document.extraction_method}")
    print(f"  text_format: {result.document.text_format}")
    print(f"  raw_text 长度: {len(result.document.raw_text)} 字符")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_real_resume.py <简历文件路径>")
        sys.exit(1)
    main(sys.argv[1])
