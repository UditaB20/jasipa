"""Curated question material used by the deterministic fallback of QuestionGenerationAgent.

The fallback is skill-driven rather than department-driven: MCQs are pulled for whichever JD skills
have bank entries, coding challenges are chosen by proficiency level and role domain, and every
other required skill gets a scenario question anchored to a responsibility from the JD.
Each coding challenge carries a reference solution that is verified against its tests in the sandbox.
"""

# skill keyword (lower-case) -> MCQs. "level" is the minimum proficiency the item suits.
MCQ_BANK = {
    "python": [
        {"level": "foundational", "prompt": "What does `list(dict.fromkeys(['b', 'a', 'b']))` return in Python 3.7+?",
         "options": ["A) ['a', 'b']", "B) ['b', 'a']", "C) ['b', 'a', 'b']", "D) {'b': None, 'a': None}"],
         "correct_option": "B", "rubric_guideline": "Dicts preserve insertion order, so this de-duplicates while keeping first occurrence order."},
        {"level": "intermediate", "prompt": "Which statement about Python's `asyncio` compared with threads is correct?",
         "options": ["A) asyncio runs coroutines on multiple CPU cores in parallel",
                     "B) asyncio uses a single-threaded event loop with cooperative scheduling, suited to I/O-bound work",
                     "C) asyncio removes the GIL for CPU-bound code",
                     "D) asyncio can only be used for file I/O"],
         "correct_option": "B", "rubric_guideline": "Cooperative single-threaded event loop; best for I/O-bound concurrency."},
    ],
    "sql": [
        {"level": "foundational", "prompt": "Which clause filters groups after aggregation?",
         "options": ["A) WHERE", "B) HAVING", "C) ORDER BY", "D) DISTINCT"], "correct_option": "B",
         "rubric_guideline": "HAVING filters aggregated groups; WHERE filters rows before grouping."},
        {"level": "intermediate", "prompt": "For salaries [100, 90, 90, 80], which window function gives the value 80 rank 3?",
         "options": ["A) ROW_NUMBER()", "B) RANK()", "C) DENSE_RANK()", "D) NTILE(3)"], "correct_option": "C",
         "rubric_guideline": "DENSE_RANK does not leave gaps after ties (100→1, 90→2, 80→3)."},
    ],
    "javascript": [
        {"level": "foundational", "prompt": "What does `[1, 2, 3].map(x => x * 2).filter(x => x > 2)` evaluate to?",
         "options": ["A) [2, 4, 6]", "B) [4, 6]", "C) [3]", "D) [2]"], "correct_option": "B",
         "rubric_guideline": "map doubles to [2,4,6]; filter keeps values greater than 2."},
    ],
    "typescript": [
        {"level": "intermediate", "prompt": "What is the main difference between `unknown` and `any` in TypeScript?",
         "options": ["A) They are identical", "B) `unknown` must be narrowed before use; `any` disables type checking",
                     "C) `any` must be narrowed before use", "D) `unknown` only applies to function return types"],
         "correct_option": "B", "rubric_guideline": "unknown is the type-safe counterpart of any."},
    ],
    "react": [
        {"level": "intermediate", "prompt": "Why should list items rendered in React have stable `key` props?",
         "options": ["A) Keys are required for CSS styling", "B) They let React match items between renders so state and DOM are preserved correctly",
                     "C) They make components render twice as fast in all cases", "D) Keys are only needed for server rendering"],
         "correct_option": "B", "rubric_guideline": "Keys drive reconciliation identity; unstable keys cause lost state and extra DOM work."},
    ],
    "java": [
        {"level": "intermediate", "prompt": "What is the key distinction between `Comparable` and `Comparator` in Java?",
         "options": ["A) Comparable supports multiple orderings, Comparator only one",
                     "B) Comparable is in java.util, Comparator in java.lang",
                     "C) Comparable defines a class's natural ordering (compareTo); Comparator supplies external orderings (compare)",
                     "D) There is no functional difference"],
         "correct_option": "C", "rubric_guideline": "Natural ordering vs. external strategy objects."},
    ],
    "machine learning": [
        {"level": "foundational", "prompt": "A model scores 99% training accuracy and 70% validation accuracy. What is the most likely issue?",
         "options": ["A) Underfitting", "B) Overfitting", "C) Data leakage into validation", "D) Class balance is perfect"],
         "correct_option": "B", "rubric_guideline": "Large train/validation gap indicates overfitting."},
        {"level": "intermediate", "prompt": "For a fraud dataset with 0.5% positives, which metric is most informative?",
         "options": ["A) Accuracy", "B) Precision-recall AUC", "C) Mean squared error", "D) R-squared"],
         "correct_option": "B", "rubric_guideline": "Accuracy is misleading under heavy imbalance; PR-AUC focuses on the rare class."},
    ],
    "pytorch": [
        {"level": "intermediate", "prompt": "Why is `optimizer.zero_grad()` typically called each training step in PyTorch?",
         "options": ["A) To reset model weights", "B) Because gradients accumulate across backward() calls by default",
                     "C) To move tensors to the GPU", "D) To disable autograd"], "correct_option": "B",
         "rubric_guideline": "Gradients accumulate; they must be cleared between steps unless accumulation is intended."},
    ],
    "pandas": [
        {"level": "foundational", "prompt": "Which pandas call returns the number of rows per value of column `dept`?",
         "options": ["A) df['dept'].unique()", "B) df['dept'].value_counts()", "C) df.describe()", "D) df.dropna('dept')"],
         "correct_option": "B", "rubric_guideline": "value_counts tallies occurrences per distinct value."},
    ],
    "docker": [
        {"level": "foundational", "prompt": "What is the relationship between a Docker image and a container?",
         "options": ["A) They are the same thing", "B) A container is a running (or stopped) instance created from an image",
                     "C) An image is a running instance of a container", "D) Images only exist on Docker Hub"],
         "correct_option": "B", "rubric_guideline": "Images are immutable templates; containers are instances."},
    ],
    "kubernetes": [
        {"level": "intermediate", "prompt": "Which Kubernetes object keeps a specified number of identical pod replicas running and supports rolling updates?",
         "options": ["A) Service", "B) ConfigMap", "C) Deployment", "D) Namespace"], "correct_option": "C",
         "rubric_guideline": "Deployments manage ReplicaSets and rolling updates."},
    ],
    "aws": [
        {"level": "foundational", "prompt": "Which AWS service is object storage?",
         "options": ["A) EC2", "B) S3", "C) RDS", "D) Lambda"], "correct_option": "B",
         "rubric_guideline": "S3 provides object storage."},
    ],
    "git": [
        {"level": "foundational", "prompt": "Which command creates a new commit that undoes a previous commit without rewriting history?",
         "options": ["A) git reset --hard", "B) git revert", "C) git rebase -i", "D) git stash"], "correct_option": "B",
         "rubric_guideline": "git revert is history-preserving."},
    ],
    "statistics": [
        {"level": "foundational", "prompt": "A 95% confidence interval for a mean is [10, 14]. Which interpretation is correct?",
         "options": ["A) 95% of observations lie between 10 and 14",
                     "B) The procedure produces intervals that contain the true mean 95% of the time",
                     "C) There is a 95% chance the sample mean is 12", "D) The data are normally distributed"],
         "correct_option": "B", "rubric_guideline": "Frequentist coverage interpretation."},
    ],
    "excel": [
        {"level": "foundational", "prompt": "Which Excel function looks up a value in the first column of a range and returns a value from another column in the same row?",
         "options": ["A) SUMIF", "B) VLOOKUP", "C) CONCAT", "D) COUNTA"], "correct_option": "B",
         "rubric_guideline": "VLOOKUP (or XLOOKUP) performs vertical lookups."},
    ],
    "accounting": [
        {"level": "foundational", "prompt": "Under accrual accounting, when is revenue from a 12-month service contract recognised?",
         "options": ["A) In full when the contract is signed", "B) As the service obligation is satisfied over the 12 months",
                     "C) Only when cash is received", "D) At the end of the contract"], "correct_option": "B",
         "rubric_guideline": "Revenue is recognised as performance obligations are satisfied (ASC 606 / IFRS 15)."},
    ],
    "financial modeling": [
        {"level": "intermediate", "prompt": "Holding everything else constant, what happens to a project's NPV when the discount rate rises?",
         "options": ["A) NPV rises", "B) NPV falls for a project with positive future cash flows", "C) NPV is unchanged", "D) NPV becomes the IRR"],
         "correct_option": "B", "rubric_guideline": "Higher discount rates reduce the present value of future cash flows."},
    ],
    "recruitment": [
        {"level": "foundational", "prompt": "Under the EEOC four-fifths guideline, adverse impact is indicated when a group's selection rate is below what?",
         "options": ["A) 50% of the overall rate", "B) 80% of the highest group's rate", "C) 90% of the average rate", "D) Any difference at all"],
         "correct_option": "B", "rubric_guideline": "Selection rate below 4/5ths of the highest-rate group is a screening indicator."},
    ],
    "human resources": [
        {"level": "foundational", "prompt": "What most reduces interviewer bias in a structured interview?",
         "options": ["A) Letting each interviewer choose their own questions", "B) Asking every candidate the same job-related questions scored against anchored criteria",
                     "C) Relying on overall impressions", "D) Reviewing social-media profiles"], "correct_option": "B",
         "rubric_guideline": "Standardised questions with anchored scoring reduce halo and similarity bias."},
    ],
    "networking": [
        {"level": "foundational", "prompt": "Which protocol resolves human-readable hostnames to IP addresses?",
         "options": ["A) DHCP", "B) DNS", "C) ARP", "D) SMTP"], "correct_option": "B",
         "rubric_guideline": "DNS maps names to addresses."},
    ],
    "linux": [
        {"level": "foundational", "prompt": "Which command shows the processes currently using the most CPU, updating live?",
         "options": ["A) ls -la", "B) top", "C) chmod", "D) grep"], "correct_option": "B", "rubric_guideline": "top / htop display live process usage."},
    ],
    "data analysis": [
        {"level": "foundational", "prompt": "A dataset's mean income is much higher than its median. What does this most likely indicate?",
         "options": ["A) The distribution is right-skewed by high values", "B) The data are perfectly symmetric",
                     "C) The median was computed incorrectly", "D) There are no outliers"], "correct_option": "A",
         "rubric_guideline": "Mean above median indicates right skew."},
    ],
    "system design": [
        {"level": "advanced", "prompt": "A read-heavy service has slow database reads of rarely changing data. Which change most directly reduces read latency?",
         "options": ["A) Add a cache (e.g. Redis) with an explicit invalidation/TTL policy", "B) Increase the number of write replicas only",
                     "C) Switch every request to synchronous batch jobs", "D) Remove database indexes"], "correct_option": "A",
         "rubric_guideline": "Caching hot, slowly changing reads with a clear invalidation strategy."},
    ],
}

# Synonyms map JD skill wording onto bank keys.
SKILL_ALIASES = {
    "postgresql": "sql", "mysql": "sql", "sql server": "sql", "node.js": "javascript", "js": "javascript",
    "scikit-learn": "machine learning", "deep learning": "machine learning", "ml": "machine learning",
    "tensorflow": "machine learning", "hr": "human resources", "talent acquisition": "recruitment",
    "employee relations": "human resources", "finance": "financial modeling", "auditing": "accounting",
    "gcp": "aws", "azure": "aws", "cloud": "aws", "data structures": "python", "algorithms": "python",
    "systems administration": "linux", "troubleshooting": "networking", "power bi": "data analysis",
    "tableau": "data analysis", "numpy": "pandas", "spark": "data analysis", "microservices": "system design",
}

# Required skills that indicate the role writes code, so a coding challenge is appropriate.
# SQL alone does not qualify: analyst roles often list it without writing application code.
CODING_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "scala", "ruby", "php",
    "react", "node.js", "django", "flask", "fastapi", "spring boot", "data structures", "algorithms",
    "pytorch", "tensorflow", "pandas", "numpy", "backend", "frontend", "software engineering",
}
SOFTWARE_SKILLS = {
    "java", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "scala", "ruby", "php", "react",
    "node.js", "django", "flask", "fastapi", "spring boot", "data structures", "algorithms", "microservices",
    "system design", "backend", "frontend", "software engineering",
}

CODING_BANK = [
    {"key": "word_frequency", "level": "foundational", "domains": ["general"], "skill": "Problem Solving",
     "title": "Top words", "function_name": "top_words",
     "prompt": "Write `top_words(text, k)` that returns the k most frequent lower-cased words in `text` (words are separated by whitespace), "
               "ordered by frequency descending and then alphabetically for ties.",
     "starter_code": "def top_words(text, k):\n    # return a list of k words\n    pass\n",
     "tests": [{"args": ["the cat the dog", 1], "expected": ["the"]},
               {"args": ["b a b a c", 2], "expected": ["a", "b"]},
               {"args": ["Hello hello WORLD", 2], "expected": ["hello", "world"], "hidden": True},
               {"args": ["", 3], "expected": [], "hidden": True},
               {"args": ["x y z", 5], "expected": ["x", "y", "z"], "hidden": True}],
     "reference_solution": "def top_words(text, k):\n    counts = {}\n    for w in text.lower().split():\n        counts[w] = counts.get(w, 0) + 1\n    return [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]\n",
     "rubric_guideline": "Correct counting, deterministic tie-breaking, handles empty input and k larger than the vocabulary."},
    {"key": "valid_brackets", "level": "foundational", "domains": ["software"], "skill": "Data Structures",
     "title": "Balanced brackets", "function_name": "is_balanced",
     "prompt": "Write `is_balanced(s)` that returns True if every bracket in `s` ('()', '[]', '{}') is closed in the correct order. Other characters are ignored.",
     "starter_code": "def is_balanced(s):\n    pass\n",
     "tests": [{"args": ["([]{})"], "expected": True}, {"args": ["(]"], "expected": False},
               {"args": [""], "expected": True, "hidden": True}, {"args": ["((a+b)*[c]"], "expected": False, "hidden": True},
               {"args": ["}{"], "expected": False, "hidden": True}],
     "reference_solution": "def is_balanced(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for ch in s:\n        if ch in '([{':\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return not stack\n",
     "rubric_guideline": "Stack-based matching, O(n) time, handles empty string and unmatched closers."},
    {"key": "merge_intervals", "level": "intermediate", "domains": ["software", "general"], "skill": "Algorithms",
     "title": "Merge booking intervals", "function_name": "merge_intervals",
     "prompt": "Write `merge_intervals(intervals)` that merges overlapping [start, end] intervals (touching intervals such as [1,3] and [3,5] also merge) "
               "and returns them sorted by start.",
     "starter_code": "def merge_intervals(intervals):\n    pass\n",
     "tests": [{"args": [[[1, 3], [2, 6], [8, 10]]], "expected": [[1, 6], [8, 10]]},
               {"args": [[[1, 3], [3, 5]]], "expected": [[1, 5]]},
               {"args": [[]], "expected": [], "hidden": True},
               {"args": [[[5, 7], [1, 2], [2, 4]]], "expected": [[1, 4], [5, 7]], "hidden": True},
               {"args": [[[1, 10], [2, 3], [4, 5]]], "expected": [[1, 10]], "hidden": True}],
     "reference_solution": "def merge_intervals(intervals):\n    merged = []\n    for start, end in sorted(intervals):\n        if merged and start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
     "rubric_guideline": "Sort then sweep, O(n log n); handles unsorted input, containment and empty input."},
    {"key": "dept_salary_summary", "level": "intermediate", "domains": ["data"], "skill": "Data Analysis",
     "title": "Department salary summary", "function_name": "department_summary",
     "prompt": "Write `department_summary(rows)` where `rows` is a list of {\"dept\": str, \"salary\": number} records (salary may be null). "
               "Return a dict mapping each department to its average salary rounded to 2 decimals, ignoring null salaries and "
               "omitting departments with no valid salaries.",
     "starter_code": "def department_summary(rows):\n    pass\n",
     "tests": [{"args": [[{"dept": "eng", "salary": 100}, {"dept": "eng", "salary": 50}]], "expected": {"eng": 75.0}},
               {"args": [[{"dept": "ops", "salary": None}, {"dept": "hr", "salary": 10}]], "expected": {"hr": 10.0}},
               {"args": [[]], "expected": {}, "hidden": True},
               {"args": [[{"dept": "a", "salary": 1}, {"dept": "a", "salary": 2}, {"dept": "b", "salary": 3}]], "expected": {"a": 1.5, "b": 3.0}, "hidden": True}],
     "reference_solution": "def department_summary(rows):\n    totals = {}\n    for row in rows:\n        if row.get('salary') is None:\n            continue\n        t = totals.setdefault(row['dept'], [0, 0])\n        t[0] += row['salary']\n        t[1] += 1\n    return {d: round(s / n, 2) for d, (s, n) in totals.items()}\n",
     "rubric_guideline": "Correct grouping, null handling and rounding; equivalent to a SQL GROUP BY with AVG and NULL filtering."},
    {"key": "moving_average", "level": "intermediate", "domains": ["ml"], "skill": "Machine Learning",
     "title": "Rolling feature", "function_name": "moving_average",
     "prompt": "Write `moving_average(values, window)` returning the mean of each full window of size `window`, rounded to 3 decimals. "
               "Return an empty list when the window is larger than the input. Aim for O(n).",
     "starter_code": "def moving_average(values, window):\n    pass\n",
     "tests": [{"args": [[1, 2, 3, 4], 2], "expected": [1.5, 2.5, 3.5]}, {"args": [[5], 2], "expected": []},
               {"args": [[2, 4, 6], 3], "expected": [4.0], "hidden": True},
               {"args": [[1, 1, 1, 1, 1], 1], "expected": [1.0, 1.0, 1.0, 1.0, 1.0], "hidden": True}],
     "reference_solution": "def moving_average(values, window):\n    if window <= 0 or window > len(values):\n        return []\n    out, total = [], sum(values[:window])\n    out.append(round(total / window, 3))\n    for i in range(window, len(values)):\n        total += values[i] - values[i - window]\n        out.append(round(total / window, 3))\n    return out\n",
     "rubric_guideline": "Sliding-window sum for O(n); edge cases for short input."},
    {"key": "cycle_detection", "level": "advanced", "domains": ["software", "general"], "skill": "Algorithms",
     "title": "Dependency cycle check", "function_name": "has_cycle",
     "prompt": "Write `has_cycle(graph)` where `graph` maps each node to a list of nodes it depends on. Return True if the dependency graph contains a cycle.",
     "starter_code": "def has_cycle(graph):\n    pass\n",
     "tests": [{"args": [{"a": ["b"], "b": ["c"], "c": []}], "expected": False},
               {"args": [{"a": ["b"], "b": ["a"]}], "expected": True},
               {"args": [{"a": ["a"]}], "expected": True, "hidden": True},
               {"args": [{"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}], "expected": False, "hidden": True},
               {"args": [{"x": ["y"], "y": ["z"], "z": ["x"], "q": []}], "expected": True, "hidden": True}],
     "reference_solution": "def has_cycle(graph):\n    state = {}\n    def visit(node):\n        if state.get(node) == 1:\n            return True\n        if state.get(node) == 2:\n            return False\n        state[node] = 1\n        if any(visit(n) for n in graph.get(node, [])):\n            return True\n        state[node] = 2\n        return False\n    return any(visit(n) for n in list(graph))\n",
     "rubric_guideline": "DFS with three-colour marking or Kahn's algorithm, O(V + E); handles self-loops and diamonds."},
    {"key": "rate_limiter", "level": "advanced", "domains": ["software"], "skill": "System Design",
     "title": "Sliding-window rate limiter", "function_name": "allowed_requests",
     "prompt": "Write `allowed_requests(timestamps, limit, window)` that processes request timestamps (seconds, non-decreasing) and returns a list of booleans: "
               "True if the request is allowed because fewer than `limit` requests were allowed in the half-open window (t - window, t].",
     "starter_code": "def allowed_requests(timestamps, limit, window):\n    pass\n",
     "tests": [{"args": [[1, 2, 3], 2, 10], "expected": [True, True, False]},
               {"args": [[1, 11, 12], 1, 10], "expected": [True, True, False]},
               {"args": [[], 3, 5], "expected": [], "hidden": True},
               {"args": [[0, 0, 5, 5, 10], 2, 5], "expected": [True, True, True, True, True], "hidden": True}],
     "reference_solution": "from collections import deque\ndef allowed_requests(timestamps, limit, window):\n    q, out = deque(), []\n    for t in timestamps:\n        while q and q[0] <= t - window:\n            q.popleft()\n        if len(q) < limit:\n            q.append(t)\n            out.append(True)\n        else:\n            out.append(False)\n    return out\n",
     "rubric_guideline": "Queue of accepted timestamps evicted by window; amortised O(1) per request."},
]
