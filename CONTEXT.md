# Personal Assistant

A personal assistant that ingests the owner's notes — including photographed handwritten journal pages — organizes them, and maintains a living wiki about the owner. Later releases add email/calendar awareness and proactive briefings.

## Language

**Vault**:
The dedicated Obsidian vault, outside this repo, where all notes and the Wiki live as Markdown. The application's read/write target.
_Avoid_: database, store, repo

**Note**:
One Capture, faithfully transcribed into dated Markdown in the Vault — the owner's words, not a summary of them. Written once by Ingestion and never rewritten by the agent afterward; the owner may edit it freely in Obsidian. Notes are the record the Wiki is derived from, never the reverse.
_Avoid_: document, entry, record

**Wiki**:
The living, agent-maintained set of Vault pages describing the owner — one page per Entity, plus the `Me.md` singleton. Derived from Notes and freely rewritten as they arrive; a page states what is true now, and can be regenerated from the Notes if it goes wrong.
_Avoid_: profile, knowledge base, memory

**Entity**:
Something in the owner's life that the Wiki tracks as a subject of its own — a Person, a Project, or a Topic. Each Entity has exactly one Wiki page.
_Avoid_: subject, item, node, object

**Capture**:
The act of getting raw input from the owner's world to the pipeline — e.g. photographing a journal page.
_Avoid_: upload, import

**Ingestion**:
The pipeline run that turns captured input into Notes and Wiki updates: transcribe, organize, file into the Vault.
_Avoid_: processing, sync
