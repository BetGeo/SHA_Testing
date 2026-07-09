"""Loading and matching against the SHA project/proposal code list."""
import csv
import difflib
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PROJECTS_PATH = Path(__file__).parent / "data" / "project_codes.tsv"

# Codes that are spoken as short words rather than project names/numbers.
SHORT_CODES = {
    "ADM", "INI", "PD", "SICK", "STAT", "TOL", "TOWOP", "TOWP", "VAC", "_VAC",
}

CODE_PATTERN = re.compile(
    r"\b(LFCIPRJ\d+|PRJ\d+[A-Z]?|PRP\d+[A-Z]?|INI\d+)\b", re.IGNORECASE
)


@dataclass
class Project:
    name: str
    code: str


def _partial_ratio(short: str, long_: str) -> float:
    """Best alignment ratio of `short` against any equal-length window of `long_`."""
    if len(short) > len(long_):
        short, long_ = long_, short
    matcher = difflib.SequenceMatcher(None, short, long_)
    best = 0.0
    for block in matcher.get_matching_blocks():
        start = max(block.b - block.a, 0)
        window = long_[start : start + len(short)]
        ratio = difflib.SequenceMatcher(None, short, window).ratio()
        best = max(best, ratio)
    return best


def _match_score(query: str, candidate: str) -> float:
    words = [w for w in query.split() if w]
    contained = sum(1 for w in words if w in candidate) / len(words) if words else 0
    return max(
        contained,
        _partial_ratio(query, candidate),
        difflib.SequenceMatcher(None, query, candidate).ratio(),
    )


def load_projects(path: Path = DEFAULT_PROJECTS_PATH) -> list[Project]:
    projects = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            projects.append(Project(name=row["name"], code=row["code"]))
    return projects


class ProjectMatcher:
    def __init__(self, projects: list[Project]):
        self.projects = projects
        self.by_code = {p.code.upper(): p for p in projects}
        self.names = [p.name for p in projects]

    def match_code_in_text(self, text: str) -> Project | None:
        """Look for an explicit code (PRJ26031, ADM, VAC, ...) spoken in the text."""
        upper_words = {w.strip(".,") .upper() for w in text.split()}
        for word in upper_words:
            if word in SHORT_CODES and word in self.by_code:
                return self.by_code[word]
        m = CODE_PATTERN.search(text.replace(" ", ""))
        if m:
            code = m.group(1).upper()
            if code in self.by_code:
                return self.by_code[code]
        return None

    def fuzzy_match_name(self, text: str, limit: int = 3) -> list[Project]:
        """Return up to `limit` closest project-name matches for free-spoken text.

        Spoken project references are usually short fragments of a much longer
        official name ("astria" for "Astria Building Design Services"), so a
        plain whole-string similarity ratio scores everything low. We rank by
        the best partial-string alignment instead (same idea as fuzzywuzzy's
        partial_ratio), boosted when every spoken word literally appears in
        the candidate name.
        """
        query = text.strip().lower()
        if not query:
            return []
        scored = sorted(self.projects, key=lambda p: -_match_score(query, p.name.lower()))
        return scored[:limit]

    def resolve(self, text: str, limit: int = 3) -> tuple[Project | None, list[Project]]:
        """Try an exact code match first; otherwise return fuzzy name candidates."""
        exact = self.match_code_in_text(text)
        if exact:
            return exact, []
        return None, self.fuzzy_match_name(text, limit=limit)
