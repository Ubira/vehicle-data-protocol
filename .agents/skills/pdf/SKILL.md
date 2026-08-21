---
name: pdf
description: Extract text from PDF files for analysis. Use when the user wants to read, search, or analyze PDF documents (specifications, standards, datasheets, regulations).
argument-hint: "<path-to-pdf>"
allowed-tools: Bash, Read, Grep
---

# PDF Text Extraction

`pdftotext` (from poppler-utils) is installed at `/usr/bin/pdftotext`.

## Usage

```bash
# Convert entire PDF to text
pdftotext input.pdf /tmp/output.txt

# Convert specific pages (first page = 1)
pdftotext -f 5 -l 10 input.pdf /tmp/output.txt

# Preserve layout (useful for tables)
pdftotext -layout input.pdf /tmp/output.txt

# Extract to stdout (pipe to grep, etc.)
pdftotext input.pdf - | grep -i "search term"
```

## Workflow

1. Convert the PDF to text: `pdftotext <pdf> /tmp/<name>.txt`
2. Check line count: `wc -l /tmp/<name>.txt`
3. Search for relevant sections: use `Grep` tool on the text file
4. Read specific sections: use `Read` tool with offset/limit

## Notes

- PDFs fetched via `WebFetch` are saved to the project's tool-results directory
- Scanned/image PDFs won't produce text — `pdftotext` only works with text-based PDFs
- For large regulation documents, search with `grep -n` first to find relevant line numbers, then read targeted sections