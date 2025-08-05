"""
Personal AI Models Configuration
Centralized configuration for all available personal AI models
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ModelCategory(Enum):
    CODING_AGENT = "coding_agent"
    REASONING = "reasoning"
    GENERAL = "general"
    CREATIVE = "creative"
    RESEARCH = "research"
    FAST_RESPONSE = "fast_response"

class HardwareRequirement(Enum):
    LIGHT = "light"      # 8GB RAM, no GPU needed
    MEDIUM = "medium"    # 16GB RAM, optional GPU
    HEAVY = "heavy"      # 32GB RAM, GPU recommended
    EXTREME = "extreme"  # 64GB RAM, high-end GPU required

@dataclass
class ModelConfig:
    """Configuration for a personal AI model"""
    id: str
    name: str
    display_name: str
    description: str
    category: ModelCategory
    size_gb: float
    parameters: str
    hardware_req: HardwareRequirement
    specialties: List[str]
    download_url: str
    model_family: str
    context_window: int
    speed_rating: int  # 1-10 scale
    quality_rating: int  # 1-10 scale
    license: str
    repository: str
    use_cases: List[str]
    pros: List[str]
    cons: List[str]
    recommended_for: List[str]
    training_data_focus: str
    inference_engine: str  # ollama, vllm, etc.
    quantization: str  # 4bit, 8bit, fp16, etc.
    
# Available Personal AI Models (2025)
AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    "devstral_small": ModelConfig(
        id="devstral_small",
        name="mistral/devstral-small-1.1",
        display_name="Code Agent Pro",
        description="Autonomous coding agent that explores codebases and makes multi-file edits",
        category=ModelCategory.CODING_AGENT,
        size_gb=15.0,
        parameters="24B",
        hardware_req=HardwareRequirement.HEAVY,
        specialties=["Multi-file editing", "Codebase exploration", "Autonomous coding", "Bug fixing"],
        download_url="https://huggingface.co/mistralai/Devstral-Small-1.1",
        model_family="Mistral",
        context_window=128000,
        speed_rating=7,
        quality_rating=9,
        license="Apache 2.0",
        repository="mistralai/Devstral-Small-1.1",
        use_cases=["Software development", "Code refactoring", "Bug hunting", "Architecture changes"],
        pros=["Best SWE-Bench performance", "Agentic capabilities", "Open source", "Single GPU"],
        cons=["High memory usage", "Newer model (less community support)"],
        recommended_for=["Professional developers", "Complex codebases", "Automated coding"],
        training_data_focus="Real GitHub issues and repositories",
        inference_engine="ollama",
        quantization="4bit"
    ),
    
    "deepseek_r1_8b": ModelConfig(
        id="deepseek_r1_8b",
        name="deepseek/deepseek-r1-distill-llama-8b",
        display_name="Deep Reasoner",
        description="Advanced reasoning model for complex problem-solving and step-by-step analysis",
        category=ModelCategory.REASONING,
        size_gb=5.0,
        parameters="8B",
        hardware_req=HardwareRequirement.MEDIUM,
        specialties=["Chain-of-thought reasoning", "Math problems", "Complex logic", "Self-verification"],
        download_url="https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        model_family="DeepSeek",
        context_window=32768,
        speed_rating=6,
        quality_rating=9,
        license="MIT",
        repository="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        use_cases=["Complex problem solving", "Mathematical reasoning", "Research analysis", "Logic puzzles"],
        pros=["Superior reasoning", "Cost-effective", "Good hardware support"],
        cons=["Slower responses", "Verbose output"],
        recommended_for=["Research tasks", "Complex analysis", "Educational content"],
        training_data_focus="Reasoning tasks and mathematical problems",
        inference_engine="ollama",
        quantization="4bit"
    ),
    
    "qwen_coder_7b": ModelConfig(
        id="qwen_coder_7b",
        name="qwen/qwen2.5-coder-7b-instruct",
        display_name="Multi-Language Expert",
        description="Specialized coding model supporting 92 programming languages with large context",
        category=ModelCategory.CODING_AGENT,
        size_gb=4.0,
        parameters="7B",
        hardware_req=HardwareRequirement.MEDIUM,
        specialties=["92 programming languages", "Large codebase analysis", "Code completion", "Debugging"],
        download_url="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct",
        model_family="Qwen",
        context_window=128000,
        speed_rating=8,
        quality_rating=8,
        license="Apache 2.0",
        repository="Qwen/Qwen2.5-Coder-7B-Instruct",
        use_cases=["Multi-language projects", "Code completion", "Large codebase navigation", "API integration"],
        pros=["Broad language support", "Large context window", "Fast inference"],
        cons=["Less specialized than single-language models"],
        recommended_for=["Full-stack developers", "Multi-language teams", "Large projects"],
        training_data_focus="5.5T tokens across 92 programming languages",
        inference_engine="ollama",
        quantization="4bit"
    ),
    
    "mistral_small_3": ModelConfig(
        id="mistral_small_3",
        name="mistral/mistral-small-3-instruct",
        display_name="Quick Assistant",
        description="Fast, efficient general-purpose model for everyday conversations and tasks",
        category=ModelCategory.FAST_RESPONSE,
        size_gb=15.0,
        parameters="24B",
        hardware_req=HardwareRequirement.HEAVY,
        specialties=["Fast responses", "General knowledge", "Conversational AI", "Quick problem solving"],
        download_url="https://huggingface.co/mistralai/Mistral-Small-3-Instruct",
        model_family="Mistral",
        context_window=32768,
        speed_rating=9,
        quality_rating=8,
        license="Apache 2.0",
        repository="mistralai/Mistral-Small-3-Instruct",
        use_cases=["Daily conversations", "Quick questions", "General assistance", "Brainstorming"],
        pros=["Very fast", "Efficient", "Good general knowledge"],
        cons=["Less specialized capabilities"],
        recommended_for=["Daily use", "General assistance", "Quick consultations"],
        training_data_focus="General internet text with instruction tuning",
        inference_engine="ollama",
        quantization="4bit"
    ),
    
    "llama_3_1_8b": ModelConfig(
        id="llama_3_1_8b",
        name="meta/llama-3.1-8b-instruct",
        display_name="Research Assistant",
        description="Meta's latest model optimized for research, analysis, and detailed explanations",
        category=ModelCategory.RESEARCH,
        size_gb=5.0,
        parameters="8B",
        hardware_req=HardwareRequirement.MEDIUM,
        specialties=["Research analysis", "Detailed explanations", "Academic writing", "Data interpretation"],
        download_url="https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct",
        model_family="Llama",
        context_window=128000,
        speed_rating=7,
        quality_rating=8,
        license="Llama 3.1 License",
        repository="meta-llama/Meta-Llama-3.1-8B-Instruct",
        use_cases=["Research papers", "Analysis reports", "Educational content", "Data science"],
        pros=["Strong reasoning", "Large community", "Well-documented"],
        cons=["Larger model family available"],
        recommended_for=["Researchers", "Students", "Content creators"],
        training_data_focus="Diverse internet text with focus on factual accuracy",
        inference_engine="ollama",
        quantization="4bit"
    ),
    
    "deepseek_v3_8b": ModelConfig(
        id="deepseek_v3_8b",
        name="deepseek/deepseek-v3-8b-instruct",
        display_name="General Assistant",
        description="Balanced general-purpose model with strong reasoning and conversational abilities",
        category=ModelCategory.GENERAL,
        size_gb=5.0,
        parameters="8B",
        hardware_req=HardwareRequirement.MEDIUM,
        specialties=["General conversations", "Balanced reasoning", "Multi-domain knowledge", "Cost-effective"],
        download_url="https://huggingface.co/deepseek-ai/DeepSeek-V3-8B-Instruct",
        model_family="DeepSeek",
        context_window=64000,
        speed_rating=8,
        quality_rating=7,
        license="MIT",
        repository="deepseek-ai/DeepSeek-V3-8B-Instruct",
        use_cases=["General assistance", "Mixed tasks", "Balanced workloads", "Cost-conscious usage"],
        pros=["Good balance", "Cost-effective", "Decent performance"],
        cons=["Not specialized for specific tasks"],
        recommended_for=["General users", "Mixed workloads", "Budget-conscious users"],
        training_data_focus="Balanced mix of general and specialized content",
        inference_engine="ollama",
        quantization="4bit"
    )
}

# Model recommendations based on user type
RECOMMENDED_SETUPS = {
    "beginner": {
        "models": ["mistral_small_3", "qwen_coder_7b"],
        "total_size": 19.0,
        "description": "Perfect for getting started with personal AI"
    },
    "developer": {
        "models": ["devstral_small", "qwen_coder_7b", "deepseek_r1_8b"],
        "total_size": 24.0,
        "description": "Comprehensive coding and reasoning capabilities"
    },
    "researcher": {
        "models": ["llama_3_1_8b", "deepseek_r1_8b", "mistral_small_3"],
        "total_size": 25.0,
        "description": "Research, analysis, and general assistance"
    },
    "power_user": {
        "models": list(AVAILABLE_MODELS.keys()),
        "total_size": 49.0,
        "description": "Complete personal AI toolkit"
    }
}

def get_model_by_id(model_id: str) -> Optional[ModelConfig]:
    """Get model configuration by ID"""
    return AVAILABLE_MODELS.get(model_id)

def get_models_by_category(category: ModelCategory) -> List[ModelConfig]:
    """Get all models in a specific category"""
    return [model for model in AVAILABLE_MODELS.values() if model.category == category]

def get_recommended_setup(user_type: str) -> Dict:
    """Get recommended model setup for user type"""
    return RECOMMENDED_SETUPS.get(user_type, RECOMMENDED_SETUPS["beginner"])

def calculate_total_size(model_ids: List[str]) -> float:
    """Calculate total size for a list of model IDs"""
    return sum(AVAILABLE_MODELS[mid].size_gb for mid in model_ids if mid in AVAILABLE_MODELS)

def get_models_by_hardware(hardware_req: HardwareRequirement) -> List[ModelConfig]:
    """Get models that match hardware requirements"""
    return [model for model in AVAILABLE_MODELS.values() if model.hardware_req == hardware_req]
# Personal AI Models Configuration
# This file contains the configuration for all available personal AI models

PERSONAL_MODELS_CONFIG = {
    "llama_3_1_8b": {
        "id": "llama_3_1_8b",
        "name": "meta/llama-3.1-8b-instruct",
        "display_name": "Llama 3.1 8B Instruct",
        "description": "General-purpose conversational AI with strong reasoning capabilities",
        "category": "general_purpose",
        "size_gb": 5.0,
        "parameters": "8B",
        "context_window": 128000,
        "hardware_req": "8GB RAM",
        "model_family": "Llama",
        "repository": "meta-llama/Llama-3.1-8B-Instruct",
        "license": "Llama 3.1 License",
        "specialties": ["conversation", "reasoning", "analysis"],
        "use_cases": ["general chat", "research assistance", "content analysis"],
        "pros": ["Strong reasoning", "Large context window", "Well-rounded"],
        "cons": ["Requires 8GB RAM", "Slower than smaller models"]
    },
    "qwen_coder_7b": {
        "id": "qwen_coder_7b",
        "name": "qwen/qwen2.5-coder-7b-instruct",
        "display_name": "Qwen 2.5 Coder 7B",
        "description": "Specialized coding assistant supporting 92+ programming languages",
        "category": "coding",
        "size_gb": 4.0,
        "parameters": "7B",
        "context_window": 128000,
        "hardware_req": "6GB RAM",
        "model_family": "Qwen",
        "repository": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "license": "Apache 2.0",
        "specialties": ["programming", "code analysis", "debugging"],
        "use_cases": ["code completion", "bug fixing", "code review"],
        "pros": ["92 languages", "Large context", "Fast inference"],
        "cons": ["Coding focused", "Less general knowledge"]
    },
    "deepseek_r1_8b": {
        "id": "deepseek_r1_8b",
        "name": "deepseek/deepseek-r1-distill-qwen-8b",
        "display_name": "DeepSeek R1 8B",
        "description": "Advanced reasoning model with step-by-step problem solving",
        "category": "reasoning",
        "size_gb": 5.0,
        "parameters": "8B",
        "context_window": 8192,
        "hardware_req": "8GB RAM",
        "model_family": "DeepSeek",
        "repository": "deepseek-ai/DeepSeek-R1-Distill-Qwen-8B",
        "license": "MIT",
        "specialties": ["reasoning", "mathematics", "logic"],
        "use_cases": ["complex problem solving", "math help", "logical analysis"],
        "pros": ["Excellent reasoning", "Step-by-step thinking", "Math focused"],
        "cons": ["Smaller context window", "Specialized use case"]
    },
    "deepseek_v3_8b": {
        "id": "deepseek_v3_8b",
        "name": "deepseek/deepseek-v3-8b-instruct",
        "display_name": "DeepSeek V3 8B",
        "description": "Balanced general-purpose model with strong performance",
        "category": "general_purpose",
        "size_gb": 5.0,
        "parameters": "8B",
        "context_window": 64000,
        "hardware_req": "8GB RAM",
        "model_family": "DeepSeek",
        "repository": "deepseek-ai/DeepSeek-V3-8B-Instruct",
        "license": "MIT",
        "specialties": ["general knowledge", "conversation", "analysis"],
        "use_cases": ["daily assistance", "research", "content creation"],
        "pros": ["Well-balanced", "Good performance", "Reliable"],
        "cons": ["Not specialized", "Medium context window"]
    },
    "mistral_small_3": {
        "id": "mistral_small_3",
        "name": "mistral/mistral-small-3-instruct",
        "display_name": "Mistral Small 3",
        "description": "Fast and efficient model for quick responses",
        "category": "general_purpose",
        "size_gb": 15.0,
        "parameters": "22B",
        "context_window": 32768,
        "hardware_req": "16GB RAM",
        "model_family": "Mistral",
        "repository": "mistralai/Mistral-Small-Instruct-2409",
        "license": "Apache 2.0",
        "specialties": ["quick responses", "general knowledge", "efficiency"],
        "use_cases": ["fast chat", "quick questions", "lightweight tasks"],
        "pros": ["Very fast", "Efficient", "Good quality"],
        "cons": ["Larger size", "Higher RAM requirement"]
    },
    "devstral_small": {
        "id": "devstral_small",
        "name": "mistral/devstral-small-1.1",
        "display_name": "Mistral Devstral Small",
        "description": "Specialized development assistant for code analysis and generation",
        "category": "coding",
        "size_gb": 15.0,
        "parameters": "22B",
        "context_window": 32768,
        "hardware_req": "16GB RAM",
        "model_family": "Mistral",
        "repository": "mistralai/Devstral-Small-1.1",
        "license": "Apache 2.0",
        "specialties": ["code generation", "debugging", "refactoring"],
        "use_cases": ["software development", "code review", "architecture"],
        "pros": ["Development focused", "High quality code", "Multi-language"],
        "cons": ["Large size", "Development focused only"]
    }
}
