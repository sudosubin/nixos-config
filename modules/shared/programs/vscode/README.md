# VSCodium

The shared Darwin/Linux module uses `programs.vscodium`, not
`programs.vscode.package`, so Home Manager writes to the correct fork's paths.
`code` is a shell alias for `codium`, declared through Home Manager's standard
`home.shellAliases` option. The VSCodium module has no dedicated alias option.
Cursor CLI is intentionally independent and remains installed in
`modules/darwin/home.nix`.

## UI fonts and settings

VSCodium provides `workbench.experimental.fontFamily`. Together with the editor,
terminal and debug console font settings, this replaces the old Cursor package's
CSS injection and checksum patch. No editor bundle is modified. Markdown preview
uses a separate prose font intentionally.

User settings are immutable and managed by Home Manager. Edit `files/settings.json`
rather than changing settings through the UI. `extensions.autoUpdate` uses the
native `"off"` enum value to avoid a write-back migration from the old boolean
value. The material icon theme is still generated at build time because its
extension would otherwise rewrite files in the Nix store.

Local History keeps up to 1,000 revisions per file, rather than the default 50,
to avoid pruning imported Cursor/Kiro revisions. This is a finite retention limit,
not a permanent archive. Setting it to zero does **not** mean unlimited history.

The old `typescriptteam.native-preview` ID is blocked by VSCodium's extension
safety checks. Do not bypass that protection. Builtin TypeScript remains enabled
(`js/ts.experimental.useTsgo = false`). The `vscode-typescript-nightly` extension
is only a TypeScript 7 SDK, not a replacement language client by itself.

## Offline Local History migration

Run the utility from the repository root:

```sh
python3 -m unittest discover -s scripts/tests -v

# Dry-run by default. Close all editor versions before copying or applying.
python3 scripts/migrate-vscode-history.py \
  --source "$HOME/Library/Application Support/Cursor/User/History" \
  --source "$HOME/Library/Application Support/Kiro/User/History" \
  --destination "$HOME/Library/Application Support/VSCodium/User/History"
```

Take and verify private backups first. On macOS, older VSCodium data might also
be under `~/Support/VSCodium`; check custom user-data directories and profiles.
Do not overwrite an existing destination tree or copy entire `state.vscdb` files.

The utility:

- Unions revision events by exact resource URI, timestamp, content hash and source
  metadata; identical content at different times remains separate.
- Preserves destination events and resolves snapshot ID collisions, including
  case-insensitive filesystems, using native four-character IDs.
- Rejects missing snapshots, unsupported schemas, invalid URI hashes, symlinks,
  overlapping paths and concurrent source changes.
- Recovers unindexed snapshots using their preserved modification times.
- Stages and verifies the complete result before publishing it. An existing
  destination is retained as `History.before-migration-*` for rollback.
- Never deletes or modifies a source tree.

Use `--apply --audit-dir /private/path` to publish after reviewing the dry-run.
The audit contains a complete source-to-destination content-hash manifest and
must be kept private, outside this repository.

For metadata-less buckets, `--resource-map map.json` accepts a mapping of bucket
hashes to original URIs; these must pass the native URI hash check. If the original
path cannot be determined, `--recover-unmapped-to /private/recovered-files`
explicitly preserves the snapshots under clearly named recovery files, without
guessing their original paths. Keep that directory: its file URIs are referenced
by the imported history.

For Cursor user configuration history, a prefix mapping can be supplied:

```sh
--rewrite-uri-prefix 'vscode-userdata:/Users/USER/Library/Application%20Support/Cursor/User/=vscode-userdata:/Users/USER/Library/Application%20Support/VSCodium/User/'
```

Recently opened files, search and terminal histories require a separate,
schema-checked allowlist import. AI chat, credentials and extension state must not
be imported with them. Verify the merged files again after running VSCodium,
before deleting old IDE data or any backups containing AI conversations.

Cursor IDE and CLI share parts of `~/.cursor`, including project transcripts and
AI attribution data. Never delete that directory wholesale while retaining CLI.
Preserve `~/.config/cursor` and `~/.local/share/cursor-agent`; attribute shared
transcripts to IDE or CLI session IDs before selectively removing IDE copies.
