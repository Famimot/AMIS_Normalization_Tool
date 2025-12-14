from setuptools import setup, find_packages
import codecs
import os

# Read README for long description
here = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="amis_tool",
    version="4.3.0",
    author="Gennadiy Kravtsov",
    author_email="62abc@mail.ru",
    description="Adaptive Multi-Interval Scale (AMIS) - normalization and comparison of heterogeneous metrics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Famimot/AMIS_Normalization_Tool",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Education :: Testing",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "matplotlib>=3.4.0",
        "openpyxl>=3.0.0",
    ],
    keywords=[
        "normalization",
        "data-analysis",
        "education",
        "statistics",
        "AMIS",
        "adaptive-scaling",
        "metric-comparison",
    ],
    project_urls={
        "Homepage": "https://github.com/Famimot/AMIS_Normalization_Tool",
        "Bug Tracker": "https://github.com/Famimot/AMIS_Normalization_Tool/issues",
        "Documentation": "https://github.com/Famimot/AMIS_Normalization_Tool#readme",
    },
    include_package_data=True,
    entry_points={
        'gui_scripts': [
            'amis=run_amis:main',  # Запуск из run_amis.py в корне
        ],
    },
)