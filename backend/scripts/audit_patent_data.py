"""Read-only audit of the local patent CSV corpus and retrieval index metadata."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def normalized(value: str) -> str:
    return " ".join((value or "").lower().split())


def content_hash(row: dict[str, str]) -> str:
    value = normalized(row.get("title", "")) + " " + normalized(row.get("abstract", ""))
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def duplicate_summary(counts: Counter) -> dict[str, int]:
    return {
        "repeated_keys": sum(count > 1 for count in counts.values()),
        "excess_rows": sum(count - 1 for count in counts.values() if count > 1),
    }


class UnionFind:
    def __init__(self, keys):
        self.parent = {key: key for key in keys}
        self.size = {key: 1 for key in keys}

    def find(self, key):
        while key != self.parent[key]:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def join(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            if self.size[left] < self.size[right]:
                left, right = right, left
            self.parent[right] = left
            self.size[left] += self.size[right]

    def component_sizes(self):
        return Counter(self.find(key) for key in self.parent)


def audit():
    raw_counts = Counter()
    raw_domains = defaultdict(set)
    raw_by_file = {}
    for path in sorted((DATA / "raw").glob("*.csv")):
        local = Counter()
        for row in rows(path):
            key = (row.get("Lens ID") or "").strip()
            if key:
                raw_counts[key] += 1
                local[key] += 1
                raw_domains[key].add(path.stem)
        raw_by_file[path.name] = {"rows_with_id": sum(local.values()), "unique_ids": len(local), **duplicate_summary(local)}

    patents = list(rows(DATA / "processed" / "patents.csv"))
    by_id = {row["patent_id"]: row for row in patents}
    patent_ids = set(by_id)
    patent_id_counts = Counter(row["patent_id"] for row in patents)
    display_counts = Counter(normalized(row.get("display_key", "")) for row in patents if row.get("display_key"))
    hashes = defaultdict(list)
    title_counts = Counter()
    for row in patents:
        hashes[content_hash(row)].append(row["patent_id"])
        if normalized(row.get("title", "")):
            title_counts[normalized(row["title"])] += 1
    duplicate_hash_groups = [group for group in hashes.values() if len(group) > 1]

    class_rows = 0
    class_types = Counter()
    class_key_counts = Counter()
    all_class_links = set()
    cpc_class_links = set()
    class_patents = set()
    class_by_patent = defaultdict(set)
    cpc_patents_by_code = defaultdict(set)
    for row in rows(DATA / "processed" / "classifications.csv"):
        class_rows += 1
        pid = row["patent_id"]
        kind = row["classification_type"]
        code = row["classification_code"]
        class_types[kind] += 1
        class_key_counts[(pid, kind, code)] += 1
        all_class_links.add((pid, code))
        if kind == "CPC":
            cpc_class_links.add((pid, code))
        class_patents.add(pid)
        if pid in patent_ids and kind == "CPC":
            class_by_patent[pid].add(code)
            cpc_patents_by_code[code].add(pid)

    family_rows = 0
    family_types = Counter()
    family_key_counts = Counter()
    family_patents = set()
    family_members = set()
    self_links = Counter()
    internal_edges = Counter()
    uf_simple = UnionFind(patent_ids)
    uf_extended = UnionFind(patent_ids)
    direct_family_pairs = set()
    for row in rows(DATA / "processed" / "patent_families.csv"):
        family_rows += 1
        pid = row["patent_id"]
        member = row["family_member"]
        kind = row["family_type"]
        family_types[kind] += 1
        family_key_counts[(pid, kind, member)] += 1
        family_patents.add(pid)
        family_members.add(member)
        if pid == member:
            self_links[kind] += 1
        if pid in patent_ids and member in patent_ids and pid != member:
            internal_edges[kind] += 1
            direct_family_pairs.add(frozenset((pid, member)))
            if kind == "SIMPLE":
                uf_simple.join(pid, member)
            if kind == "EXTENDED":
                uf_extended.join(pid, member)

    simple_sizes = uf_simple.component_sizes()
    extended_sizes = uf_extended.component_sizes()
    duplicate_groups_in_simple = 0
    duplicate_groups_in_extended = 0
    duplicate_groups_with_shared_cpc = 0
    duplicate_groups_with_simple_family_and_shared_cpc = 0
    direct_duplicate_pairs = set()
    duplicate_group_examples = []
    for group in duplicate_hash_groups:
        if len({uf_simple.find(pid) for pid in group}) < len(group):
            duplicate_groups_in_simple += 1
        if len({uf_extended.find(pid) for pid in group}) < len(group):
            duplicate_groups_in_extended += 1
        shared_cpc = False
        simple_and_cpc = False
        for i, left in enumerate(group):
            for right in group[i + 1:]:
                codes_overlap = bool(class_by_patent[left] & class_by_patent[right])
                shared_cpc |= codes_overlap
                simple_and_cpc |= codes_overlap and uf_simple.find(left) == uf_simple.find(right)
                pair = frozenset((left, right))
                if pair in direct_family_pairs:
                    direct_duplicate_pairs.add(pair)
        duplicate_groups_with_shared_cpc += shared_cpc
        duplicate_groups_with_simple_family_and_shared_cpc += simple_and_cpc
        if len(duplicate_group_examples) < 8:
            duplicate_group_examples.append([
                {"patent_id": pid, "display_key": by_id[pid].get("display_key"),
                 "jurisdiction": by_id[pid].get("jurisdiction"), "domain": by_id[pid].get("domain")}
                for pid in group[:4]
            ])

    citation_rows = list(rows(DATA / "processed" / "citations_metadata.csv"))
    citation_ids = Counter(row["patent_id"] for row in citation_rows)
    retrieval = list(rows(DATA / "vector_store" / "patents_deduped.csv"))
    retrieval_ids = [row["patent_id"] for row in retrieval]
    retrieval_hashes = Counter(row.get("content_hash", "") for row in retrieval)
    with (DATA / "vector_store" / "metadata_mapping.json").open(encoding="utf-8") as stream:
        mapping = json.load(stream)
    map_ids = [mapping.get(str(i)) for i in range(len(mapping))]

    def component_summary(sizes):
        multi = [size for size in sizes.values() if size > 1]
        return {"multi_patent_components": len(multi), "patents_in_multi_components": sum(multi),
                "largest_component": max(multi, default=1)}

    return {
        "raw": {"rows_with_id": sum(raw_counts.values()), "unique_lens_ids": len(raw_counts),
                **duplicate_summary(raw_counts),
                "ids_in_multiple_domain_files": sum(len(domains) > 1 for domains in raw_domains.values()),
                "by_file": raw_by_file},
        "processed_patents": {"rows": len(patents), "unique_patent_ids": len(by_id),
                              "id_duplicates": duplicate_summary(patent_id_counts),
                              "display_key_duplicates": duplicate_summary(display_counts),
                              "identical_title_abstract_groups": len(duplicate_hash_groups),
                              "identical_title_abstract_excess_rows": sum(len(group) - 1 for group in duplicate_hash_groups),
                              "identical_title_groups": duplicate_summary(title_counts),
                              "blank_titles": sum(not normalized(row.get("title", "")) for row in patents),
                              "blank_abstracts": sum(not normalized(row.get("abstract", "")) for row in patents),
                              "duplicate_groups_with_simple_family_connection": duplicate_groups_in_simple,
                              "duplicate_groups_with_extended_family_connection": duplicate_groups_in_extended,
                              "duplicate_groups_with_shared_cpc": duplicate_groups_with_shared_cpc,
                              "duplicate_groups_with_simple_family_and_shared_cpc": duplicate_groups_with_simple_family_and_shared_cpc,
                              "direct_family_pairs_with_identical_content": len(direct_duplicate_pairs),
                              "examples": duplicate_group_examples},
        "classifications": {"rows": class_rows, "by_type": dict(class_types),
                            "unique_patent_ids": len(class_patents),
                            "orphan_patent_ids": len(class_patents - patent_ids),
                            "orphan_rows": sum(n for (pid, _, _), n in class_key_counts.items() if pid not in patent_ids),
                            "duplicate_patent_type_code": duplicate_summary(class_key_counts),
                            "unique_patent_code_links_all_types": len(all_class_links),
                            "unique_patent_code_links_cpc_only": len(cpc_class_links),
                            "non_cpc_only_links_loaded_as_cpc_by_current_importer": len(all_class_links - cpc_class_links),
                            "cpc_codes": len(cpc_patents_by_code),
                            "patents_with_cpc": len(class_by_patent),
                            "cpc_codes_on_multiple_patents": sum(len(ids) > 1 for ids in cpc_patents_by_code.values()),
                            "top_shared_cpc": cpc_patents_by_code and sorted(
                                ((code, len(ids)) for code, ids in cpc_patents_by_code.items()),
                                key=lambda pair: (-pair[1], pair[0]))[:10]},
        "families": {"rows": family_rows, "by_type": dict(family_types),
                     "source_patent_ids": len(family_patents),
                     "orphan_source_ids": len(family_patents - patent_ids),
                     "member_ids": len(family_members),
                     "member_ids_absent_from_patents": len(family_members - patent_ids),
                     "self_links": dict(self_links),
                     "duplicate_patent_type_member": duplicate_summary(family_key_counts),
                     "internal_nonself_edges": dict(internal_edges),
                     "simple_components": component_summary(simple_sizes),
                     "extended_components": component_summary(extended_sizes)},
        "citations_metadata": {"rows": len(citation_rows), "unique_patent_ids": len(citation_ids),
                               "orphan_patent_ids": len(set(citation_ids) - patent_ids),
                               "duplicate_patent_ids": duplicate_summary(citation_ids)},
        "retrieval_corpus": {"rows": len(retrieval), "unique_patent_ids": len(set(retrieval_ids)),
                             "duplicate_content_hashes": duplicate_summary(retrieval_hashes),
                             "ids_not_in_processed_patents": len(set(retrieval_ids) - patent_ids),
                             "metadata_mapping_rows": len(mapping),
                             "mapping_matches_corpus_order": map_ids == retrieval_ids},
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
