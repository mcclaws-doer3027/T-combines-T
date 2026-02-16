import praw
from groq import Groq
import json
import time
from datetime import datetime

class RedditOAuthAnalyzer:
    def __init__(self, config, reddit_username=None, reddit_password=None):
        """Initialize with detailed logging"""
        
        print("="*60)
        print("🔐 INITIALIZING REDDIT")
        print("="*60)
        
        print(f"Username: {reddit_username}")
        print(f"Password: {'*' * len(reddit_password) if reddit_password else 'None'}")
        
        if reddit_username and reddit_password:
            try:
                self.reddit = praw.Reddit(
                    client_id="ohXpoqrZYub1kg",
                    client_secret="",
                    user_agent=f"python:validator:v1 (by /u/{reddit_username})",
                    username=reddit_username,
                    password=reddit_password,
                    timeout=15
                )
                
                print("Testing authentication...")
                me = self.reddit.user.me()
                print(f"✅ Authenticated as: u/{me}")
                
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                raise
        else:
            print("❌ No credentials provided")
            raise Exception("Reddit credentials missing")
        
        print("\n🤖 INITIALIZING GROQ")
        self.groq_client = Groq(api_key=config['GROQ_API_KEY'])
        print("✅ Groq initialized\n")
    
    def scrape_posts(self, category, limit=10):
        """DIAGNOSTIC VERSION - prints everything"""
        
        print("="*60)
        print(f"SCRAPING: {category}")
        print("="*60)
        
        # Simple categories for testing
        categories = {
            'marketing': {
                'subreddits': ['startups'],
                'keywords': ['problem']
            },
            'sales': {
                'subreddits': ['startups'],
                'keywords': ['difficult']
            },
            'productivity': {
                'subreddits': ['startups'],
                'keywords': ['struggling']
            },
            'developer_tools': {
                'subreddits': ['programming'],
                'keywords': ['annoying']
            },
            'general': {
                'subreddits': ['startups'],
                'keywords': ['problem']
            }
        }
        
        config = categories.get(category.lower(), categories['general'])
        posts = []
        
        print(f"Subreddits: {config['subreddits']}")
        print(f"Keywords: {config['keywords']}")
        print(f"Target: {limit} posts\n")
        
        for subreddit_name in config['subreddits']:
            print(f"\n📍 SUBREDDIT: r/{subreddit_name}")
            
            for keyword in config['keywords']:
                print(f"\n  🔍 KEYWORD: '{keyword}'")
                
                try:
                    print(f"  Step 1: Getting subreddit object...")
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    print(f"  Step 2: Searching...")
                    search_results = subreddit.search(
                        keyword,
                        limit=5,  # Very small for testing
                        sort='hot',
                        time_filter='month'
                    )
                    
                    print(f"  Step 3: Converting to list...")
                    results_list = []
                    for i, submission in enumerate(search_results):
                        print(f"    Post {i+1}: {submission.title[:40]}...")
                        results_list.append(submission)
                        if i >= 4:  # Stop at 5
                            break
                    
                    print(f"  ✅ Got {len(results_list)} posts")
                    
                    print(f"  Step 4: Processing posts...")
                    for submission in results_list:
                        print(f"    Processing: {submission.title[:30]}...")
                        
                        # Quick filters
                        if submission.score < 2:
                            print(f"      ⏭️  Skip (low score: {submission.score})")
                            continue
                        
                        if not submission.selftext or len(submission.selftext) < 20:
                            print(f"      ⏭️  Skip (no body)")
                            continue
                        
                        print(f"      ✓ Passed filters (score: {submission.score})")
                        
                        # Get minimal comments
                        print(f"      Getting comments...")
                        try:
                            submission.comments.replace_more(limit=0)
                            comments = []
                            for comment in list(submission.comments)[:3]:
                                if hasattr(comment, 'body'):
                                    comments.append({
                                        'text': comment.body[:100],
                                        'score': getattr(comment, 'score', 0)
                                    })
                            print(f"      ✓ Got {len(comments)} comments")
                        except Exception as e:
                            print(f"      ⚠️  Comment error: {e}")
                            comments = []
                        
                        posts.append({
                            'id': submission.id,
                            'title': submission.title,
                            'body': submission.selftext[:500],
                            'url': f"https://reddit.com{submission.permalink}",
                            'subreddit': subreddit_name,
                            'score': submission.score,
                            'num_comments': submission.num_comments,
                            'created_utc': submission.created_utc,
                            'comments': comments
                        })
                        
                        print(f"      ✅ Added to results (total: {len(posts)})")
                        
                        if len(posts) >= limit:
                            print(f"\n  🎯 Reached target of {limit} posts!")
                            break
                        
                        time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  ❌ ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                if len(posts) >= limit:
                    break
                
                time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE: {len(posts)} posts found")
        print(f"{'='*60}\n")
        
        return posts
    
    def analyze_post(self, post):
        """Analyze with Groq - simplified"""
        
        print(f"  🤖 Analyzing with AI...")
        
        comments_text = "\n".join([
            f"- {c['text'][:50]}..."
            for c in post['comments'][:3]
        ])
        
        prompt = f"""Analyze this briefly. Return ONLY JSON:

Title: {post['title']}
Body: {post['body'][:300]}
Comments: {comments_text}

Return:
{{
  "pain_score": 0-100,
  "business_context": true/false,
  "willingness_to_pay": "high/medium/low/none",
  "frequency": "daily/weekly/monthly",
  "people_affected": number,
  "key_pain_indicators": ["phrase1"],
  "me_too_count": number,
  "existing_solutions": [],
  "solution_gaps": [],
  "recommendation": "strong_opportunity/moderate/weak/skip",
  "reasoning": "brief"
}}"""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Return only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            ai_text = response.choices[0].message.content
            ai_text = ai_text.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(ai_text)
            analysis['opportunity_score'] = self._calculate_score(post, analysis)
            
            print(f"  ✅ AI analysis complete (score: {analysis['opportunity_score']})")
            
            return analysis
        
        except Exception as e:
            print(f"  ❌ AI error: {e}")
            return None
    
    def _calculate_score(self, post, analysis):
        """Simple scoring"""
        score = analysis['pain_score'] * 2.5
        score += min(100, post['score'] / 5)
        wtp = {'high': 200, 'medium': 100, 'low': 50, 'none': 0}
        score += wtp.get(analysis['willingness_to_pay'], 0)
        return min(1000, int(score))
    
    def analyze_category(self, category, limit=5):
        """Full pipeline - diagnostic version"""
        
        print("\n" + "="*60)
        print(f"STARTING ANALYSIS: {category}")
        print("="*60 + "\n")
        
        start_time = time.time()
        
        # Scrape
        posts = self.scrape_posts(category, limit=limit)
        
        if not posts:
            print("❌ No posts found!\n")
            return []
        
        print(f"\n🤖 ANALYZING {len(posts)} POSTS WITH AI\n")
        
        results = []
        for i, post in enumerate(posts, 1):
            print(f"[{i}/{len(posts)}] {post['title'][:40]}...")
            
            analysis = self.analyze_post(post)
            
            if analysis:
                post['analysis'] = analysis
                results.append(post)
            
            time.sleep(0.5)
        
        results.sort(key=lambda x: x['analysis']['opportunity_score'], reverse=True)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ ANALYSIS COMPLETE")
        print(f"   Found: {len(results)} opportunities")
        print(f"   Time: {elapsed:.1f} seconds")
        print(f"{'='*60}\n")
        
        return results