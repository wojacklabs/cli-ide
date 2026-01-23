# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication

- Write all code in English
- Respond in Korean for terminal chat

## Development Rules

### Do NOT

- Create mock-up or fake features that simulate functionality without real implementation
- Attempt to fix issues based only on logs/symptoms without examining the actual code
- Propose unsolicited Plan B that reduces scope or changes direction when stuck
- Declare completion after just writing code - must verify via build/execution
- Partially follow official documentation then improvise the rest - follow official docs completely or ask for guidance
- Leave debug console.log/print statements after fixing issues
- Keep failed approach code "for later" - remove immediately
- Proceed to next task without cleaning up current task's artifacts

### Revert & Cleanup Rules

#### Git Checkpoint
- Before attempting significant changes: `git add -A && git commit -m "checkpoint: before trying X"`
- When approach fails: `git checkout .` or revert to checkpoint commit
- Never leave half-finished failed attempts in the codebase

#### Debug Code Management
- When adding debug logs, use marker comment: `// DEBUG:` or `# DEBUG:`
- After fixing issue, search and remove all debug code: `grep -r "DEBUG:" .`
- Verify no debug statements remain before declaring task complete

#### Failed Approach Handling
- If an approach fails, completely remove all related code before trying next approach
- Do not comment out failed code - delete it entirely
- Use git to recover if needed later, not commented code

### Completion Checklist (verify before declaring any task done)
- [ ] All debug console.log/print removed
- [ ] No remnants of failed approaches
- [ ] No unnecessary comments added
- [ ] Build/test passes
