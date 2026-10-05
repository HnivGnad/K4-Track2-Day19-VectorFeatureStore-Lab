"""Five-query smoke demo for the bonus hybrid-memory agent."""
from agent import DictProfileStore, HybridMemoryAgent


agent = HybridMemoryAgent(profile_store=DictProfileStore())
for memory in [
    "Tôi đã đọc hướng dẫn Kubernetes về Deployment, Service và rolling update.",
    "Kubernetes Horizontal Pod Autoscaler tự động mở rộng pod theo CPU và lưu lượng.",
    "Tài liệu cloud security nói về least privilege, mã hoá và audit log.",
    "Bài viết FinOps giải thích cách giảm chi phí cloud bằng rightsizing.",
    "Ghi chú AI: hybrid search kết hợp BM25 với vector bằng Reciprocal Rank Fusion.",
]:
    agent.remember(memory)

queries = [
    "Tôi đã đọc gì về Kubernetes?",
    "Recommend đọc gì tiếp",
    "Tôi đang quan tâm gì gần đây?",
    "Tài liệu về tự động mở rộng hạ tầng?",
    "Cho tôi summary cloud security",
]

for number, query in enumerate(queries, 1):
    print(f"\n=== Query {number}: {query} ===")
    print(agent.recall(query))
