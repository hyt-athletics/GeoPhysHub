# GeoPhysHub - 井中地球物理算法集成插件平台

## 项目简介

GeoPhysHub 是一个基于插件架构的井中地球物理算法集成平台，用于管理和运行各种地球物理数据处理算法。

## 目录结构

```
GeoPhysHub/
├── src/          # 主程序源代码
├── plugins/      # 算法插件目录
├── tests/        # 测试代码
├── .venv/        # 虚拟环境
├── requirements.txt  # Python依赖包
└── README.md     # 项目说明文档
```

## 主要功能

- 插件化架构，支持灵活的算法扩展
- Streamlit 可视化界面
- 支持 LAS 格式测井数据处理
- 集成 numpy 和 matplotlib 进行数据处理和可视化

## 安装使用

1. 激活虚拟环境
2. 安装依赖：`pip install -r requirements.txt`
3. 运行项目

## 依赖包

- streamlit>=1.20.0 - Web应用框架
- pluggy>=1.0.0 - 插件系统
- numpy>=1.20.0 - 数值计算
- lasio>=0.30.0 - LAS文件处理
- matplotlib>=3.5.0 - 数据可视化
