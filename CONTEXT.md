# Personal Assistant

A personal assistant that ingests the owner's notes — including photographed handwritten journal pages — organizes them, and maintains a living wiki about the owner. Later releases add email/calendar awareness and proactive briefings.

## Language

**Vault**:
The dedicated Obsidian vault, outside this repo, where all notes and the Wiki live as Markdown. The application's read/write target.
_Avoid_: database, store, repo

**Note**:
One day of the owner's journal, faithfully transcribed into dated Markdown in the Vault — the owner's words, not a summary of them. Delimited by the writer's own top-level date heading, not by the Capture that carried it: one Capture may yield several Notes, or only extend an existing one. Append-only for the agent — Ingestion may add to the end of a Note as later Captures arrive, but never revises what is already written; the owner may edit it freely in Obsidian. Notes are the record the Wiki is derived from, never the reverse.
_Avoid_: document, entry, record

**Wiki**:
The living, agent-maintained set of Vault pages describing the owner — one page per Entity, plus the `Me.md` singleton. Derived from Notes and freely rewritten as they arrive; a page states what is true now, and can be regenerated from the Notes if it goes wrong.
_Avoid_: profile, knowledge base, memory

**Entity**:
Something in the owner's life that the Wiki tracks as a subject of its own — a Person, a Project, or a Topic. Each Entity has exactly one Wiki page.
_Avoid_: subject, item, node, object

**Capture**:
One ordered batch of raw input handed to a single Ingestion run — e.g. the journal pages photographed in one sitting. Ordered because the journal is continuous: consecutive pages overlap and a sentence may span the seam between them, so a Capture is read as one stream rather than as independent pieces.
_Avoid_: upload, import, photo

**Ingestion**:
The pipeline run that turns captured input into Notes and Wiki updates: transcribe, organize, file into the Vault.
_Avoid_: processing, sync
