"""Pure helpers: Ollama address parsing (KI-033), export filenames (KI-017), model keys (KI-020), coercion (KI-016)."""
import pytest

import main
from models import Character, CharacterType, Scene, as_int

# The doctest cases of ollama-python's _parse_host (0.6.3), which _ollama_base_url mirrors.
OLLAMA_HOST_CASES = [
    (None, "http://127.0.0.1:11434"),
    ("", "http://127.0.0.1:11434"),
    ("1.2.3.4", "http://1.2.3.4:11434"),
    (":56789", "http://127.0.0.1:56789"),
    ("1.2.3.4:56789", "http://1.2.3.4:56789"),
    ("http://1.2.3.4", "http://1.2.3.4:80"),
    ("https://1.2.3.4", "https://1.2.3.4:443"),
    ("https://1.2.3.4:56789", "https://1.2.3.4:56789"),
    ("example.com", "http://example.com:11434"),
    ("example.com:56789", "http://example.com:56789"),
    ("http://example.com", "http://example.com:80"),
    ("https://example.com", "https://example.com:443"),
    ("https://example.com:56789", "https://example.com:56789"),
    ("example.com/", "http://example.com:11434"),
    ("example.com:56789/", "http://example.com:56789"),
    ("example.com/path", "http://example.com:11434/path"),
    ("example.com:56789/path", "http://example.com:56789/path"),
    ("https://example.com:56789/path", "https://example.com:56789/path"),
    ("example.com:56789/path/", "http://example.com:56789/path"),
    ("[0001:002:003:0004::1]", "http://[0001:002:003:0004::1]:11434"),
    ("[0001:002:003:0004::1]:56789", "http://[0001:002:003:0004::1]:56789"),
    ("http://[0001:002:003:0004::1]", "http://[0001:002:003:0004::1]:80"),
    ("https://[0001:002:003:0004::1]", "https://[0001:002:003:0004::1]:443"),
    ("https://[0001:002:003:0004::1]:56789", "https://[0001:002:003:0004::1]:56789"),
    ("[0001:002:003:0004::1]/", "http://[0001:002:003:0004::1]:11434"),
    ("[0001:002:003:0004::1]:56789/", "http://[0001:002:003:0004::1]:56789"),
    ("[0001:002:003:0004::1]/path", "http://[0001:002:003:0004::1]:11434/path"),
    ("[0001:002:003:0004::1]:56789/path", "http://[0001:002:003:0004::1]:56789/path"),
    ("https://[0001:002:003:0004::1]:56789/path", "https://[0001:002:003:0004::1]:56789/path"),
    ("[0001:002:003:0004::1]:56789/path/", "http://[0001:002:003:0004::1]:56789/path"),
]


@pytest.mark.parametrize("host,expected", OLLAMA_HOST_CASES)
def test_ollama_base_url_matches_ollama_python(host, expected):
    assert main._ollama_base_url(host) == expected


@pytest.mark.parametrize("title,fmt,expected", [
    ("Untitled Novel", "txt", "Untitled_Novel.txt"),
    ("A: B/C?", "txt", "A__B_C_.txt"),
    ("林凡传奇", "md", "林凡传奇.md"),
    ("???", "md", "novel.md"),
    ("End.", "txt", "End.txt"),
    ('Bad<>"|*\\name', "txt", "Bad______name.txt"),
    ("  ", "txt", "novel.txt"),
])
def test_export_filename(title, fmt, expected):
    assert main._export_filename(title, fmt) == expected


@pytest.mark.parametrize("name,key", [
    ("gemma3", "gemma3:latest"),
    ("gemma3:12b", "gemma3:12b"),
    ("host:5000/ns/model", "host:5000/ns/model:latest"),
    ("host:5000/ns/model:7b", "host:5000/ns/model:7b"),
])
def test_model_key(name, key):
    assert main._model_key(name) == key


def test_models_coerce_near_miss_llm_values():
    c = Character(name="Elder Wu", slug="elder_wu", age=70, type="supporting", abilities="sword", habits=None)
    assert c.age == "70"
    assert c.type == CharacterType.TEMPORARY
    assert c.abilities == ["sword"]
    assert c.habits == []
    assert Character(name="Lin", slug="lin", type="Main Character").type == CharacterType.MAIN
    assert Scene(name="Cave", slug="cave", known_inhabitants="Elder Wu").known_inhabitants == ["Elder Wu"]
    assert as_int("2", 1) == 2 and as_int("many", 1) == 1


def test_models_still_require_name_and_slug():
    with pytest.raises(ValueError):
        Character(slug="no_name")
