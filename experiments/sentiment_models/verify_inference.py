"""Check chunk adapter against each real tokenizer's ordinary single-text call."""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, BertTokenizer, BertForSequenceClassification
from benchmark import DEFAULT, MODELS, encode_chunk, save

torch.set_num_threads(2)
checks = []
for name in MODELS:
    path = DEFAULT / 'models' / name
    if name == 'hkust_finbert':
        tokenizer = BertTokenizer(vocab=str(path / 'vocab.txt'), do_lower_case=True)
        model_class = BertForSequenceClassification
    else:
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        model_class = AutoModelForSequenceClassification
    model = model_class.from_pretrained(path, local_files_only=True, trust_remote_code=False,
                                      use_safetensors=False, weights_only=True).eval()
    assert len(tokenizer) == model.get_input_embeddings().num_embeddings
    sample = 'Revenue fell by 20 percent. The company called it a serious setback.'
    direct = tokenizer(sample, return_tensors='pt', truncation=False)
    prepared = encode_chunk(tokenizer, tokenizer.encode(sample, add_special_tokens=False))
    encoded = {k: torch.tensor([v]) for k, v in prepared.items()}
    assert set(direct) == set(encoded)
    assert all(torch.equal(direct[k], encoded[k]) for k in direct)
    with torch.inference_mode():
        a, b = model(**direct).logits, model(**encoded).logits
    assert torch.equal(a, b)
    checks.append({'model': name, 'vocabulary': len(tokenizer), 'inputs_equal': True,
                   'max_logit_difference': (a - b).abs().max().item(),
                   'predicted_label': model.config.id2label[a.argmax(-1).item()].lower()})
save(DEFAULT / 'inference-verification.json', checks)
print(checks)
