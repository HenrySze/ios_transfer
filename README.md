# iMessage Archive

A personal tool to extract iMessage history off an iPhone (via a local backup)
onto this Mac, so old conversations can be archived and cleared off the phone
to free up storage.

Two-stage pipeline:

1. **Extract** — read a local iPhone backup and produce a raw, "as original as
   possible" JSON archive (plus copied-out attachments). This is the source
   of truth and is never modified by later stages.
2. **Render** — turn the raw JSON archive into a browsable, iMessage-styled
   HTML view. Can be re-run anytime to change the look without touching the
   phone or the backup again.

## Project structure

```
imessage_archive/
  __init__.py
  backup.py        # locate the local backup, read Manifest.db, pull out chat.db + attachment files
  models.py         # shared dataclasses: Message, Chat, Handle, Attachment (the schema raw JSON follows)
  extract.py        # chat.db -> raw/ (one JSON per conversation + attachments copied out)
  render_html.py     # raw/ JSON -> iMessage-styled HTML
  cli.py             # `extract`, `render`, `all` subcommands
```

### Raw JSON schema (one file per conversation, `raw/chats/<chat_id>.json`)

- chat: `id`, `display_name`, `participants`, `is_group`
- messages: `guid`, `date` (ISO 8601), `sender` (`"me"` or handle), `text`,
  `service` (iMessage/SMS), `attachments` (copied filenames + original mime
  type), with room to add `reactions` / `reply_to` later without breaking
  the schema

## Workflow

1. Create a local, unencrypted backup of the iPhone via Finder (copy the
   resulting backup folder anywhere convenient, e.g. the Desktop).
2. Run extract, one contact at a time:
   `python -m imessage_archive extract <path to backup folder> --contact <name or handle>`
   → produces `raw/chats/<chat_id>.json` + copied attachments for just that
   conversation. Re-run per contact as needed; the backup folder is never
   modified and can be reused for multiple contacts.
3. (Optional, repeatable, no backup needed) Render any raw JSON to HTML:
   `python -m imessage_archive render raw/chats/<chat_id>.json`

## Status

Planning stage — starting with `backup.py` (locating the backup and reading
`Manifest.db` to find `chat.db`).
