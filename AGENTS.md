# Repository Instructions

## Source-grounded document work

When reading, transcribing, or summarizing a source document in this repository, the source is authoritative. Do not add interpretations, research agendas, explanations, conclusions, or outside context unless the user explicitly asks for them.

If the user asks for the original text or a factual summary:

1. Preserve the source's wording, order, names, numerical values, units, qualifications, and uncertainty.
2. Preserve meaningful structure such as bullet hierarchy, headings, and bold emphasis.
3. Do not silently repair incomplete phrases or awkward wording. Keep them as written.
4. Clearly distinguish verbatim transcription from summary. Do not label a paraphrase as original text.
5. Link the resulting note to its source file when practical.

## Mandatory PDF inspection procedure

Do not infer the contents of a PDF from text extraction or embedded-image extraction alone.

For every relevant page:

1. Check the page count.
2. Attempt text extraction, but treat it only as one inspection method.
3. Render the **entire PDF page** to an image and inspect the full page from top to bottom.
4. If text extraction is empty or incomplete, use the full-page rendering for visual transcription or OCR.
5. Verify the final Markdown against the full-page rendering, including lower-page content and nested bullets.

Important distinctions:

- `page.get_text()` returning no text means only that no extractable text layer was found. It does **not** mean that no text is visibly present in the PDF.
- `page.get_images()` returns embedded raster assets. An extracted image may be only one figure or slide placed on a larger PDF page. It must not be treated as the entire page.
- Before stating that content is absent from a PDF, inspect a full-page rendering and any other relevant page objects. Say "no extractable text layer" when that is the actual finding.

## Known repository-specific PDF pitfall

`docs/research_notes/google_doc/260929_光RG_FB.pdf` is a one-page PDF whose upper portion contains an embedded slide image and whose lower portion contains additional visible feedback text. PyMuPDF text extraction can return zero characters, and extracting the single embedded image captures only the upper slide—not the full page.

For this file, render the complete page (for example, with `page.get_pixmap(...)`) before reading or transcribing it. The complete transcription is stored in:

`docs/research_notes/260929_optcomm_rg_feedback.md`

## Verification before reporting completion

Before saying that document work is complete:

- Re-open the produced Markdown.
- Compare it against the complete rendered source, not just extracted text or individual images.
- Confirm that all requested sections are present.
- Describe extraction limitations precisely and avoid unverified claims.
