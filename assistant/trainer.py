import json
from pathlib import Path

EXAMPLES_FILE = Path("datasets/examples.jsonl")
FEEDBACK_FILE = Path("datasets/feedback.jsonl")
TEST_FILE = Path("datasets/test_intents.jsonl")

DATASET_FILES = {
    "feedback": Path("datasets/feedback.jsonl"),
    "examples": Path("datasets/examples.jsonl"),
    "test_intents": Path("datasets/test_intents.jsonl"),
}

def count_jsonl_lines(path):
    if not path.exists():
        return {
            "exists": False,
            "total": 0,
            "valid": 0,
            "broken": 0
        }
        
    total = 0
    valid = 0
    broken = 0
    
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            clean_line = line.strip()
            
            if not clean_line:
                continue
            
            total += 1
            
            try:
                json.loads(clean_line)
                valid += 1
            except:
                broken += 1
                
    return {
        "exists": True,
        "total": total,
        "valid": valid,
        "broken": broken
    }
    
def get_dataset_stats():
    stats = {}
    
    for name, path in DATASET_FILES.items():
        stats[name] = count_jsonl_lines(path)
        
    return stats

def read_jsonl_records(path):
    records = []
    
    if not path.exists():
        return records
    
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            clean_line = line.strip()
            
            if not clean_line:
                continue
            
            try:
                records.append(json.loads(clean_line))
            except:
                continue
            
    return records

def get_record_intent(record):
    for key in ["correct_intent", "intent", "expected"]:
        if key in record:
            return record.get(key)
        
    return None

def get_dataset_intent_counts():
    counts = {}
    
    for dataset_name, path in DATASET_FILES.items():
        records = read_jsonl_records(path)
        
        for record in records:
            intent = get_record_intent(record)
            
            if not intent:
                intent = "unknown"
                
            if intent not in counts:
                counts[intent] = 0
                
            counts[intent] = 1
            
    sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    
    return sorted_counts

def get_record_input(record):
    
    for key in ["input", "message", "text", "query"]:
        if key in record:
            return record.get(key)
        
    return None

def get_dataset_duplicates():
    seen = {}
    duplicates = []
    
    for dataset_name, path in DATASET_FILES.items():
        records = read_jsonl_records(path)
        
        for record in records:
            text = get_record_input(record)
            
            if not text:
                continue
            
            clean_text = text.lower().strip()
            
            if clean_text in seen:
                duplicates.append({
                    "input": clean_text,
                    "first_dataset": seen[clean_text]["dataset"],
                    "duplicate_dataset": dataset_name,
                    "first_intent": seen[clean_text]["intent"],
                    "duplicate_intent": get_record_intent(record)
                })
            else:
                seen[clean_text] = {
                    "dataset": dataset_name,
                    "intent": get_record_intent(record)
                }
                
    return duplicates

def get_dataset_conflicts():
    seen = {}
    conflicts = []
    
    for dataset_name, path in DATASET_FILES.items():
        records = read_jsonl_records(path)
        
        for record in records:
            text = get_record_input(record)
            intent = get_record_intent(record)
            
            if not text or not intent:
                continue
            
            clean_text = text.lower().strip()
            
            if clean_text in seen:
                previous = seen[clean_text]
                
                if previous["intent"] != intent:
                    conflicts.append({
                        "input": clean_text,
                        "first_dataset": previous["dataset"],
                        "first_intent": previous["intent"],
                        "conflict_dataset": dataset_name,
                        "conflict_intent": intent
                    })
                    
            else:
                seen[clean_text] = {
                    "dataset": dataset_name,
                    "intent": intent
                }
                
    return conflicts

def get_dataset_broken_records():
    broken_records = []
    
    for dataset_name, path in DATASET_FILES.items():
        if not path.exists():
            continue
        
        with open(path, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                clean_line = line.strip()
                
                if not clean_line:
                    continue
                
                try:
                    json.loads(clean_line)
                except Exception as error:
                    broken_records.append({
                        "dataset": dataset_name,
                        "line": line_number,
                        "error": str(error)
                    })
                    
    return broken_records

def get_dataset_missing_fields():
    missing = []
    
    for dataset_name, path in DATASET_FILES.items():
        records = read_jsonl_records(path)
        
        for index, record in enumerate(records, start=1):
            text = get_record_input(record)
            intent = get_record_intent(record)
            
            missing_fields = []
            
            if not text:
                missing_fields.append("input")
                
            if not intent:
                missing_fields.append("intent")
                
            if missing_fields:
                missing.append({
                    "dataset": dataset_name,
                    "record": index,
                    "missing": missing_fields
                })
                
    return missing

STOP_WORDS = {
    "can",
    "you",
    "please",
    "could",
    "would",
    "me",
    "my",
    "the",
    "a",
    "an",
    "some",
    "to",
    "for",
    "do",
    "go",
    "lets",
    "let's",
}

WORD_ALIASES = {
    "gaming": "game",
    "games": "game",
    "playing": "play",
    "played": "play",
    "songs": "music",
    "song": "music",
}

COMMAND_WORDS = {
    "play",
    "open",
    "start",
    "launch",
    "set",
    "create",
    "add",
    "remind",
}

def normalize_word(word):
    if word in WORD_ALIASES:
        return WORD_ALIASES[word]
    
    return word

def save_training_example(user_input, intent):
    EXAMPLES_FILE.parent.mkdir(exist_ok=True)
    
    example = {
        "input": user_input,
        "intent": intent
    }
    
    with open(EXAMPLES_FILE, "a") as file:
        file.write(json.dumps(example) + "\n")
        
def feedback_exists(user_input, correct_intent):
    for example in load_feedback_examples():
        same_input = example["input"].strip().lower() == user_input.strip().lower()
        same_intent = example["correct_intent"] == correct_intent
        
        if same_input and same_intent:
            return True
        
    return False
        
def save_feedback(user_input, correct_intent):
    FEEDBACK_FILE.parent.mkdir(exist_ok=True)
    
    if feedback_exists(user_input, correct_intent):
        return False
    
    feedback = {
        "input": user_input,
        "correct_intent": correct_intent
    }
    
    with open(FEEDBACK_FILE, "a") as file:
        file.write(json.dumps(feedback) + "\n")
        
    return True
        
def load_feedback_examples():
    if not FEEDBACK_FILE.exists():
        return []
    
    examples = []
    
    with open(FEEDBACK_FILE, 'r') as file:
        for line in file:
            if line.strip():
                examples.append(json.loads(line))
    
    return examples

def find_learned_intent(user_input):
    best_example, best_score = find_best_match(user_input)
    
    if best_example and best_score >= 0.6:
        return best_example["correct_intent"]
    
    return None

def normalize_text(text):
    text = text.lower().strip()

    for symbol in [".", ",", "?", "!", "'", '"']:
        text = text.replace(symbol, "")
    
    return text

def tokenize(text):
    cleaned_text = normalize_text(text)
    raw_words = cleaned_text.split()
    
    useful_words = []
    
    for word in raw_words:
        normalized_word = normalize_word(word)
        
        if normalized_word not in STOP_WORDS:
            useful_words.append(normalized_word)
    
    return useful_words

def similarity_score(text_a, text_b):
    words_a = set(tokenize(text_a))
    words_b = set(tokenize(text_b))
    
    if not words_a or not words_b:
        return 0
    
    shared_words = words_a.intersection(words_b)
    shorter_length = min(len(words_a), len(words_b))
    
    return len(shared_words) / shorter_length

def find_best_match(user_input):
    best_example = None
    best_score = 0
    
    for example in load_feedback_examples():
        saved_input = example["input"]
        score = similarity_score(user_input, saved_input)
        
        if score > best_score:
            best_score = score
            best_example = example
            
    return best_example, best_score

def train_intent_model():
    model = {}
    
    for example in load_feedback_examples():
        intent = example["correct_intent"]
        words = tokenize(example["input"])
        
        if intent not in model:
            model[intent] = {}
            
        for word in words:
            if word not in model[intent]:
                model[intent][word] = 0
                
            model[intent][word] += 1
            
    return model

def get_word_intent_frequency(model):
    frequencies = {}
    
    for intent, word_counts in model.items():
        for word in word_counts:
            if word not in frequencies:
                frequencies[word] = 0
            
            frequencies[word] += 1
            
    return frequencies

def get_word_weight(word, word_frequencies):
    frequency = word_frequencies.get(word, 0)
    
    if frequency == 0:
        return 0
    
    if word in COMMAND_WORDS:
        return 0.35
    
    if frequency > 1:
        return 0.25
    
    return 1.0

def get_debug_weights(user_input):
    model = train_intent_model()
    word_frequencies = get_word_intent_frequency(model)
    words = tokenize(user_input)
    
    weights = {}
    
    for word in words:
        weights[word] = get_word_weight(word, word_frequencies)
        
    return weights

def summarize_confusion(confusion):
    summary = {}
    
    for item in confusion:
        key = f"{item['expected']} -> {item['predicted']}"
        
        if key not in summary:
            summary[key] = 0
            
        summary[key] += 1
        
    return summary

def predict_intent_with_model(user_input):
    model = train_intent_model()
    words = tokenize(user_input)
    word_frequencies = get_word_intent_frequency(model)
    
    if not words:
        return None, 0, {}
    
    scores = {}
    
    for intent, word_counts in model.items():
        score = 0
        
        for word in words:
            word_count = word_counts.get(word, 0)
            word_weight = get_word_weight(word, word_frequencies)
            
            score += word_count * word_weight
            
        scores[intent] = score
        
    if not scores:
        return None, 0, {}
    
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]
    total_score = sum(scores.values())
    
    if best_score == 0:
        return None, 0, scores
    
    confidence = best_score / total_score
    
    return best_intent, confidence, scores

def load_test_examples():
    if not TEST_FILE.exists():
        return []
    
    examples = []
    
    with open(TEST_FILE, "r") as file:
        for line in file:
            if line.strip():
                examples.append(json.loads(line))
                
    return examples

def evaluate_model():
    test_examples = load_test_examples()
    
    total = 0
    correct = 0
    mistakes = []
    confusion = []
    
    for example in test_examples:
        user_input = example["input"]
        expected_intent = example["intent"]
        
        predicted_intent, confidence, scores = predict_intent_with_model(user_input)
        
        total += 1
        
        if predicted_intent == expected_intent:
            correct += 1
        else:
            mistakes.append({
                "input": user_input,
                "expected": expected_intent,
                "predicted": predicted_intent,
                "confidence": confidence,
                "scores": scores
            })
            
            confusion.append({
                "expected": expected_intent,
                "predicted": predicted_intent,
            })
            
    accuracy = correct / total if total > 0 else 0
    
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "mistakes": mistakes,
        "confusion": confusion
    }