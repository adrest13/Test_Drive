import csv
from collections import deque
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parent / "data" / "social_small.csv"


def _find_users_file(csv_path):
    csv_path = Path(csv_path)
    if csv_path.name.endswith("_edges.csv"):
        candidate = csv_path.with_name(csv_path.name.replace("_edges.csv", "_users.csv"))
        if candidate.exists():
            return candidate
    candidate = csv_path.with_name(f"{csv_path.stem}_users.csv")
    if candidate.exists():
        return candidate
    return None


def load_graph(csv_path=DATASET_PATH):
    csv_path = Path(csv_path)
    graph = {}

    users_file = _find_users_file(csv_path)
    if users_file is not None:
        with users_file.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                user = row[0].strip()
                if user:
                    graph.setdefault(user, [])

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        for left, right in reader:
            left = left.strip()
            right = right.strip()
            if not left or not right:
                continue
            graph.setdefault(left, []).append(right)
            graph.setdefault(right, []).append(left)

    return graph


def people_in_network_radius(user, max_distance, csv_path=DATASET_PATH):
    """Вернуть dict[int, list[str]]: distance -> users на этом расстоянии."""
    graph = load_graph(csv_path)

    if user not in graph or max_distance <= 0:
        return {}

    distances = {user: 0}
    queue = deque([user])
    
    while queue:
        current = queue.popleft()
        current_distance = distances[current]
        
        if current_distance >= max_distance:
            continue
            
        for neighbor in graph.get(current, []):
            if neighbor not in distances:
                next_distance = current_distance + 1
                if next_distance <= max_distance: 
                    distances[neighbor] = next_distance
                    queue.append(neighbor)
    
    result = {}
    for person, dist in distances.items():
        if person != user and 1 <= dist <= max_distance:
            result.setdefault(dist, []).append(person)
    
    for dist in result:
        result[dist].sort()
    
    return result


def recommend_people(user, max_distance=2, limit=5, csv_path=DATASET_PATH):
    """Вернуть кандидатов для знакомства в фиксированном формате."""
    graph = load_graph(csv_path)
    
    if user not in graph or limit <= 0 or max_distance < 2:
        return []
    
    distances = {user: 0}
    queue = deque([user])
    
    while queue:
        current = queue.popleft()
        current_distance = distances[current]
        
        if current_distance >= max_distance:  
            continue
            
        for neighbor in graph.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = current_distance + 1
                queue.append(neighbor)
    
    candidates = []
    direct_friends = set(graph.get(user, []))
    user_friends = direct_friends 
    
    for person, dist in distances.items():
        if (person != user and person not in direct_friends and 2 <= dist <= max_distance):
            
            person_friends = set(graph.get(person, []))
            mutual_friends = len(user_friends.intersection(person_friends))
            
            candidates.append({
                "user": person,
                "distance": dist,
                "mutual_friends": mutual_friends
            })
    
    candidates.sort(key=lambda x: (x["distance"], -x["mutual_friends"], x["user"]))

    return candidates[:limit]