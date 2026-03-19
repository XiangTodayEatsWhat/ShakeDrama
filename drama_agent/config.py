"""
国产短剧生成Agent - 配置管理
"""
import json as _json
import os
from contextvars import ContextVar as _ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CUSTOM_MODELS_FILE = os.path.join(_BASE_DIR, "custom_models.json")
_LLM_PROFILES_FILE = os.path.join(_BASE_DIR, "llm_profiles.json")


class LLMProvider(Enum):
    """LLM提供商"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    CLAUDE = "claude"
    WLAI = "wlai"
    GEMINI = "gemini"
    GROK = "grok"
    GROK42 = "grok42"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider = LLMProvider.OPENAI

    wlai_api_key: str = os.environ.get("WLAI_API_KEY", "")
    wlai_base_url: str = os.environ.get("WLAI_BASE_URL", "https://yunwu.ai/v1")
    wlai_model: str = os.environ.get("WLAI_MODEL", "claude-opus-4-6")
    wlai_max_tokens: int = 24000
    wlai_thinking_enabled: bool = True
    wlai_thinking_budget_tokens: int = 10240
    wlai_thinking_budget_ideation: int = 10240
    wlai_thinking_budget_outline: int = 10240
    wlai_thinking_budget_scripting: int = 10240

    deepseek_api_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_base_url: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o")

    claude_api_key: str = os.environ.get("CLAUDE_API_KEY", "")
    claude_model: str = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
    grok_model: str = os.environ.get("GROK_MODEL", "grok-4.1")
    grok42_model: str = os.environ.get("GROK42_MODEL", "grok-4.2")

    custom_api_key: str = ""
    custom_base_url: str = ""
    custom_model: str = ""

    temperature: float = 0.8
    max_tokens: int = 8192
    top_p: float = 0.95

    def _thinking_budget_for_stage(self, stage_name: Optional[str]) -> int:
        """按运行阶段返回 thinking 预算。"""
        stage = stage_name if stage_name is not None else getattr(get_config(), "current_stage_name", None)
        if stage in ("00_样本选择", "01_灵感", "02_梗概", "03_总体大纲", "04_人设", "05_审核"):
            return getattr(self, "wlai_thinking_budget_ideation", 2048)
        if stage in ("06_多集大纲", "07_分集大纲"):
            return getattr(self, "wlai_thinking_budget_outline", 10240)
        return getattr(self, "wlai_thinking_budget_scripting", 6144)

    def get_active_config(self) -> dict:
        """获取当前激活的LLM配置"""
        if self.provider == LLMProvider.WLAI:
            return {
                "api_key": self.wlai_api_key,
                "base_url": self.wlai_base_url,
                "model": self.wlai_model,
                "max_tokens": getattr(self, "wlai_max_tokens", 16000),
                "thinking_enabled": getattr(self, "wlai_thinking_enabled", True),
                "thinking_budget_tokens": self._thinking_budget_for_stage(None),
            }
        if self.provider == LLMProvider.DEEPSEEK:
            return {
                "api_key": self.deepseek_api_key,
                "base_url": self.deepseek_base_url,
                "model": self.deepseek_model,
            }
        if self.provider == LLMProvider.OPENAI:
            return {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.openai_model,
            }
        if self.provider == LLMProvider.CLAUDE:
            return {
                "api_key": self.claude_api_key,
                "base_url": "https://api.anthropic.com",
                "model": self.claude_model,
            }
        if self.provider == LLMProvider.GEMINI:
            return {
                "api_key": self.wlai_api_key,
                "base_url": self.wlai_base_url,
                "model": self.gemini_model,
                "max_tokens": getattr(self, "wlai_max_tokens", 16000),
                "thinking_enabled": getattr(self, "wlai_thinking_enabled", True),
                "thinking_budget_tokens": self._thinking_budget_for_stage(None),
            }
        if self.provider == LLMProvider.GROK:
            return {
                "api_key": self.wlai_api_key,
                "base_url": self.wlai_base_url,
                "model": self.grok_model,
                "max_tokens": getattr(self, "wlai_max_tokens", 16000),
                "thinking_enabled": getattr(self, "wlai_thinking_enabled", True),
                "thinking_budget_tokens": self._thinking_budget_for_stage(None),
            }
        if self.provider == LLMProvider.GROK42:
            return {
                "api_key": self.wlai_api_key,
                "base_url": self.wlai_base_url,
                "model": self.grok42_model,
                "max_tokens": getattr(self, "wlai_max_tokens", 16000),
                "thinking_enabled": getattr(self, "wlai_thinking_enabled", True),
                "thinking_budget_tokens": self._thinking_budget_for_stage(None),
            }
        if self.provider == LLMProvider.CUSTOM:
            return {
                "api_key": self.custom_api_key,
                "base_url": self.custom_base_url or "https://api.openai.com/v1",
                "model": self.custom_model or "gpt-4o",
            }
        return {}


@dataclass
class DramaConfig:
    """短剧配置"""
    min_episodes: int = 80
    max_episodes: int = 100
    episodes_per_batch: int = 5
    episode_word_min: int = 500
    episode_word_max: int = 700
    episode_word_count_mode: str = "no_punct"
    max_scenes_per_episode: int = 3
    max_action_markers_per_episode: int = 15
    max_action_chars_per_line: int = 25
    hook_score_threshold: float = 6.0
    ai_tone_score_threshold: float = 7.0
    max_rewrite_attempts: int = 5
    scene_header_format: str = "{episode}-{scene} {location} {time} {interior}"
    action_prefix: str = "△"
    os_format: str = "（OS）"
    vo_format: str = "（VO）"


@dataclass
class SampleLibraryConfig:
    """样本剧本库配置"""
    use_for_format: bool = True
    use_for_style: bool = True
    use_for_hooks: bool = True
    use_for_creativity: bool = False
    enable_rag: bool = True
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_retrieval: int = 3
    samples_dir: str = os.environ.get(
        "DRAMA_SAMPLES_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    )


@dataclass
class Config:
    """总配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    drama: DramaConfig = field(default_factory=DramaConfig)
    sample_library: SampleLibraryConfig = field(default_factory=SampleLibraryConfig)
    project_root: str = ""
    output_dir: str = ""
    bible_path: str = ""
    run_log_dir: Optional[str] = None
    current_stage_name: Optional[str] = None
    console_quiet: bool = False

    def __post_init__(self):
        if not self.project_root:
            self.project_root = os.path.dirname(os.path.abspath(__file__))
        if not self.output_dir:
            self.output_dir = os.path.join(self.project_root, "output")
        if not self.bible_path:
            self.bible_path = os.path.join(self.output_dir, "bible.json")
        if not self.sample_library.samples_dir:
            self.sample_library.samples_dir = os.path.join(self.project_root, "samples")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.sample_library.samples_dir, exist_ok=True)


_config_var: _ContextVar[Optional[Config]] = _ContextVar('_config_var', default=None)
_default_config: Optional[Config] = None


def get_config() -> Config:
    """获取当前线程/任务的 Config。"""
    cfg = _config_var.get(None)
    if cfg is not None:
        return cfg
    global _default_config
    if _default_config is None:
        _default_config = Config()
    return _default_config


def set_config(config: Config):
    """在当前线程/任务上下文中设置 Config。"""
    _config_var.set(config)


def _load_json_list(path: str) -> list:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _save_json_list(path: str, items: list):
    with open(path, "w", encoding="utf-8") as f:
        _json.dump(items, f, ensure_ascii=False, indent=2)


def load_custom_models() -> list:
    return _load_json_list(_CUSTOM_MODELS_FILE)


def save_custom_models(models: list):
    _save_json_list(_CUSTOM_MODELS_FILE, models)


def load_llm_profiles() -> list:
    return _load_json_list(_LLM_PROFILES_FILE)


def save_llm_profiles(profiles: list):
    _save_json_list(_LLM_PROFILES_FILE, profiles)


def resolve_provider_to_config(config: Config, provider_str: str):
    """根据 provider 字符串设置 config.llm，支持内置、自定义与配置档。"""
    provider_str = (provider_str or "").strip()

    if provider_str.startswith("profile__"):
        profile_id = provider_str[len("profile__"):]
        profiles = load_llm_profiles()
        matched = next((p for p in profiles if str(p.get("id", "")) == profile_id), None)
        if matched:
            config.llm.provider = LLMProvider.CUSTOM
            config.llm.custom_api_key = matched.get("api_key", "")
            config.llm.custom_base_url = matched.get("base_url", "")
            config.llm.custom_model = matched.get("model", "") or matched.get("name", "") or "custom-model"
            return

    if provider_str.startswith("custom__"):
        name = provider_str[len("custom__"):]
        customs = load_custom_models()
        matched = next((m for m in customs if m["name"] == name), None)
        if matched:
            config.llm.provider = LLMProvider.CUSTOM
            config.llm.custom_api_key = matched.get("api_key", "")
            config.llm.custom_base_url = matched.get("base_url", "")
            config.llm.custom_model = matched.get("model", "") or name
        else:
            config.llm.provider = LLMProvider.OPENAI
        return

    provider_map = {
        "wlai": LLMProvider.WLAI,
        "deepseek": LLMProvider.DEEPSEEK,
        "openai": LLMProvider.OPENAI,
        "claude": LLMProvider.CLAUDE,
        "gemini": LLMProvider.GEMINI,
        "grok": LLMProvider.GROK,
        "grok42": LLMProvider.GROK42,
    }
    config.llm.provider = provider_map.get(provider_str, LLMProvider.OPENAI)
