# test_clustering.py
from app.parser.txt_loader import TxtLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser
from app.semantic.embedder import EmbeddingEngine
from app.semantic.clustering import ClusteringAnalyzer

raw = TxtLoader("data/raw_surveys/survey_001.txt").load()
cleaned = TextCleaner(raw).clean()
survey = SurveyParser(cleaned).parse()

engine = EmbeddingEngine()
embedding_result = engine.embed(survey.items)

analyzer = ClusteringAnalyzer()
result = analyzer.analyze(embedding_result)

print(f"Mode                 : {result.mode}")
print(f"Cross-affinity items : {len(result.cross_affinity_items)}")
print(f"Low cohesion blocks  : {result.low_cohesion_blocks}")
print()
print("Block cohesion:")
for b in result.block_cohesion:
    flag = " ← LOW" if b.low_cohesion else ""
    print(f"  Block {b.block}: mean={b.mean_similarity:.4f} "
          f"min={b.min_similarity:.4f} max={b.max_similarity:.4f}{flag}")
print()
print("Top 5 cross-affinity items:")
cross = [p for p in result.item_profiles if p.cross_block_affinity]
cross_sorted = sorted(cross, key=lambda p: p.own_block_similarity)[:5]
for p in cross_sorted:
    print(f"  Item {p.item_id}: own_block={p.own_block} "
          f"own_sim={p.own_block_similarity:.4f} "
          f"best_foreign={p.best_foreign_block} "
          f"foreign_sim={p.best_foreign_similarity:.4f}")