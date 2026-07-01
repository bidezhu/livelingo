import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

PUBLIC_HEALTH_HOT_WORDS = {
    "公共卫生": "public health",
    "全球卫生": "global health",
    "卫生政策": "health policy",
    "健康中国": "Healthy China",
    "健康促进": "health promotion",
    "健康教育": "health education",
    "健康素养": "health literacy",
    "健康公平": "health equity",
    "健康不平等": "health inequality",
    "社会决定因素": "social determinants of health",
    "卫生体系": "health system",
    "卫生服务": "health services",
    "基本公共卫生服务": "basic public health services",
    "初级卫生保健": "primary health care",
    "基层医疗卫生机构": "primary health care institutions",
    "疾病预防控制": "disease prevention and control",
    "疾控中心": "Center for Disease Control and Prevention",
    "监测预警": "surveillance and early warning",
    "流行病学": "epidemiology",
    "描述性流行病学": "descriptive epidemiology",
    "分析性流行病学": "analytical epidemiology",
    "队列研究": "cohort study",
    "病例对照研究": "case-control study",
    "横断面研究": "cross-sectional study",
    "随机对照试验": "randomized controlled trial",
    "系统综述": "systematic review",
    "荟萃分析": "meta-analysis",
    "发病率": "incidence",
    "患病率": "prevalence",
    "死亡率": "mortality rate",
    "病死率": "case fatality rate",
    "归因风险": "attributable risk",
    "相对风险": "relative risk",
    "优势比": "odds ratio",
    "置信区间": "confidence interval",
    "统计显著性": "statistical significance",
    "敏感性分析": "sensitivity analysis",
    "非传染性疾病": "non-communicable diseases",
    "慢性病": "chronic diseases",
    "心血管疾病": "cardiovascular disease",
    "糖尿病": "diabetes",
    "肥胖": "obesity",
    "儿童肥胖": "childhood obesity",
    "儿童超重": "childhood overweight",
    "营养不良": "malnutrition",
    "膳食风险": "dietary risks",
    "含糖饮料": "sugar-sweetened beverages",
    "含糖饮料税": "sugar-sweetened beverage tax",
    "糖税": "sugar tax",
    "食品环境": "food environment",
    "食品标签": "food labeling",
    "行业重新配方": "industry reformulation",
    "传染病": "infectious diseases",
    "疫苗接种": "vaccination",
    "免疫规划": "immunization program",
    "筛查": "screening",
    "早诊早治": "early detection and treatment",
    "风险评估": "risk assessment",
    "风险沟通": "risk communication",
    "成本效益分析": "cost-effectiveness analysis",
    "质量调整生命年": "quality-adjusted life year",
    "伤残调整生命年": "disability-adjusted life year",
    "循证决策": "evidence-informed decision-making",
    "循证政策": "evidence-informed policy",
    "政策对话": "policy dialogue",
    "政策简报": "policy brief",
    "利益相关方": "stakeholders",
    "利益相关方映射": "stakeholder mapping",
    "联合国儿童基金会": "UNICEF",
    "世界卫生组织": "WHO",
    "东盟": "ASEAN",
}

DEFAULTS = {
    "api_key": "",
    "engine_type": "livetranslate",  # "legacy" or "livetranslate"
    "asr_model": "fun-asr-realtime",
    "translate_model": "qwen-plus",
    "livetranslate_model": "qwen3.5-livetranslate-flash-realtime",
    "language_mode": "auto",
    "source_language": "zh",
    "target_language": "en",
    "hot_words": dict(PUBLIC_HEALTH_HOT_WORDS),
    "sample_rate": 16000,
    "segment_sentences": 4,
    "min_segment_seconds": 4.0,
    "max_segment_seconds": 28.0,
    "display_segments": 2,
    "subtitle_max_chars": 520,
    "clean_fillers": True,
    "subtitle_vertical_align": 0.5,
    "fullscreen_font_scale": 1.25,
    "show_language_labels": False,
    "font_size_cn": 30,
    "font_size_en": 24,
    "max_subtitle_lines": 4,
    "window_height": 220,
    "bg_color": "#1a1a1a",
    "text_color_cn": "#FFFFFF",
    "text_color_en": "#BBBBBB",
    "text_color_partial": "#888888",
    "device_id": None,
    "device_name": None,
    "silence_timeout": 1.7,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    cfg["hot_words"] = dict(PUBLIC_HEALTH_HOT_WORDS)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            saved_hot_words = saved.get("hot_words", {})
            cfg.update(saved)
            hot_words = dict(PUBLIC_HEALTH_HOT_WORDS)
            if isinstance(saved_hot_words, dict):
                hot_words.update(saved_hot_words)
            cfg["hot_words"] = hot_words
        except Exception:
            pass
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
