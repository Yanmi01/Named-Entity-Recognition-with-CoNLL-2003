# -*- coding: utf-8 -*-
"""NER on CoNLL-2003 Dataset

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1xJNI7-vQThFpU7nPLH7OUq5auDfSNszZ

# Token classification (PyTorch)
"""

!pip install datasets evaluate transformers[sentencepiece]
!pip install accelerate
!apt install git-lfs

"""You will need to setup git, adapt your email and name in the following cell."""

!git config --global user.email "egbewaleyanmife@gmail.com"
!git config --global user.name "Yanmi01"

"""You will also need to be logged in to the Hugging Face Hub. Execute the following and enter your credentials."""

from huggingface_hub import notebook_login

notebook_login()

from datasets import load_dataset

raw_datasets = load_dataset("conll2003")

raw_datasets

#testing the dataset

raw_datasets["train"][0]["tokens"]

raw_datasets["train"][0]["ner_tags"]

# Retrieve the feature definition of the dataset
ner_feature = raw_datasets["train"].features["ner_tags"]
ner_feature

# Convert the ner_feature outpiut to readable tags.
label_names = ner_feature.feature.names
label_names

# Retrieve tokens (words) and NER tag indices for the specific example in the training dataset
words = raw_datasets["train"][5]["tokens"]  # List of words (tokens) in the sentence
labels = raw_datasets["train"][5]["ner_tags"]  # List of corresponding NER tag indices for each word

# Initialize two empty strings to store aligned words and labels
line1 = ""  # For storing words
line2 = ""  # For storing NER tag names

# Iterate over each word and its corresponding NER tag index
for word, label in zip(words, labels):
    full_label = label_names[label]  # Convert label index to its corresponding NER tag name
    max_length = max(len(word), len(full_label))  # Find the maximum length between the word and the label name

    # Add the word& label to line1 & line2 and pad with spaces for alignment
    line1 += word + " " * (max_length - len(word) + 1)
    line2 += full_label + " " * (max_length - len(full_label) + 1)

# Print the aligned words and their corresponding NER tags
print(line1)
print(line2)

# you can also try:
index = 5  # Change this to process a different sentence

# Extract the sentence (tokens and tags) from the dataset
example = raw_datasets["train"][index]
tokens = example["tokens"]  # Words or subwords in the sentence
ner_tags = example["ner_tags"]  # Integer NER tags

# Map numeric NER tags to IOB-format strings
label_names = ['O', 'B-PER', 'I-PER', 'B-ORG', 'I-ORG', 'B-LOC', 'I-LOC', 'B-MISC', 'I-MISC']
iob_tags = [label_names[tag] for tag in ner_tags]

# Display the tokens and their corresponding tags
print(f"{'Token':<15}{'NER Tag'}")
print("-" * 25)
for token, iob_tag in zip(tokens, iob_tags):
    print(f"{token:<15}{iob_tag}")

from transformers import AutoTokenizer

model_checkpoint = "bert-base-cased"
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint)

inputs = tokenizer(raw_datasets["train"][0]["tokens"], is_split_into_words=True)
inputs.tokens()

inputs.word_ids()

# looking at the tokenizer and eeing that words like lamb is being splitted. we're going to write a function that extends the tag to the split chunk of words
def align_labels_with_tokens(labels, word_ids):
    new_labels = []         # list to store the new aligned labels
    current_word = None     # variable to track word id
    for word_id in word_ids:

        if word_id != current_word:     # If this is the start of a new word
            current_word = word_id      # Update the current word tracker
            label = -100 if word_id is None else labels[word_id]      # assign -100 to special token so it isn't computed by the cross entropy loss function as part of the sentence
            new_labels.append(label)

        elif word_id is None:    # if it is a special token
            new_labels.append(-100)    # once again append -100

        else:                     # If this is a subword token that's the same word as the previous token,
            label = labels[word_id]    # Use the label of the original word
            # If the label is B-XXX we change it to I-XXX by adding 1 to make it even
            if label % 2 == 1:
                label += 1
            new_labels.append(label)

    return new_labels

# testing the function
labels = raw_datasets["train"][0]["ner_tags"]
word_ids = inputs.word_ids()
print(labels)
print(align_labels_with_tokens(labels, word_ids))

def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(
        examples["tokens"], truncation=True, is_split_into_words=True
    )
    all_labels = examples["ner_tags"]           # Extract all NER labels from the examples
    new_labels = []
    for i, labels in enumerate(all_labels):
        word_ids = tokenized_inputs.word_ids(i)        # For each example, get the word_ids that show which token belongs to which word
        new_labels.append(align_labels_with_tokens(labels, word_ids))

    tokenized_inputs["labels"] = new_labels
    return tokenized_inputs

tokenized_datasets = raw_datasets.map(
    tokenize_and_align_labels,
    batched=True,
    remove_columns=raw_datasets["train"].column_names,
)

from transformers import DataCollatorForTokenClassification

data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

batch = data_collator([tokenized_datasets["train"][i] for i in range(2)])
batch["labels"]

for i in range(2):
    print(tokenized_datasets["train"][i]["labels"])

!pip install seqeval

import evaluate

metric = evaluate.load("seqeval")

labels = raw_datasets["train"][0]["ner_tags"]
labels = [label_names[i] for i in labels]
labels

predictions = labels.copy()
predictions[2] = "O"
metric.compute(predictions=[predictions], references=[labels])

import numpy as np


def compute_metrics(eval_preds):
    logits, labels = eval_preds
    predictions = np.argmax(logits, axis=-1)

    # Remove ignored index (special tokens) and convert to labels
    true_labels = [[label_names[l] for l in label if l != -100] for label in labels]
    true_predictions = [
        [label_names[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    all_metrics = metric.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": all_metrics["overall_precision"],
        "recall": all_metrics["overall_recall"],
        "f1": all_metrics["overall_f1"],
        "accuracy": all_metrics["overall_accuracy"],
    }

id2label = {i: label for i, label in enumerate(label_names)}
label2id = {v: k for k, v in id2label.items()}

from transformers import AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained(
    model_checkpoint,
    id2label=id2label,
    label2id=label2id,
)

model.config.num_labels

from huggingface_hub import notebook_login

notebook_login()

from transformers import TrainingArguments

args = TrainingArguments(
    "bert-finetuned-ner",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    num_train_epochs=3,
    weight_decay=0.01,
    push_to_hub=True,
)

from transformers import Trainer

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    tokenizer=tokenizer,
)
trainer.train()

trainer.push_to_hub(commit_message="Training complete")

from torch.utils.data import DataLoader

train_dataloader = DataLoader(
    tokenized_datasets["train"],
    shuffle=True,
    collate_fn=data_collator,
    batch_size=8,
)
eval_dataloader = DataLoader(
    tokenized_datasets["validation"], collate_fn=data_collator, batch_size=8
)

model = AutoModelForTokenClassification.from_pretrained(
    model_checkpoint,
    id2label=id2label,
    label2id=label2id,
)

from torch.optim import AdamW

optimizer = AdamW(model.parameters(), lr=2e-5)

from accelerate import Accelerator

accelerator = Accelerator()
model, optimizer, train_dataloader, eval_dataloader = accelerator.prepare(
    model, optimizer, train_dataloader, eval_dataloader
)

from transformers import get_scheduler

num_train_epochs = 3
num_update_steps_per_epoch = len(train_dataloader)
num_training_steps = num_train_epochs * num_update_steps_per_epoch

lr_scheduler = get_scheduler(
    "linear",
    optimizer=optimizer,
    num_warmup_steps=0,
    num_training_steps=num_training_steps,
)

from huggingface_hub import Repository, get_full_repo_name

model_name = "bert-finetuned-ner-accelerate"
repo_name = get_full_repo_name(model_name)
repo_name

output_dir = "bert-finetuned-ner-accelerate"
repo = Repository(output_dir, clone_from=repo_name)

def postprocess(predictions, labels):
    predictions = predictions.detach().cpu().clone().numpy()
    labels = labels.detach().cpu().clone().numpy()

    # Remove ignored index (special tokens) and convert to labels
    true_labels = [[label_names[l] for l in label if l != -100] for label in labels]
    true_predictions = [
        [label_names[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    return true_labels, true_predictions

from tqdm.auto import tqdm
import torch

progress_bar = tqdm(range(num_training_steps))

for epoch in range(num_train_epochs):
    # Training
    model.train()
    for batch in train_dataloader:
        outputs = model(**batch)
        loss = outputs.loss
        accelerator.backward(loss)

        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()
        progress_bar.update(1)

    # Evaluation
    model.eval()
    for batch in eval_dataloader:
        with torch.no_grad():
            outputs = model(**batch)

        predictions = outputs.logits.argmax(dim=-1)
        labels = batch["labels"]

        # Necessary to pad predictions and labels for being gathered
        predictions = accelerator.pad_across_processes(predictions, dim=1, pad_index=-100)
        labels = accelerator.pad_across_processes(labels, dim=1, pad_index=-100)

        predictions_gathered = accelerator.gather(predictions)
        labels_gathered = accelerator.gather(labels)

        true_predictions, true_labels = postprocess(predictions_gathered, labels_gathered)
        metric.add_batch(predictions=true_predictions, references=true_labels)

    results = metric.compute()
    print(
        f"epoch {epoch}:",
        {
            key: results[f"overall_{key}"]
            for key in ["precision", "recall", "f1", "accuracy"]
        },
    )

    # Save and upload
    accelerator.wait_for_everyone()
    unwrapped_model = accelerator.unwrap_model(model)
    unwrapped_model.save_pretrained(output_dir, save_function=accelerator.save)
    if accelerator.is_main_process:
        tokenizer.save_pretrained(output_dir)
        repo.push_to_hub(
            commit_message=f"Training in progress epoch {epoch}", blocking=False
        )

accelerator.wait_for_everyone()
unwrapped_model = accelerator.unwrap_model(model)
unwrapped_model.save_pretrained(output_dir, save_function=accelerator.save)

from transformers import pipeline

# Replace this with your own checkpoint
model_checkpoint = "huggingface-course/bert-finetuned-ner"
token_classifier = pipeline(
    "token-classification", model=model_checkpoint, aggregation_strategy="simple"
)
token_classifier("My name is Sylvain and I work at Hugging Face in Brooklyn.")

