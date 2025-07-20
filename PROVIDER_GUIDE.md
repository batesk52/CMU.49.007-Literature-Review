# Multi-Provider API Guide

This guide shows how to use the knowledge base system with different AI providers: OpenAI, Google Gemini, and Claude.

## Provider Comparison

| Provider | Embeddings Quality | Context Window | Cost | Notes |
|----------|-------------------|----------------|------|-------|
| OpenAI | Excellent (dedicated models) | 8k-128k tokens | $$ | Best for embeddings, mature API |
| Gemini | Good (dedicated models) | 32k-1M tokens | $ | Good balance, generous free tier |
| Claude | Limited (workaround) | 100k-200k tokens | $$ | Best for text generation, no native embeddings |

## Setup

The system now includes centralized configuration management. You can validate your setup:

```bash
# Check which providers are available
python config.py validate

# Show current configuration
python config.py show
```

### 1. OpenAI
```bash
# In .env file:
OPENAI_API_KEY=sk-...your-key-here...
```
- Get API key from: https://platform.openai.com/api-keys
- Uses `text-embedding-3-small` for embeddings
- Uses `gpt-4` for text generation

### 2. Google Gemini
```bash
# In .env file:
GEMINI_API_KEY=...your-key-here...
```
- Get API key from: https://makersuite.google.com/app/apikey
- Uses `embedding-001` model for embeddings
- Uses `gemini-pro` for text generation
- Free tier available (60 requests/minute)

### 3. Claude (Anthropic)
```bash
# In .env file:
CLAUDE_API_KEY=...your-key-here...
# or
ANTHROPIC_API_KEY=...your-key-here...
```
- Get API key from: https://console.anthropic.com/
- Uses Claude 3 Sonnet for text generation
- **Note**: Claude doesn't provide native embeddings API. The system uses a workaround that generates semantic concepts and converts them to vectors. This is less accurate than dedicated embedding models.

## Using the V2 Modules

### Summarization with Different Providers

```bash
# Auto-detect provider based on available API keys
python markdown_summarizer_v2.py file1.md file2.md

# Explicitly use Gemini
python markdown_summarizer_v2.py --provider gemini file1.md

# Explicitly use Claude
python markdown_summarizer_v2.py --provider claude file1.md

# Explicitly use OpenAI
python markdown_summarizer_v2.py --provider openai file1.md
```

### Semantic Search with Different Providers

```bash
# Build embeddings with Gemini
python semantic_search_v2.py --provider gemini build

# Search with Claude (not recommended due to embedding limitations)
python semantic_search_v2.py --provider claude search "your query"

# View statistics
python semantic_search_v2.py stats
```

### Complete Workflow Example

```bash
# 1. Set up environment (choose one)
echo "GEMINI_API_KEY=your-gemini-key" > .env
# or
echo "OPENAI_API_KEY=your-openai-key" > .env
# or
echo "CLAUDE_API_KEY=your-claude-key" > .env

# 2. Build knowledge base with your chosen provider
python knowledge_base_builder.py build

# 3. Build embeddings (if using OpenAI or Gemini)
python knowledge_base_builder.py build-embeddings

# 4. Search your knowledge base
python knowledge_base_builder.py search "configuration"
python knowledge_base_builder.py semantic-search "how to set up development"
```

## Migration Between Providers

The system caches embeddings with provider information, so you can:

1. **Switch providers without losing data**: The cache keeps embeddings from all providers
2. **Compare results**: Try the same search with different providers
3. **Gradual migration**: Build new embeddings with a new provider while keeping old ones

```bash
# Example: Migrate from OpenAI to Gemini
# 1. Your cache already has OpenAI embeddings
# 2. Add Gemini API key to .env
# 3. Force rebuild with new provider
python semantic_search_v2.py --provider gemini build --force
```

## Cost Optimization Tips

1. **Use Gemini for development**: Free tier is generous
2. **Use OpenAI for production embeddings**: Best quality
3. **Use Claude for complex Q&A**: Best reasoning, but avoid for embeddings
4. **Cache everything**: The system automatically caches to minimize API calls

## Programmatic Usage

```python
from api_providers import APIProviderFactory
from markdown_summarizer_v2 import MarkdownSummarizerV2
from semantic_search_v2 import SemanticSearchV2

# Auto-detect provider
provider = APIProviderFactory.create_provider()

# Or specify provider
provider = APIProviderFactory.create_provider("gemini")

# Use with summarizer
summarizer = MarkdownSummarizerV2("gemini")
summary = summarizer.summarize_content("Your markdown content here")

# Use with semantic search
search = SemanticSearchV2(provider_name="gemini")
results = search.semantic_search("your query", knowledge_db)
```

## Limitations by Provider

### OpenAI
- Rate limits apply (varies by tier)
- Costs can add up for large documents
- Excellent for all use cases

### Gemini
- Free tier: 60 requests/minute
- Embedding dimensions may differ from OpenAI
- Good for most use cases

### Claude
- No native embeddings API (uses workaround)
- More expensive for high-volume use
- Best for complex reasoning tasks, not recommended for semantic search

## Troubleshooting

1. **"No API keys found"**: Make sure your `.env` file is in the project root
2. **Rate limit errors**: Add delays or upgrade your API tier
3. **Different results between providers**: This is normal - each uses different models
4. **Claude embeddings not working well**: This is expected - use OpenAI or Gemini for embeddings

## Recommendations

- **For semantic search**: Use OpenAI or Gemini
- **For summarization**: Any provider works well
- **For Q&A**: Claude excels at complex reasoning
- **For cost-effectiveness**: Gemini with free tier
- **For production**: OpenAI for consistency and quality