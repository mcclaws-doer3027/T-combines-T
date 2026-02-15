# revenue_calculator.py

def estimate_revenue(analysis_data):
    """Calculate revenue projections"""
    
    # Extract data
    people_affected = analysis_data.get('people_affected', 100)
    wtp = analysis_data.get('willingness_to_pay', 'low')
    
    # Estimate addressable market (typically 10-20% of total)
    addressable = int(people_affected * 0.15)
    
    # Price points based on WTP
    price_map = {
        'high': {'low': 79, 'mid': 149, 'high': 299},
        'medium': {'low': 29, 'mid': 49, 'high': 99},
        'low': {'low': 9, 'mid': 19, 'high': 39},
        'none': {'low': 0, 'mid': 0, 'high': 0}
    }
    
    prices = price_map.get(wtp, price_map['low'])
    
    # Conservative: 10% of addressable
    conservative = {
        'customers': max(10, int(addressable * 0.1)),
        'price': prices['low'],
        'mrr': 0,
        'annual': 0
    }
    conservative['mrr'] = conservative['customers'] * conservative['price']
    conservative['annual'] = conservative['mrr'] * 12
    
    # Moderate: 20% of addressable
    moderate = {
        'customers': max(50, int(addressable * 0.2)),
        'price': prices['mid'],
        'mrr': 0,
        'annual': 0
    }
    moderate['mrr'] = moderate['customers'] * moderate['price']
    moderate['annual'] = moderate['mrr'] * 12
    
    # Optimistic: 40% of addressable
    optimistic = {
        'customers': max(100, int(addressable * 0.4)),
        'price': prices['high'],
        'mrr': 0,
        'annual': 0
    }
    optimistic['mrr'] = optimistic['customers'] * optimistic['price']
    optimistic['annual'] = optimistic['mrr'] * 12
    
    return {
        'conservative': conservative,
        'moderate': moderate,
        'optimistic': optimistic,
        'addressable_market': addressable
    }