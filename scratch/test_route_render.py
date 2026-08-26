import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
import json

def test_routes():
    print("=== Testing Flask /price-trends and /api/price-trends routes ===")
    client = app.test_client()
    
    # 1. GET /price-trends
    res1 = client.get('/price-trends')
    print("GET /price-trends Status:", res1.status_code)
    html = res1.data.decode('utf-8')
    has_data_container = 'id="dataContainer"' in html and 'style="display: none;"' not in html[html.find('id="dataContainer"'):html.find('id="dataContainer"')+50]
    print("Is dataContainer VISIBLE in rendered HTML?", has_data_container)
    print("Is emptyStateBox HIDDEN in rendered HTML?", 'id="emptyStateBox" class="empty-state-box" style="display: none;"' in html)

    # 2. GET /api/price-trends?crop=Rice
    res2 = client.get('/api/price-trends?crop=Rice')
    print("\nGET /api/price-trends?crop=Rice Status:", res2.status_code)
    data = json.loads(res2.data.decode('utf-8'))
    print("API Data Response:")
    print("  has_data:", data.get('has_data'))
    print("  total_observations:", data.get('total_observations'))
    print("  current_avg_price:", data.get('current_avg_price'))
    print("  govt_msp:", data.get('govt_msp'))
    print("  labels count:", len(data.get('labels', [])))
    print("  prices count:", len(data.get('prices', [])))

if __name__ == '__main__':
    test_routes()
