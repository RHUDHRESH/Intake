import langgraph
import langchain
import langchain_google_vertexai
import langchain_anthropic
import sentence_transformers
import chromadb
import faiss
import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import dash

from classifiers import AdaptiveQuestionnaire, BusinessTypeClassifier, FrameworkSelector
from graphs.intake_graph import compile_intake_graph


def main() -> None:
    classifier = BusinessTypeClassifier()
    questionnaire = AdaptiveQuestionnaire()
    selector = FrameworkSelector()
    graph = compile_intake_graph()

    assert classifier.get_classification_questions(), "Classifier failed to load"
    assert questionnaire.UNIVERSAL_QUESTIONS, "Questionnaire missing universal questions"
    assert selector.BASE_FRAMEWORKS, "Framework selector missing base map"
    assert graph, "Graph compilation failed"

    print("All critical imports succeeded.")


if __name__ == "__main__":
    main()
