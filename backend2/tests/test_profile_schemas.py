from backend2.schemas.profile import ProfileData, DimensionScore, Constraint, Preference

def test_profile_data_with_new_fields():
    data = ProfileData(
        name="张三",
        tags=["Python", "后端"],
        strengths=["算法基础扎实"],
        weaknesses=["无大规模系统经验"],
        dimension_scores=[DimensionScore(name="技术能力", score=75, source="user_input")],
        constraints=[Constraint(type="location", value="北京", label="北京")],
        preferences=[Preference(type="industry", value="互联网", label="互联网")],
    )
    d = data.to_dict()
    assert d["name"] == "张三"
    assert d["tags"] == ["Python", "后端"]
    assert d["dimension_scores"][0]["score"] == 75
    assert d["dimension_scores"][0]["source"] == "user_input"

def test_profile_data_backward_compat():
    """老数据（无新增字段）应能正常反序列化。"""
    data = ProfileData(name="李四")
    assert data.tags == []
    assert data.dimension_scores == []
