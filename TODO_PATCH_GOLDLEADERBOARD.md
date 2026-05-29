# TODO: Rename `/coinleaderboard` to `/goldleaderboard`

During Patch 68 Batch 1 uploads, generated docs still showed `/coinleaderboard` in:

- `COMMAND_FILE_MAP.md`
- `COMMAND_REFERENCE.md`
- `PLAYER_COMMAND_QUICKSTART.md`

After batch uploads finish, audit the source and generated docs so the command name becomes `/goldleaderboard` consistently.

Checklist:

- Update the slash command decorator in `clash_mmo/commands/wallet_commands.py` if needed.
- Update generated command docs.
- Update player quickstart docs.
- Verify command registration.
- Verify duplicate command names.
