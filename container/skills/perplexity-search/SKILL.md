---
name: perplexity-search
description: Search the web using Perplexity AI. Use this for ALL web searches — current events, facts, how-tos, research. Returns AI-synthesized answers with cited sources. Only fall back to WebSearch or WebFetch if this tool fails or returns an error.
allowed-tools: Bash(perplexity-search:*)
---

# Perplexity Search

Search the web using Perplexity AI's sonar models. Provides up-to-date, synthesized answers with source citations.

Requires `PERPLEXITY_API_KEY` in the group's `.env` file (or `groups/global/.env` for all groups).

## Usage

```bash
perplexity-search.sh "your search query"
perplexity-search.sh "query" --model sonar            # faster, cheaper
perplexity-search.sh "query" --model sonar-pro        # best quality (default)
perplexity-search.sh "query" --model sonar-reasoning  # chain-of-thought, complex research
```

## Models

| Model | Quality | Speed |
|-------|---------|-------|
| `sonar-pro` (default) | Best | Medium |
| `sonar` | Good | Fast |
| `sonar-reasoning` | Best + reasoning trace | Slow |

## Output

Returns a synthesized answer followed by numbered source citations:

```
<answer text>

Sources:
[1] https://example.com/article
[2] https://another.com/page
```

## Notes

- Use this for all web lookups: news, facts, prices, documentation, reviews
- Fall back to WebSearch/WebFetch only if this skill is unavailable or exits with error
- Citations are real URLs from the answer; include them in your reply when relevant
