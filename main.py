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
    """Прочитать граф из CSV с рёбрами и, при наличии, из companion users-файла."""
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

    # 1. Если пользователя нет в графе или max_distance <= 0, верните {}.
    if user not in graph or max_distance <= 0:
        return {}

    # Используем BFS для поиска расстояний
    distances = {user: 0}
    queue = deque([user])
    
    while queue:
        current = queue.popleft()
        current_distance = distances[current]
        
        # Если достигли максимального расстояния, не идем дальше
        if current_distance >= max_distance:
            continue
            
        for neighbor in graph.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = current_distance + 1
                queue.append(neighbor)
    
    # Группируем пользователей по расстоянию (исключая исходного пользователя)
    result = {}
    for person, dist in distances.items():
        if person != user and 1 <= dist <= max_distance:
            result.setdefault(dist, []).append(person)
    
    # Сортируем списки пользователей для стабильности
    for dist in result:
        result[dist].sort()
    
    return result


def recommend_people(user, max_distance=2, limit=5, csv_path=DATASET_PATH):
    """Вернуть кандидатов для знакомства в фиксированном формате."""
    graph = load_graph(csv_path)
    
    # 1. Если пользователя нет в графе, limit <= 0 или max_distance < 2, верните [].
    if user not in graph or limit <= 0 or max_distance < 2:
        return []
    
    # 2. Находим расстояния до всех вершин через BFS
    distances = {user: 0}
    queue = deque([user])
    
    while queue:
        current = queue.popleft()
        current_distance = distances[current]
        
        # Не ограничиваем BFS, чтобы найти всех возможных кандидатов
        for neighbor in graph.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = current_distance + 1
                queue.append(neighbor)
    
    # 3. Исключаем самого пользователя и его прямых друзей
    # 4. Оставляем только кандидатов на расстоянии от 2 до max_distance
    candidates = []
    direct_friends = set(graph.get(user, []))
    
    for person, dist in distances.items():
        if (person != user andperson not in direct_friends and 2 <= dist <= max_distance):
            
            # 5. Считаем число общих друзей с исходным пользователем
            mutual_friends = 0
            user_friends = set(graph.get(user, []))
            person_friends = set(graph.get(person, []))
            
            # Общие друзья - пересечение множеств друзей пользователя и кандидата
            mutual_friends = len(user_friends.intersection(person_friends))
            
            candidates.append({
                "user": person,
                "distance": dist,
                "mutual_friends": mutual_friends
            })
    
    # 7. Сортируем кандидатов:
    #    - меньше distance лучше
    #    - больше mutual_friends лучше
    #    - затем по user
    candidates.sort(key=lambda x: (x["distance"], -x["mutual_friends"], x["user"]))
    
    # 8. Обрезаем результат по limit
    return candidates[:limit]


# Краткое пояснение решения:
# Модель данных: граф
# Алгоритм для people_in_network_radius:
#   Используется BFS
# Почему он подходит:
#   BFS подходит для поиска кратчайших расстояний в невзвешенном графе.
# Как вы считали рейтинг в recommend_people:
#   Для каждого кандидата расстояние уже известно из BFS. Количество общих друзей
#   считается как размер пересечения множеств друзей исходного пользователя и
#   кандидата. Затем кандидаты сортируются по приоритету: сначала по расстоянию
#   (меньше - лучше), затем по количеству общих друзей (больше - лучше), затем
#   по имени пользователя.
