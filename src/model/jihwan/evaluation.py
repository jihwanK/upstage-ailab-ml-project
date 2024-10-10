import pandas as pd
import numpy as np

def precision_at_k(recommended_items, relevant_items, k):
    recommended_items = recommended_items[:k]
    relevant_items_set = set(relevant_items)
    hits = len(set(recommended_items) & relevant_items_set)
    return hits / k

def recall_at_k(recommended_items, relevant_items, k):
    relevant_items_set = set(relevant_items)
    hits = len(set(recommended_items) & relevant_items_set)
    return hits / len(relevant_items_set)


if __name__ == "__main__":
    
    ### model
    model = None
    
    ### evaluation
    precision_scores = []
    recall_scores = []
    f1_scores = []
    K = 10
    
    testset = pd.read_csv("../../../data/train_eval/test.csv")
    masked_df = testset.copy()
    users = masked_df.index

    for idx in masked_df.shape[0]:
        relevant_items = np.where(masked_df.iloc[idx] != 0)[0]
        recommended_items = model.recommend(users[idx], k=K)
        
        precision = precision_at_k(recommended_items, relevant_items, k=K)
        recall = recall_at_k(recommended_items, relevant_items, k=K)
        f1_score = 2 * (precision * recall) / (precision + recall)
        
        precision_scores.append(precision)
        recall_scores.append(recall)
        f1_scores.append(f1_score)

    avg_precision = np.mean(precision_scores)
    avg_recall = np.mean(recall_scores)
    avg_f1 = np.mean(f1_scores)

    print(f"Precision@{K}: {avg_precision}, Recall@{K}: {avg_recall}, F1@{K}: {avg_f1}")
