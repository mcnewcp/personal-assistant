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

**Mention**:
One occurrence of an Entity in a Note, recorded as the surface form the owner actually wrote — `[[Mom]]`, never the resolved name. A Mention asserts nothing about identity; which Entity it refers to is decided in the Wiki and applied at read time, so a Mention cannot be wrong. Ingestion links the handles the owner uses as names, and never invents a name in order to link one.
_Avoid_: reference, occurrence, hit

**Alias**:
A surface form that resolves to an Entity, held in the `aliases:` frontmatter of that Entity's Wiki page. Page titles plus Aliases are the whole identity map — there is no registry beside them. Ingestion adds an Alias when it resolves a Mention to a page; only the owner removes one. An Alias is a global claim on a surface form, so only name-like strings qualify, never common nouns.
_Avoid_: synonym, nickname, alternate name

**Materialize**:
The point at which an Entity earns its own Wiki page — judged on durable substance, never on a count of Mentions. Until then its Mentions accumulate in the Notes as unresolved links, which is also how Ingestion discovers the Entity is worth a page. Materializing builds the page from every Note that mentions the Entity, so it arrives with its history intact rather than starting mid-story.
_Avoid_: create, promote, instantiate

**Regenerate**:
Rebuild a Wiki page from the Notes it derives from, discarding whatever the body said before. The single repair operation: merging two Entities, splitting one, and Materializing a new page are all the same act performed after correcting the identity map. It is why a wrong identity call is never permanent, and why the Wiki is safe to write without review.
_Avoid_: rebuild, refresh, sync

**Capture**:
One ordered batch of raw input handed to a single Ingestion run — e.g. the journal pages photographed in one sitting. Ordered because the journal is continuous: consecutive pages overlap and a sentence may span the seam between them, so a Capture is read as one stream rather than as independent pieces.
_Avoid_: upload, import, photo

**Ingestion**:
The pipeline run that turns captured input into Notes and Wiki updates: transcribe, organize, file into the Vault.
_Avoid_: processing, sync
