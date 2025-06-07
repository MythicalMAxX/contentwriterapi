# 🚀 Deployment Guide - Content Writer AI API

## Vercel Deployment

### Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI**: Install globally
   ```bash
   npm install -g vercel
   ```
3. **Environment Variables Ready**: OpenRouter API key, database URL, etc.

### Step-by-Step Deployment

#### 1. Prepare Your Project

```bash
# Install dependencies
pip install -r requirements.txt

# Test locally first
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 2. Configure Environment Variables

In your Vercel dashboard or via CLI, set these environment variables:

```bash
# Essential Variables
OPENROUTER_API_KEY=your_openrouter_api_key_here
DATABASE_URL=postgresql://username:password@host:port/database

# Rate Limiting (Optional - Redis)
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Application Settings
ENVIRONMENT=production
DEBUG=false
```

#### 3. Deploy to Vercel

```bash
# Login to Vercel
vercel login

# Deploy
vercel --prod
```

#### 4. Alternative: GitHub Integration

1. Push your code to GitHub
2. Connect your GitHub repo to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy automatically on push

### Rate Limiting Configuration

#### Local Development (In-Memory)
- No Redis required
- Rate limits stored in application memory
- Resets on server restart

#### Production (Redis-backed)
- **Recommended**: Use Redis for persistent rate limiting
- **Options**:
  - **Vercel KV**: Built-in Redis by Vercel
  - **Upstash**: Serverless Redis
  - **Railway**: PostgreSQL + Redis combo
  - **Render**: Redis instances

#### Vercel KV Setup (Recommended)

1. Go to your Vercel dashboard
2. Navigate to Storage → KV
3. Create a new KV database
4. Copy the connection details
5. Update environment variables:

```bash
# Vercel KV Configuration
REDIS_HOST=your-kv-endpoint.kv.vercel-storage.com
REDIS_PORT=6379
REDIS_PASSWORD=your_kv_token
```

### Rate Limits Configuration

Current rate limits per endpoint:

```
📊 Rate Limits:
├── Root (/)                 : 10 requests/minute
├── Models (/models)         : 60 requests/minute  
├── Generate Article         : 20 requests/minute
├── Validate Content         : 15 requests/minute
├── Calculate Cost           : 30 requests/minute
└── User Usage              : 60 requests/minute

Global Limits: 1000/hour, 100/minute
```

### Database Setup

#### Option 1: Neon (Recommended)
```bash
# Free PostgreSQL with generous limits
# Sign up at neon.tech
DATABASE_URL=postgresql://username:password@ep-xxx.neon.tech/neondb
```

#### Option 2: Railway
```bash
# PostgreSQL + Redis combo available
DATABASE_URL=postgresql://postgres:password@containers.railway.app:port/railway
```

#### Option 3: Supabase
```bash
# PostgreSQL with additional features
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
```

### Testing Your Deployment

#### 1. Test Rate Limiting

```bash
# Install test dependencies
pip install aiohttp

# Run rate limiting tests
python test_rate_limiting.py
```

#### 2. Manual Testing

```bash
# Test endpoints
curl https://your-app.vercel.app/
curl https://your-app.vercel.app/models

# Load test (should trigger rate limiting)
for i in {1..15}; do curl https://your-app.vercel.app/ & done; wait
```

### Monitoring & Debugging

#### Vercel Logs
```bash
# View real-time logs
vercel logs your-app-url --follow

# View function logs
vercel logs your-app-url --since=1h
```

#### Rate Limiting Metrics

The API returns rate limiting headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642694400
```

### Troubleshooting

#### Common Issues

1. **Cold Starts**: First request may be slow (~3-5s)
   - Solution: Implement warming function or use Vercel Pro

2. **Database Connection Timeouts**
   - Solution: Use connection pooling, increase timeout
   - Check: `maxDuration: 30` in vercel.json

3. **Rate Limiting Not Working**
   - Check Redis connection
   - Verify environment variables
   - Monitor logs for Redis errors

4. **Memory Issues**
   - Default: 1024MB limit on Vercel
   - Solution: Optimize dependencies, use streaming

#### Debug Commands

```bash
# Check environment
vercel env ls

# Test specific function
vercel dev

# View deployment logs
vercel logs --follow
```

### Performance Optimization

#### 1. Dependencies
```bash
# Use lighter dependencies where possible
# Consider: httpx vs requests, asyncpg vs psycopg2
```

#### 2. Cold Start Optimization
```python
# app/main.py - Add global connection pooling
from sqlalchemy.pool import StaticPool

engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,
    pool_recycle=300,
)
```

#### 3. Response Caching
```python
# Add caching for models endpoint
from functools import lru_cache

@lru_cache(maxsize=1)
async def get_cached_models():
    # Cache model list for 5 minutes
    pass
```

### Security Considerations

#### 1. Rate Limiting Strategy
- **IP-based**: Current implementation
- **User-based**: Consider authenticated rate limiting
- **Endpoint-specific**: Different limits per endpoint type

#### 2. Environment Variables
- Never commit API keys
- Use Vercel's secure environment variable storage
- Rotate keys periodically

#### 3. CORS Configuration
```python
# Production CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Cost Optimization

#### Vercel Pricing Considerations
- **Free Tier**: 100GB bandwidth, 100GB-hours compute
- **Pro Tier**: Faster cold starts, more compute time
- **Enterprise**: Custom limits

#### Database Costs
- **Neon**: Free tier with 3GB storage
- **Railway**: $5/month for PostgreSQL
- **Supabase**: Free tier with 500MB

#### Redis Costs
- **Vercel KV**: Pay per request
- **Upstash**: Free tier with 10K requests/day
- **Railway**: Redis addon ~$2/month

### Next Steps

1. **Authentication**: Add JWT-based auth for user tracking
2. **Analytics**: Implement usage analytics and billing
3. **Caching**: Add Redis-based response caching
4. **Monitoring**: Set up alerts for rate limit breaches
5. **Scaling**: Consider edge functions for global deployment

---

## 🧪 Testing Checklist

- [ ] Local development server starts
- [ ] Rate limiting works locally
- [ ] Environment variables configured
- [ ] Database connection successful
- [ ] Vercel deployment successful
- [ ] Rate limiting works in production
- [ ] All endpoints respond correctly
- [ ] Error handling works properly

## 📞 Support

If you encounter issues:
1. Check Vercel logs: `vercel logs --follow`
2. Test locally first: `uvicorn app.main:app --reload`
3. Verify environment variables
4. Check database connectivity

PAPA, ab aapka API production-ready hai! 🎉 