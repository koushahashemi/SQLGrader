# SQL Assignment Reviewer (Windows, offline)

Extract this entire ZIP into a folder, then double-click **START.bat**.
Requires Windows 10/11 and Python 3.11 or newer with Tcl/Tk (included in the standard python.org Windows installer). Enable “Add Python to PATH” when installing. No pip packages, API key, AI account, SQL Server installation, or GitHub repository are needed. Installing Python may require a download; the app itself works entirely offline. This is a Python desktop app with a batch launcher, not a standalone .exe.

## Your four assignments

Assignment 5: 10 questions / 20 marks. Assignment 7: 10 / 20. Assignment 8: 5 / 10. Assignment 9: 5 / 10. Instructions and model answers are included in `resources/`. All four tabs use the same UI. Source documents are included for reference.

Assignment 9's general instructions request stored procedures, but its questions and key use ordinary SELECT queries. The app follows the questions and key; decide manually whether procedure creation should affect marks. Instructions about executing SQL and screenshots are student requirements from the source documents, not actions this app performs.

## Workflow

1. Choose an assignment tab. Click **Add files** for multiple files or **Load folder**. Supported: .docx, .sql and .txt. Enable Include subfolders if needed. Import only student submissions into the correct tab. Legacy .doc files must first be saved as .docx in Word.
2. Select a file and question. Review the candidate SQL against **Reference solution** and **Assignment instructions**. Double-click a file row to open its original document in the Windows associated application. Explicit question labels such as `Question 1`, `Q1`, `1.` or `-- 1.` help extraction. Automatic Word numbering and unusual layouts may require manual matching.
3. Check **Source text / remap**. Select SQL and click **Assign selected text to question** to correct a match. The source is an immutable text snapshot, including body tables; images, headers, footers, text inside screenshots, tracked-deletion history, and handwritten answers are not graded. Embedded image counts are only an indication, not screenshot verification. Open original document for visual review.
4. Choose a final **0, 1, or 2** and enter feedback. Edits save automatically. **Save & next question** speeds review. Editing a query clears its final mark, because the confirmed content changed.
5. **Export grades** makes an Excel-compatible CSV for the selected assignment. Only instructor-confirmed marks are exported. Unreviewed questions and incomplete totals stay blank. Excel formula characters in names and feedback are escaped.

## What offline checking can and cannot do

No query is ever executed and no submission is sent anywhere. There is no online AI and no local language model. All document processing and checks use Python's standard library. Word files are read as ZIP/XML text; macros and embedded objects are never executed by the app. “Open original document” opens the selected file in its Windows associated application.

Suggested **2** means the extracted text matches the supplied key after ignoring whitespace, comments, bracketed identifiers, identifier case, and trailing statement/batch terminators. String literals retain their exact text. It is still necessary to verify question mapping and the key itself.

Suggested **1** means “different query: needs review.” It is a placeholder, **not a reliable partial-credit judgment**. The app checks for assignment-specific text patterns and shows what it found. It does not prove that SQL compiles or that its joins, predicates, output columns, or aggregates are correct. An incorrect query can contain every expected token; a fully correct alternative can omit them. CTEs, correlated subqueries, alternative functions, and different procedure or parameter names require instructor judgment. Do not copy suggestions blindly.

Suggested **0** means no SQL was extracted. Check the source before assigning zero: question matching may have failed or the answer may be an image. There is no bulk auto-finalize button.

Final rubric: **0 incorrect/missing, 1 partially correct, 2 correct**. Use the question's requirements to judge alternatives; put reasons for partial credit in feedback. The app assists extraction, comparison, navigation, persistence, and reporting. It cannot autonomously grade arbitrary valid alternative SQL without execution or an AI model.

## Saving and backups

The local working database is `%LOCALAPPDATA%\SQLAssignmentReviewer\reviews.sqlite3`. It contains filenames, paths, source text, edited queries, final marks and feedback. Protect this folder as student records. Close the app before copying this database as a backup. Reopening the app restores all four sections. No telemetry, analytics, network clients, or remote storage are included.

Reimporting the same absolute path in the same section skips it to protect reviews; it does not refresh changed originals. To refresh, export/back up existing grades, remove the imported copy, and import it again. Removing an imported file deletes its saved marks and snapshot, but keeps the original Word file. Originals are referenced by path for opening; the source text snapshot remains usable if originals move.

## Updating assignments

`resources/assignments.json` holds prompts and reference SQL. Back it up before editing and restart the app afterwards. Finish/export a grading round before changing question counts or keys; existing review records correspond to the original question numbers. Original assignment documents are provided in `resources/`.

## Troubleshooting and verification

If double-clicking fails, launch START.bat from a Command Prompt to see the error. Tkinter must be installed (use the standard Windows installer rather than the embeddable Python distribution). Error details may be recorded in `%LOCALAPPDATA%\SQLAssignmentReviewer\error.log`.

No OCR is included. Complex Word formatting can confuse extraction. Files over 25 MB or DOCX archives expanding beyond 100 MB are rejected.

Developer tests: `python -m unittest discover -s tests -v`. Nine automated tests plus a desktop GUI smoke test (all four tabs, navigation, score persistence, remapping and reopening) passed in Linux; a native Windows run is still needed to verify your Python installation and Word file associations.
