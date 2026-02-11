"""
HOTARU AI Transformer package.

Ce package regroupe les briques d'analyse et de transformation
du HTML pour optimiser la lisibilité par les IA.
"""

from .analyzer import HTMLAnalyzer
from .transformer import AIOptimizedTransformer
from .scorer import AIScorer, ScoreCard
from .visualizer import HTMLVisualizer
from .ai_transformer_page import render_ai_transformer_tab

__all__ = [
    "HTMLAnalyzer",
    "AIOptimizedTransformer",
    "AIScorer",
    "ScoreCard",
    "HTMLVisualizer",
    "render_ai_transformer_tab",
]

