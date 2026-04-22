"""Skill alias normalization."""
from __future__ import annotations


# Maps common resume variants → canonical graph vocab names (lowercase key)
_SKILL_ALIASES: dict[str, str] = {
    # Game engine
    "unreal engine 5": "Unreal", "unreal engine 4": "Unreal",
    "ue5": "Unreal", "ue4": "Unreal", "unreal engine": "Unreal",
    "unity3d": "Unity",
    # Spring / Java
    "springboot": "Spring Boot", "spring-boot": "Spring Boot",
    "spring boot framework": "Spring Boot",
    "mybatisplus": "MyBatis", "mybatis-plus": "MyBatis",
    # LangChain ecosystem
    "langgraph": "LangChain", "langchain4j": "LangChain",
    "langserve": "LangChain", "langchain/langgraph": "LangChain",
    # Vector DBs
    "pgvector": "Vector DB", "pinecone": "Vector DB",
    "weaviate": "Vector DB", "chroma": "Vector DB",
    "milvus": "Vector DB", "qdrant": "Vector DB",
    # LLM APIs
    "openai api": "OpenAI API", "chatgpt api": "OpenAI API",
    "gpt-4": "OpenAI API", "gpt4": "OpenAI API",
    "dashscope": "OpenAI API",
    # Frontend
    "react.js": "React", "reactjs": "React",
    "vue.js": "Vue.js", "vuejs": "Vue.js",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
    # DB
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    # K8s
    "k8s": "Kubernetes",
    # PyTorch / TF
    "pytorch": "PyTorch", "tensorflow": "TensorFlow",
    # CV / Medical Imaging / Deep Learning
    "opencv": "OpenCV",
    "图像分割": "图像分割", "image segmentation": "图像分割",
    "目标检测": "目标检测", "object detection": "目标检测",
    "语义分割": "语义分割", "semantic segmentation": "语义分割",
    "实例分割": "实例分割", "instance segmentation": "实例分割",
    "三维重建": "三维重建", "3d reconstruction": "三维重建",
    "nerf": "NeRF",
    "mamba": "Mamba", "mamba模型": "Mamba", "state space model": "Mamba",
    "cnn": "CNN", "卷积神经网络": "CNN",
    "transformer": "Transformer",
    "unet": "U-Net", "u-net": "U-Net",
    "medsam": "MedSAM", "sam": "SAM",
    "gan": "GAN", "生成对抗网络": "GAN",
    "diffusion": "Diffusion", "扩散模型": "Diffusion",
    "resnet": "ResNet",
    "vit": "ViT", "vision transformer": "ViT",
    "yolo": "YOLO",
    "医学图像处理": "医学图像处理", "medical image processing": "医学图像处理",
    "计算机视觉": "计算机视觉", "computer vision": "计算机视觉",
    "深度学习": "深度学习", "deep learning": "深度学习",
    "机器学习": "机器学习", "machine learning": "机器学习",
    "神经网络": "神经网络", "neural network": "神经网络",
    "迁移学习": "迁移学习", "transfer learning": "迁移学习",
    "领域自适应": "领域自适应", "domain adaptation": "领域自适应",
    "半监督学习": "半监督学习", "semi-supervised learning": "半监督学习",
    "自监督学习": "自监督学习", "self-supervised learning": "自监督学习",
    "特征工程": "特征工程", "feature engineering": "特征工程",
    "模型微调": "模型微调", "fine-tuning": "模型微调", "finetune": "模型微调",
    "模型蒸馏": "模型蒸馏", "knowledge distillation": "模型蒸馏",
    "量化部署": "量化部署", "model quantization": "量化部署",
    "onnx": "ONNX",
    "tensorrt": "TensorRT",
    "数据处理": "数据处理",
    "数据增强": "数据增强", "data augmentation": "数据增强",
    "numpy": "NumPy", "np": "NumPy",
    "pandas": "Pandas", "pd": "Pandas",
    "matplotlib": "Matplotlib",
    "scipy": "SciPy",
    "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
    "jupyter": "Jupyter",
    "anaconda": "Anaconda",
    "cuda": "CUDA", "gpu编程": "CUDA",
    "docker": "Docker",
    "git": "Git", "github": "Git",
    "linux": "Linux",
    "latex": "LaTeX",
    "markdown": "Markdown",
}


def _normalize_skill_name(name: str) -> str:
    return _SKILL_ALIASES.get(name.lower().strip(), name)


def _normalize_skills(skills: list) -> list:
    """Normalize each skill's name using the alias map."""
    result = []
    for s in skills:
        if isinstance(s, dict):
            result.append({**s, "name": _normalize_skill_name(s.get("name", ""))})
        else:
            result.append(s)
    return result
