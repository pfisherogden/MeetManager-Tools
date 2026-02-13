---
name: skill-creator
description: Guide for creating effective skills for the MeetManager-Tools project. This skill should be used when adding new specialized knowledge, workflows, or tool integrations to the .gemini/skills directory.
---

# Skill Creator

This skill provides guidance for creating effective skills within the `MeetManager-Tools` repository.

## About Skills

Skills are modular, self-contained packages that extend Gemini CLI's capabilities by providing specialized knowledge, workflows, and tools. They transform Gemini CLI into a specialized agent equipped with procedural knowledge of our specific codebase, gRPC contracts, and MDB-to-JSON data flows.

### What Skills Provide

1. **Specialized workflows**: Multi-step procedures (e.g., gRPC codegen, Docker deployment).
2. **Tool integrations**: Instructions for working with `justfile`, `uv`, `clasp`, and `npm`.
3. **Domain expertise**: Knowledge of MeetManager schemas, report verification, and architecture.
4. **Bundled resources**: Reference files and scripts for repetitive tasks.

## Core Principles

### Concise is Key

The context window is a public good. Skills share the context window with the system prompt, conversation history, and user requests.

**Default assumption: Gemini CLI is already very smart.** Only add context specific to our project that isn't publicly known. Challenge each piece: "Does Gemini CLI really need this explanation?" and "Does this paragraph justify its token cost?"

### Anatomy of a Skill in this Project

Skills live in `.gemini/skills/`. Every skill consists of a required `SKILL.md` file and optional bundled resources:

```
.gemini/skills/skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── references/ (optional) - Documentation to be loaded into context as needed
```

#### SKILL.md (required)

- **Frontmatter** (YAML): Contains `name` and `description`. These are read to determine when the skill triggers. Be clear and comprehensive.
- **Body** (Markdown): Instructions and guidance. Only loaded AFTER the skill triggers.

## Progressive Disclosure

Keep `SKILL.md` lean. If a skill supports multiple complex sub-domains (e.g., `Architecture` covering both Frontend and Backend), move specific details into `references/`.

### Pattern: High-level guide with references

```markdown
# Backend Development

## Core Logic
See [LOGIC.md](references/LOGIC.md) for data parsing details.

## gRPC Services
See [GRPC.md](references/GRPC.md) for service implementation patterns.
```

## Skill Creation Process

1. **Identify the Need**: Is there a recurring complex task or domain knowledge? (e.g., "Updating gRPC Protos").
2. **Understand with Examples**: Walk through the task once to see what context is needed.
3. **Draft SKILL.md**: Use the YAML frontmatter and clear, imperative instructions.
4. **Iterate**: Use the skill on real tasks and refine the instructions.

## Writing Guidelines

- **Use Imperative Form**: "Run `just codegen`" instead of "You should run codegen".
- **Focus on 'Why' and 'How'**: Explain the project-specific reasoning or unique steps.
- **Avoid Clutter**: Do not include READMEs or other auxiliary files in the skill directory.
