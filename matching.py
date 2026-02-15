# matching.py

CATEGORY_PROFILES = {
    'marketing': {
        'backgrounds': {'marketer': 40, 'developer': 25, 'sales': 30, 'designer': 20},
        'complexity': 'medium',
        'typical_cost': 5000
    },
    'developer_tools': {
        'backgrounds': {'developer': 40, 'marketer': 15, 'sales': 10, 'designer': 10},
        'complexity': 'high',
        'typical_cost': 3000
    },
    'sales': {
        'backgrounds': {'sales': 40, 'marketer': 30, 'developer': 20, 'designer': 15},
        'complexity': 'medium',
        'typical_cost': 7000
    },
    'productivity': {
        'backgrounds': {'developer': 30, 'marketer': 25, 'sales': 25, 'designer': 25},
        'complexity': 'medium',
        'typical_cost': 4000
    },
    'general': {
        'backgrounds': {'developer': 20, 'marketer': 20, 'sales': 20, 'designer': 20},
        'complexity': 'low',
        'typical_cost': 2000
    }
}

def calculate_match(user_profile, category):
    """Calculate match score 0-100"""
    
    score = 0
    cat_profile = CATEGORY_PROFILES.get(category, CATEGORY_PROFILES['general'])
    
    # 1. Background match (40 points)
    bg = user_profile.get('background', 'other')
    score += cat_profile['backgrounds'].get(bg, 10)
    
    # 2. Interest match (30 points)
    interests = user_profile.get('interests', [])
    if category in interests or category.replace('_', ' ') in [i.lower() for i in interests]:
        score += 30
    
    # 3. Time feasibility (15 points)
    time_map = {'nights_weekends': 10, 'part_time': 15, 'full_time': 15}
    score += time_map.get(user_profile.get('time_available'), 10)
    
    # 4. Budget feasibility (15 points)
    budget_str = user_profile.get('budget', '0-1000')
    budget = int(budget_str.split('-')[1].replace('k', '000').replace('+', ''))
    
    if budget >= cat_profile['typical_cost']:
        score += 15
    elif budget >= cat_profile['typical_cost'] / 2:
        score += 10
    else:
        score += 5
    
    return min(100, score)

def rank_categories(user_profile):
    """Return categories sorted by match score"""
    
    categories = ['marketing', 'sales', 'productivity', 'developer_tools', 'general']
    
    ranked = []
    for cat in categories:
        match = calculate_match(user_profile, cat)
        ranked.append({
            'name': cat,
            'display_name': cat.replace('_', ' ').title(),
            'match': match
        })
    
    # Sort by match score descending
    ranked.sort(key=lambda x: x['match'], reverse=True)
    
    return ranked