# Exam Library

A separate website and repository for school exam papers and marking keys, Years 1–12.

## Add exams

Use one folder per exam:

`resources/Secondary/Physics/Year 12/School name/2026/Semester 1/Paper.pdf`

`resources/Secondary/Physics/Year 12/School name/2026/Semester 1/MarkingKey.pdf`

Use `Primary` for Years 1–6. Subject and school folders can have any name. Exam year is the calendar year, separate from the student's year level. Science template folders for Years 1–12 are included.

Canonical `Paper.pdf` and `MarkingKey.pdf` are paired automatically within the same folder. `Exam.pdf` or `QuestionPaper.pdf`, and `Answers.pdf` or `Solutions.pdf`, are also recognised. Other PDFs are listed individually; give unrelated exams their own folders. Identical paper/key pairs are deduplicated. No marking key is created or claimed when one is absent.

Optional `exam.json` in the folder overrides details:

```json
{"title":"Physics Year 12 Semester 1","subject":"Physics","years":[12],"school":"School name","examYear":2026,"examType":"Semester 1","topic":"Units 3 and 4","description":"Exam paper and marking key"}
```

## Large scans or external links

Keep large files on Drive or another HTTPS host and add a JSON record under `resources/`:

```json
{"title":"Physics Year 12 Semester 1","subject":"Physics","years":[12],"school":"School name","examYear":2026,"examType":"Semester 1","url":"https://YOUR-HOST/paper.pdf","markingKeyUrl":"https://YOUR-HOST/key.pdf"}
```

The marking-key link is optional. `previewUrl` and `markingKeyPreviewUrl` may point to browser-readable PDF URLs; otherwise use the original buttons if a host blocks embedded previews. URLs must use HTTPS without credentials.

## Publishing and features

A push runs the catalogue tests, indexes the files and publishes the separate website with GitHub Actions. PDF previews are generated as copies in the deployed site; source files remain in their folders. Choose **GitHub Actions** in Settings → Pages.

Search; subject, school, year level, exam year, exam type and topic filters; PDF viewer; paired marking-key links; saved exams and recent history on the visitor's device. The catalogue starts empty and contains no demonstration papers. There is no public upload/admin approval backend yet; repository access is required to publish.

Run `python3 scripts/build_catalog.py` and `python3 -m unittest discover -s scripts -p 'test_*.py'` locally.

Only upload papers you have permission to distribute. Keep confidential upcoming exams out of this public repository. No licence over exam content is implied.
