# Japanese Driver's License Practice Test

Browser-based flashcard study app for the Japanese driver's license exam (English translation). 880 True/False questions with images, explanations, and spaced repetition.

## Features

- **880 flashcards** covering Learner's Permit (250), Driver's License (540), and Danger Anticipation (90) questions
- **Spaced repetition** -- wrong answers are re-presented with highest priority; mastery requires 2 correct in a row
- **Progress tracking** saved in your browser (localStorage) across sessions
- **Filter by category** -- study all questions or focus on LP, DL, or Danger
- **Reference material** with traffic signs, rules, and diagrams
- **Statistics** showing mastered/wrong/unseen counts per category
- **Mobile-first** -- designed for studying on your phone

## Usage

Visit the [GitHub Pages site](https://irawinder.github.io/drivers-license-practice-test/) or run locally:

```bash
cd docs
python3 -m http.server 8000
# Open http://localhost:8000
```

## Rebuilding site data

If the source exam data in `extracted/` changes, regenerate the site data:

```bash
python3 build_site_data.py
```

This reads the 11 exam JSONs from `extracted/`, flattens them into `docs/data/questions.json`, copies reference material to `docs/data/reference.json`, and copies 202 question images to `docs/images/`.

## Data source

Questions extracted from a 41-page PDF of Japanese driver's license practice tests (English translation), containing 5 Learner's Permit exams (50 questions each) and 6 Driver's License exams (90 standard + 5 danger anticipation questions each).
