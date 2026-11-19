# The Unofficial Guide

A retrieval-augmented generation (RAG) application that answers questions
about a fictional region using a collection of 14 city-guide documents.

The system retrieves relevant passages from a vector database, generates
answers with source-document citations, and declines questions when the
retrieved material falls outside its relevance threshold.

## Features

- Section-aware Markdown chunking that preserves document and topic context.
- Vector search over guides covering travel, dining, accommodation,
  accessibility, and local activities.
- Source-document citations in generated answers.
- A relevance gate for declining unsupported questions.
- Evaluation of retrieval coverage, citation accuracy, chunk structure,
  and out-of-scope refusal.

## Design focus

This project explores how document structure and retrieval thresholds
affect grounded answers. Custom chunking follows Markdown sections rather
than fixed character windows, while the relevance cutoff was selected
by comparing retrieval distances for in-scope and out-of-scope questions.

The evaluation also documents a scoring bug that incorrectly marked
correct answers as failures, and the changes made to the reference
answers and scorer to resolve it.

## Run locally

See [RUNNING.md](RUNNING.md) for setup and execution instructions.

## Project origins

Built for CodePath AI201 from The Unofficial Guide
starter. The sections below document the implementation decisions,
evaluation results, AI assistance, and remaining limitations.

---

# Unit 1

## What This Does

This project uses a vector database to answer questions about the 'city_guides' corpus, which consists of 14 markdown files covering various locations in a fictional region. These guides cover topics such as travel, sightseeing, activities, restaurants, and accommodation.

## Chunking Strategy

**Chunk size:** 400
**Overlap:** 0

The starter chunker's 800 character window often cut directly across markdown section headers, which fragmented the content, often merging unrelated subjects or splitting important sentences in half. This was most noticeable in the verbosity/length of responses for questions that required more than one section to answer.

Measuring the section sizes across each file helped me identify that most sections were under the 400 character threshold, with an average of 358 characters. I used this as a baseline and decided to make the chunk size 400. Since each `##` section is an independent topic, using character overlap made little sense for this dataset, as it would reintroduce fragmentation issues. Instead, I attached the `##` title to the front of each chunk to preserve the topic context and ensure the embedding model and LLM see which section the chunk came from. I also noticed that the section title provides more relevant context than the source filename alone.

In the initial prototype, a plain split on the section headers produced 5 violations of Criterion 4 (minimum 150 characters, 2+ complete sentences). This was due to some files not having any text before the first section header, which resulted in tiny title chunks or some chunks with only 1 sentence. I fixed this by updating the chunking logic to merge the intro text into the file's first `##` section chunk, resulting in 84 chunks with 0 violations of Criterion 4.

## Sample Chunks

**Chunk 1** — source: `guide_accessibility.md#0` — produced by: `chunker.py::split_documents`

```
# Getting around the region with limited mobility

An honest assessment rather than a promotional one. Some of these places are

difficult and it is better to know in advance.

## Straightforward

**Thornby Wells** is the easiest town in the region. It is flat, compact, and
everything is within three minutes of everything else. Parking is free for two
hours anywhere in town and the station is central. The pump room and gardens
are level throughout.

**Marchwood** has a modern tram network with level boarding on all four lines,
running every 8 minutes on weekdays. The city museum and covered market are both
step-free. The distances between districts are the main consideration.

**Brightwater** is level along the river and through the centre. The mill museum
is step-free. The station is a 15-minute walk from campus on flat ground, or the
shuttle meets the four busiest arrivals.
```

**Chunk 2** — source: `guide_corry_vale.md#5` — produced by: `chunker.py::split_documents`

```
# Corry Vale

## When to go

May to September. Outside those months the pub in the third village closes, the farm shop reduces its hours, and several footpaths become genuinely boggy rather than merely wet. The road is not gritted above the second village and is impassable in snow.
```

**Chunk 3** — source: `guide_givens_mill.md#2` — produced by: `chunker.py::split_documents`

```
# Givens Mill

## Eat and drink

A tearoom attached to the mill, open 10 to 4 daily except Tuesdays, which sells bread made from the flour ground twenty metres away and is the reason most people come. One pub, food served lunchtimes and Thursday to Saturday evenings.
```

**Chunk 4** — source: `guide_kestrelford.md#4` — produced by: `chunker.py::split_documents`

```
# Kestrelford

## Where to stay

Two inns on the square and a handful of rooms above the pubs. Booking ahead matters between May and September and not at all otherwise. There is no accommodation of any kind within four miles of the town in either direction.
```

**Chunk 5** — source: `guide_pellew_sands.md#6` — produced by: `chunker.py::split_documents`

```
# Pellew Sands

## Practical notes

Cash is still useful at the market and in smaller places, though cards are
accepted almost everywhere now. Mobile coverage is good in the centre and
patchy on the outskirts. The nearest full hospital is in Brightwater; there is
a minor injuries unit locally with limited hours.
```

## Sample Answer

**Question:** Which bay is built on three levels?

**Answer:**

```
Halden Bay is built on three levels (Source: `guide_halden_bay.md` and `guide_accessibility.md`).

Sources retrieved: guide_accessibility.md, guide_eating.md, guide_halden_bay.md
```

**My relevance cutoff:** 0.65

To determine the cutoff, I evaluated all in scope and out of scope questions, logging the best distance for each.

The in scope questions had a best distance range of 0.2464 to 0.5314 with a mean of 0.3683. The out of scope questions had a best distance range of .8350 to 0.9968 with a mean of 0.8836. The gap between these two groups is 0.3036. For the in scope questions, queries with distinct names matched tightly while broader queries scored higher due to terms appearing in multiple documents.

I set the threshold at 0.65 to provide a buffer against the chunking strategy I used, which resulted in smaller, more focused chunks that won't always include the context of the entire document. Since each chunk targets a narrow topic, questions phrased indirectly or with only some keywords tend to score higher, so the buffer is used to avoid losing relevant chunks.

| Question                                                                       | In corpus? | Best distance |
| ------------------------------------------------------------------------------ | ---------- | ------------- |
| Which bay is built on three levels?                                            | Yes        | 0.3424        |
| In which season do riverside businesses in Brightwater close?                  | Yes        | 0.2464        |
| Which two types of food can be found on Pellew Sands's seafront?               | Yes        | 0.2626        |
| Which town requires booking ahead in the summer, due to lack of accommodation? | Yes        | 0.5314        |
| How long is the canal walk from Northgate to the old lock?                     | Yes        | 0.4585        |
| What is the capital of Mongolia?                                               | No         | 0.8463        |
| How do I change the oil in a diesel engine?                                    | No         | 0.9032        |
| Who won the 1994 World Cup?                                                    | No         | 0.9968        |
| What is the recommended dosage of ibuprofen for a headache?                    | No         | 0.8350        |
| How do I write a for loop in Rust?                                             | No         | 0.8365        |

## How I Used AI

**1.** I used Gemini to analyze the structure of the documents and confirm my suspicion that a header based chunking strategy would be more effective than a character window based strategy. This included measuring the average sizes of document sections and providing examples of an ideal chunk size and their tradeoffs against the existing strategy. Based on this analysis, I provided instructions to produce a new chunking function that split documents along `##` headers.

The first iteration focused solely on `##` headers, which left small introduction sections as separate chunks, causing a violation of the min tokens per chunk constraint. I had the model suggest improvements and it suggested merging the introduction sections with the first section of the document and prepending the title to each chunk.

I investigated how merging the introduction section with the first section would impact retrieval and found that it did not significantly impact retrieval results, while keeping chunks within the constraints of Criterion 4 and avoiding messy conditional rules for standalone introduction chunks. I also noticed that the titles of each document provided more relevant context than the filenames and that embedding the document title in each chunk improved retrieval.

**2.** I used Gemini to run all in scope and out of scope questions, log the best distance for each, analyze the gap between the results, outline the tradeoffs of moving the cutoff higher or lower, with examples of how moving the cutoff would impact results.

The model provided a structured set of tables and detailed calculations that made it easy to understand the impact of the cutoff and make an informed decision along with the python script it used to generate the results, which allowed me to verify its output.

I combined these insights with an understanding of the tradeoffs from the new chunking strategy I implemented to make a final decision on the cutoff.

---

# Unit 2

## Run Log — Before

| Criterion                                                                                             | Target | Run 1  | Run 2  | Run 3  | Verdict |
| ----------------------------------------------------------------------------------------------------- | ------ | ------ | ------ | ------ | ------- |
| 1. Retrieved chunk contains the answer                                                                | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 2. Every answer names a source                                                                        | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 3. Gate stops out-of-corpus questions                                                                 | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 4. No chunk is shorter than 150 characters, and every chunk contains at least two complete sentences. | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 5. The primary file cited in the answer is the same file where the answer is found.                   | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | MET     |

### Real Output

**Criterion 1: Retrieved chunk contains the answer**
Produced by `run_eval.py::main` via `store.py::search` and `chunker.py::split_documents`:

```
Halden Bay is built on three levels (from guide_halden_bay.md).
```

**Criterion 2: Every answer names a source**
Produced by `run_eval.py::main`, `store.py::search`, and `chunker.py::split_documents`:

```
Several riverside businesses in Brightwater close entirely from January to March, which falls during the winter season (guide_seasons.md and guide_brightwater.md).
```

**Criterion 3: Gate stops out-of-corpus questions**

Produced by `run_eval.py::check_out_of_scope`, cutoff 0.65. Refused 5 of 5.

```
What is the capital of Mongolia? — Best distance 0.887 — refused
How do I change the oil in a diesel engine? — Best distance 0.897 — refused
Who won the 1994 World Cup? — Best distance 0.903 — refused
What is the recommended dosage of ibuprofen for a headache? — Best distance 0.829 — refused
How do I write a for loop in Rust? — Best distance 0.853 — refused
```

**Criterion 4: No chunk shorter than 150 characters, every chunk has 2+ complete sentences**

Produced by `tools/check_criterion4.py` using `chunker.py::split_documents`:

```
Total chunks: 84

Chunks shorter than 150 chars: 0

Chunks with fewer than 2 sentences: 0
```

**Criterion 5: Primary file cited matches the file where the answer is found**

Produced by `run_eval.py::main` via `store.py::search` and `chunker.py::split_documents`,

Answer contained in `guide_kestrelford.md`:

```
According to `guide_kestrelford.md`, booking ahead matters between May and September because there is no accommodation of any kind within four miles of the town in either direction.
```

## Verdicts

| #   | Criterion                                                                                                                                                                           | Verdict | How I decided                                                                                                                               |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | For at least 4 of my 5 test questions, the retrieved chunks include one that contains the answer.                                                                                   | MET     | Inspected chunks using python app.py retrieve for each question across all 3 runs to verify expected answer was present in the top 5 chunks |
| 2   | Every answer the system produces names at least one source document.                                                                                                                | MET     | Inspected each answer across all 5 questions and verified that each answer named a source document.                                         |
| 3   | When I ask a question my documents clearly don't cover, the relevance gate stops it and the system returns "I don't have enough information about that" — in at least 4 of 5 tries. | MET     | Ran all 5 out of scope questions with run_eval.py. All 5 scored between 0.829 and 0.903, which is above the 0.65 cutoff threshold.          |
| 4   | No chunk is shorter than 150 characters, and every chunk contains at least two complete sentences.                                                                                  | MET     | Checked length and sentence count of all 84 chunks using tools/check_criterion4.py; 0 chunks failed either criterion.                       |
| 5   | For at least 4 of my 5 test questions, the primary file cited in the answer is the same file where the answer is found.                                                             | MET     | Inspected answers from all 5 questions across 3 runs to confirm that the primary cited file matched the file where the answer was found.    |

## Diagnoses

### Scoring Miss: Question 3

- **Issue:** During the evaluation runs, Question 3 (Which two types of food can be found on Pellew Sands's seafront?) was flagged as fail across all 3 runs in the `run_eval.py` table, even though the source documents and answers were correct.
- **Diagnosis:** This was a specification and scoring error rather than a retrieval failure.
  1. In `questions.py`, the expected string was misconfigured as `"Fish and chips"`, whereas the reference document `guide_pellewsands.md` states: `"chips and ice cream"`.
  2. The judge function in `scorer.py` checks if the expected string appears in the answer at least once. Because this question asks for _two_ distinct types of food, the original configuration will always fail.

## The Improvement

**What I changed:**

1. Updated `questions.py` to the corrected answer for Question 3 as `["chips", "ice cream"]` rather than `"Fish and chips"`.
1. Updated `scorer.py` to support checking if all comma separated strings appear in the generated answer.

**Why I picked it:**

I picked this fix because question 3 failed evaluation across all 3 runs, which gives a false impression of retriaval failure, when in reality retrieval worked as expected. The fix was minimal and allows for more complex question requirements moving forward.

### Run Log — After

| Criterion                                                                                             | Target | Run 1  | Run 2  | Run 3  | Verdict |
| ----------------------------------------------------------------------------------------------------- | ------ | ------ | ------ | ------ | ------- |
| 1. Retrieved chunk contains the answer                                                                | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 2. Every answer names a source                                                                        | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 3. Gate stops out-of-corpus questions                                                                 | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 4. No chunk is shorter than 150 characters, and every chunk contains at least two complete sentences. | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |
| 5. The primary file cited in the answer is the same file where the answer is found.                   | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET     |

**Did it help?**

After the fixes, question 3 passes on all 3 runs and criterion 5 achieves 5/5 on all 3 runs.

## What's Still Broken

All five criteria are met across each run. Nothing in the current evaluation suite remains broken.

If I had more time, I would address the workaround in the chunking strategy for orphaned introduction chunks. Currently, intro paragraphs are merged into the first ## section to satisfy the minimum chunk length requirement of Criterion 4. This sometimes inflates the first chunk and bundles overview details with unrelated content.

## What I'd Do Differently

I would rewrite Criterion 5 to test the changes made to scorer.py. Instead of only verifying that the answer was found in a single file, I would craft questions that require synthesizing multiple chunks across several relevant files. This would verify that the scorer checks for expected values across multiple documents.
