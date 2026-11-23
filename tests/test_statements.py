import pytest
from assistant import statements

@pytest.mark.parametrize("text,mood", [
    ("i am fine, thank you", "fine"), ("I'm so tired", "tired"), ("im good and you", "good"),
    ("i am feeling really stressed", "stressed"), ("i feel tired", "tired"),
    ("i am tired and stressed", "tired and stressed")])
def test_mood(text, mood):
    assert statements.classify(text)["mood"] == mood

@pytest.mark.parametrize("text", [
    "i am going home", "i am not fine", "i feel like pizza", "i am tired of this",
    "i am fine but i need help", "i am learning python", "i am ahmad's friend"])
def test_not_a_mood(text):
    assert (statements.classify(text) or {}).get("kind") != "mood"

def test_name_candidate_and_asked_back():
    assert statements.classify("i am ahmad")["kind"] == "maybe_name"
    assert statements.classify("i'm good, how are you")["asked_back"] is True