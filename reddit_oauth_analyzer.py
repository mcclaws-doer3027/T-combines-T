import praw
from groq import Groq
import json
import time
from datetime import datetime
import requests
from requests.exceptions import Timeout, RequestException

class RedditOAuthAnalyzer:
    def __init__(self, config, reddit_username=None, reddit_password=None):
        """Initialize Reddit with OAuth"""
        
        print("🔐 Initializing Reddit OAuth...")
        
        if reddit_username and reddit_password:
            self.reddit = praw.Reddit(
                client_id="ohXpoqrZYub1kg",
                client_secret="",
                user_agent=f"python:saas-validator:v1.0 (by /u/{reddit_username})",
                username=reddit_username,
                password=reddit_password,
                timeout=10  # Add timeout!
            )
            try:
                print(f"✅ Authenticated as: u/{self.reddit.user.me()}")
            except Exception as e:
                print(f"⚠️ Auth issue: {e}")
        else:
            self.reddit = praw.Reddit(
                client_id="ohXpoqrZYub1kg",
                client_secret="",
                user_agent="python:saas-validator:v1.0",
                timeout=10
            )
        
        self.groq_client = Groq(api_key=config['GROQ_API_KEY'])
        print("✅ Groq AI initialized\n")
    
    def scrape_posts(self, category, limit=20):  # REDUCED from 30 to 20
        """Scrape Reddit posts - OPTIMIZED VERSION"""
        
        categories = {
            'marketing': {
                'subreddits': ['startups', 'entrepreneur'],  # Reduced to 2
                'keywords': ['struggling', 'problem']  # Reduced to 2
            },
            'sales': {
                'subreddits': ['startups', 'entrepreneur'],
                'keywords': ['difficult', 'issue']
            },
            'productivity': {
                'subreddits': ['startups', 'productivity'],
                'keywords': ['wasting time', 'inefficient']
            },
            'developer_tools': {
                'subreddits': ['programming', 'webdev'],
                'keywords': ['annoying', 'tedious']
            },
            'general': {
                'subreddits': ['startups', 'entrepreneur'],
                'keywords': ['problem', 'struggling']
            }
        }
        
        config = categories.get(category.lower(), categories['general'])
        posts = []
        
        print(f"🔍 Searching {category} (fast mode)...\n")
        
        for subreddit_name in config['subreddits']:
            if len(posts) >= limit:
                break
                
            for keyword in config['keywords']:
                if len(posts) >= limit:
                    break
                    
                try:
                    print(f"→ r/{subreddit_name}: '{keyword}'")
                    
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # OPTIMIZED: Get fewer posts per search
                    for submission in subreddit.search(
                        keyword,
                        limit=8,  # Reduced from 15
                        sort='hot',  # Hot is faster than new
                        time_filter='month'
                    ):
                        # Quick filters (fail fast)
                        if submission.score < 3:
                            continue
                        
                        if not submission.selftext or len(submission.selftext) < 30:
                            continue
                        
                        if submission.selftext in ['[removed]', '[deleted]']:
                            continue
                        
                        # OPTIMIZED: Get only top 5 comments (not 10)
                        try:
                            submission.comments.replace_more(limit=0)
                            comments = []
                            
                            # Only get first 5 comments (FAST)
                            for comment in list(submission.comments)[:5]:
                                if hasattr(comment, 'body') and comment.body not in ['[removed]', '[deleted]']:
                                    comments.append({
                                        'text': comment.body[:200],  # Reduced from 250
                                        'score': getattr(comment, 'score', 0)
                                    })
                                    if len(comments) >= 5:
                                        break
                        except Exception as e:
                            comments = []
                        
                        # Need at least 2 comments
                        if len(comments) < 2:
                            continue
                        
                        posts.append({
                            'id': submission.id,
                            'title': submission.title,
                            'body': submission.selftext[:1000],  # Reduced from 1500
                            'url': f"https://reddit.com{submission.permalink}",
                            'subreddit': subreddit_name,
                            'score': submission.score,
                            'num_comments': submission.num_comments,
                            'created_utc': submission.created_utc,
                            'comments': comments
                        })
                        
                        print(f"  ✓ {submission.title[:45]}...")
                        
                        if len(posts) >= limit:
                            break
                        
                        time.sleep(0.2)  # Reduced from 0.3
                
                except Exception as e:
                    print(f"  ✗ Error: {str(e)[:40]}")
                    continue
                
                time.sleep(0.3)  # Reduced from 0.5
        
        print(f"\n✅ Found {len(posts)} posts\n")
        return posts
    
    def analyze_post(self, post):
        """Analyze with Groq AI - OPTIMIZED"""
        
        # Shorter comment summary
        comments_text = "\n".join([
            f"- {c['text'][:80]}... ({c['score']}↑)"
            for c in post['comments'][:5]  # Only 5 comments
        ])
        
        # SHORTER PROMPT (faster processing)
        prompt = f"""Analyze for SaaS validation. Return ONLY valid JSON.

Title: {post['title']}
r/{post['subreddit']} | {post['score']}↑

Post: {post['body'][:600]}

Comments: {comments_text}

Return exactly:
{{
  "pain_score": 0-100,
  "business_context": true/false,
  "willingness_to_pay": "high/medium/low/none",
  "frequency": "daily/weekly/monthly",
  "people_affected": number,
  "key_pain_indicators": ["phrase1", "phrase2"],
  "me_too_count": number,
  "existing_solutions": ["tool1"],
  "solution_gaps": ["gap1"],
  "recommendation": "strong_opportunity/moderate/weak/skip",
  "reasoning": "brief under 20 words"
}}"""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "SaaS validator. Return only JSON, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500  # Reduced from 600
            )
            
            ai_text = response.choices[0].message.content
            ai_text = ai_text.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(ai_text)
            analysis['opportunity_score'] = self._calculate_score(post, analysis)
            
            return analysis
        
        except Exception as e:
            print(f"  ✗ AI error: {str(e)[:40]}")
            return None
    
    def _calculate_score(self, post, analysis):
        """Calculate score - SAME AS BEFORE"""
        
        score = analysis['pain_score'] * 2.5
        score += min(100, post['score'] / 5 + post['num_comments'])
        
        wtp = {'high': 200, 'medium': 100, 'low': 50, 'none': 0}
        score += wtp.get(analysis['willingness_to_pay'], 0)
        
        score += min(80, analysis['me_too_count'] * 10)
        
        people = analysis['people_affected']
        score += 80 if people > 5000 else (50 if people > 1000 else 20)
        
        solutions = len(analysis['existing_solutions'])
        gaps = len(analysis['solution_gaps'])
        score += 80 if solutions == 0 else (60 if gaps > solutions else 30)
        
        return min(1000, int(score))
    
    def analyze_category(self, category, limit=15):  # REDUCED from 30 to 15
        """Full pipeline - OPTIMIZED"""
        
        print(f"\n{'='*60}")
        print(f"🚀 Fast Analysis: {category}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # STEP 1: Scrape (should take ~30-60 seconds)
        posts = self.scrape_posts(category, limit=limit)
        
        if not posts:
            print("❌ No posts found\n")
            return []
        
        scrape_time = time.time() - start_time
        print(f"⏱️  Scraping took: {scrape_time:.1f}s\n")
        
        # STEP 2: Analyze with AI
        print(f"🤖 Analyzing {len(posts)} posts...\n")
        
        results = []
        for i, post in enumerate(posts, 1):
            print(f"[{i}/{len(posts)}] {post['title'][:50]}...")
            
            analysis = self.analyze_post(post)
            
            if analysis and analysis['recommendation'] != 'skip':
                post['analysis'] = analysis
                results.append(post)
                print(f"  ✅ {analysis['opportunity_score']}/1000")
            else:
                print(f"  ⏭️  Skipped")
            
            time.sleep(0.5)  # Reduced from 0.8
        
        results.sort(key=lambda x: x['analysis']['opportunity_score'], reverse=True)
        
        total_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ Found {len(results)} opportunities")
        print(f"⏱️  Total time: {total_time:.1f}s (~{total_time/60:.1f} min)")
        print(f"{'='*60}\n")
        
        return results