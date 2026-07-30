# Personal Assistant

A personal assistant that ingests the owner's notes — including photographed handwritten journal pages — organizes them, and maintains a living wiki about the owner. Later releases add email/calendar awareness and proactive briefings.

## Language

**Vault**:
The dedicated Obsidian vault, outside this repo, where all notes and the Wiki live as Markdown. The application's read/write target.
_Avoid_: database, store, repo

**Note**:
A captured piece of the owner's thinking after ingestion — transcribed, organized Markdown in the Vault.
_Avoid_: document, entry, record

**Wiki**:
The living, agent-maintained set of Vault pages describing the owner — preferences, projects, people, current situation — kept current as Notes arrive.
_Avoid_: profile, knowledge base, memory

**Capture**:
The act of getting raw input from the owner's world to the pipeline — e.g. photographing a journal page.
_Avoid_: upload, import

**Ingestion**:
The pipeline run that turns captured input into Notes and Wiki updates: transcribe, organize, file into the Vault.
_Avoid_: processing, sync
