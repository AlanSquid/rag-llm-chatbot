import streamlit as st
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import random
import numpy as np
from sklearn.cluster import KMeans
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import datetime
import os

# 設置日誌系統
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 從環境變量獲取 OpenAI API 金鑰
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    st.error("No valid API key provided. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=api_key)

# 初始化 SentenceTransformer 模型
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    logging.info("Successfully loaded SentenceTransformer model")
except Exception as e:
    logging.error(f"Error loading SentenceTransformer model: {e}")
    st.error("Failed to load SentenceTransformer model. Please check your internet connection and try again.")
    st.stop()

# 定義知識庫
knowledge_base = [
    "Our store hours are 9 AM to 5 PM, Monday to Friday.",
    "To reset your password, click on the 'Forgot Password' link on the login page.",
    "We offer refunds within 30 days of purchase with a valid receipt.",
    "Our product warranty covers manufacturing defects for one year from the date of purchase.",
    "For technical support, please email support@example.com or call 0800-123-4567."
]

# 將知識庫轉換為嵌入向量
try:
    knowledge_embeddings = sentence_model.encode(knowledge_base)
    logging.info("Successfully encoded knowledge base")
except Exception as e:
    logging.error(f"Error encoding knowledge base: {e}")
    st.error("Failed to encode knowledge base. Please try again later.")
    st.stop()

# 初始化情感分析模型
model_name = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_analyzer = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# 定義不同情緒的回應模板
response_templates = {
    "POSITIVE": [
        "I'm glad to hear your positive feedback! {response}",
        "That's great! {response}",
        "Thank you for your support! {response}"
    ],
    "NEGATIVE": [
        "I'm sorry to hear you're having issues. {response} Let's work together to resolve this.",
        "I understand your frustration. {response} We'll do our best to help you.",
        "I apologize for the inconvenience. {response} Please let me know if there's anything else I can assist you with."
    ]
}

# 根據查詢的情感分析結果，生成個性化回應
def analyze_sentiment_and_personalize(query, response):
    sentiment_result = sentiment_analyzer(query)[0]
    sentiment_score = sentiment_result['score']

    if sentiment_result['label'] == 'POSITIVE' and sentiment_score > 0.6:
        sentiment = "POSITIVE"
    elif sentiment_result['label'] == 'NEGATIVE' and sentiment_score > 0.6:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"

    if sentiment in ["POSITIVE", "NEGATIVE"]:
        templates = response_templates[sentiment]
        template = random.choice(templates)
        return template.format(response=response), sentiment
    else:
        return response, sentiment

# 主動學習和知識庫更新系統
class ActiveLearningSystem:
    def __init__(self, knowledge_base, confidence_threshold=0.7):
        self.knowledge_base = knowledge_base
        self.confidence_threshold = confidence_threshold
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.uncertain_queries = []

    def evaluate_certainty(self, query, response):
        return len(response) > 50

    def add_uncertain_query(self, query, response):
        self.uncertain_queries.append((query, response))

    def cluster_uncertain_queries(self, n_clusters=5):
        if len(self.uncertain_queries) < n_clusters:
            return self.uncertain_queries

        queries = [q for q, _ in self.uncertain_queries]
        embeddings = self.sentence_model.encode(queries)

        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(embeddings)

        centers = kmeans.cluster_centers_
        representative_queries = []

        for i in range(n_clusters):
            cluster_indices = np.where(kmeans.labels_ == i)[0]
            center_embedding = centers[i]
            distances = np.linalg.norm(embeddings[cluster_indices] - center_embedding, axis=1)
            representative_index = cluster_indices[np.argmin(distances)]
            representative_queries.append(self.uncertain_queries[representative_index])

        return representative_queries

    def update_knowledge_base(self, new_entries):
        self.knowledge_base.extend(new_entries)
        global knowledge_embeddings
        knowledge_embeddings = sentence_model.encode(self.knowledge_base)

# 初始化主動學習系統
active_learning_system = ActiveLearningSystem(knowledge_base)

# 報告和分析系統
class AnalyticsSystem:
    def __init__(self):
        self.queries = []
        self.response_times = []
        self.sentiments = []
        self.topics = []

    def log_interaction(self, query, response_time, sentiment, topic):
        self.queries.append(query)
        self.response_times.append(response_time)
        self.sentiments.append(sentiment)
        self.topics.append(topic)

    def generate_report(self, start_date, end_date):
        df = pd.DataFrame({
            'query': self.queries,
            'response_time': self.response_times,
            'sentiment': self.sentiments,
            'topic': self.topics,
            'timestamp': pd.date_range(start=start_date, periods=len(self.queries), freq='H')
        })

        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        df = df.loc[mask]

        fig, axs = plt.subplots(2, 2, figsize=(15, 10))

        # 每日查詢量
        df.groupby(df['timestamp'].dt.date).size().plot(kind='line', ax=axs[0, 0])
        axs[0, 0].set_title('Daily Query Volume')
        axs[0, 0].set_xlabel('Date')
        axs[0, 0].set_ylabel('Number of Queries')

        # 回應時間分佈
        df['response_time'].hist(bins=20, ax=axs[0, 1])
        axs[0, 1].set_title('Response Time Distribution')
        axs[0, 1].set_xlabel('Response Time (seconds)')
        axs[0, 1].set_ylabel('Frequency')

        # 情感分佈
        sentiment_counts = Counter(df['sentiment'])
        axs[1, 0].pie(sentiment_counts.values(), labels=sentiment_counts.keys(), autopct='%1.1f%%')
        axs[1, 0].set_title('Sentiment Distribution')

        # 熱門主題
        topic_counts = Counter(df['topic']).most_common(5)
        topics, counts = zip(*topic_counts)
        axs[1, 1].bar(topics, counts)
        axs[1, 1].set_title('Top 5 Popular Topics')
        axs[1, 1].set_xlabel('Topic')
        axs[1, 1].set_ylabel('Count')
        plt.setp(axs[1, 1].get_xticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        # 生成報告文字
        report = f"""
        Analysis Report ({start_date} to {end_date})

        1. Total number of queries: {len(df)}
        2. Average response time: {df['response_time'].mean():.2f} seconds
        3. Sentiment distribution:
           Positive: {sentiment_counts['POSITIVE']} ({sentiment_counts['POSITIVE']/len(df)*100:.1f}%)
           Neutral: {sentiment_counts['NEUTRAL']} ({sentiment_counts['NEUTRAL']/len(df)*100:.1f}%)
           Negative: {sentiment_counts['NEGATIVE']} ({sentiment_counts['NEGATIVE']/len(df)*100:.1f}%)
        4. Top 5 popular topics:
           {', '.join([f"{topic} ({count})" for topic, count in topic_counts])}
        """

        return report, fig

# 初始化分析系統
analytics_system = AnalyticsSystem()

# 從知識庫中檢索相關內容
def retrieve_relevant_context(query, top_k=2):
    try:
        query_embedding = sentence_model.encode([query])
        similarities = cosine_similarity(query_embedding, knowledge_embeddings)[0]
        top_indices = similarities.argsort()[-top_k:][::-1]
        return [knowledge_base[i] for i in top_indices]
    except Exception as e:
        logging.error(f"Error in retrieve_relevant_context: {e}")
        return []

# 生成回應的主要函數
def generate_response(query):
    start_time = datetime.datetime.now()
    try:
        relevant_context = retrieve_relevant_context(query)
        context_text = " ".join(relevant_context)

        messages = [
            {"role": "system", "content": "You are a helpful customer service assistant. Use the provided context to answer the user's question. If the context doesn't contain relevant information, use your general knowledge but mention that the information might not be specific to our company."},
            {"role": "user", "content": f"Context: {context_text}\n\nQuestion: {query}"}
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )

        raw_response = response.choices[0].message.content.strip()
        personalized_response, sentiment = analyze_sentiment_and_personalize(query, raw_response)

        if not active_learning_system.evaluate_certainty(query, raw_response):
            active_learning_system.add_uncertain_query(query, raw_response)

        end_time = datetime.datetime.now()
        response_time = (end_time - start_time).total_seconds()

        sentiment = sentiment_analyzer(query)[0]['label']
        topic = "General"  # 這裡可以添加主題分類邏輯

        analytics_system.log_interaction(query, response_time, sentiment, topic)

        return personalized_response
    except Exception as e:
        logging.error(f"Error in generate_response: {e}")
        return f"An error occurred: {str(e)}"

# Streamlit 應用
def main():
    st.title("Advanced RAG-Enhanced Customer Service Assistant")
    st.write("Ask any question related to our services or type 'Generate report' for analytics!")

    # 初始化聊天歷史
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # 顯示聊天歷史
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 獲取用戶輸入
    user_input = st.chat_input("Type your message here...")

    if user_input:
        # 添加用戶消息到歷史
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # 在聊天界面顯示用戶消息
        with st.chat_message("user"):
            st.markdown(user_input)

        # 生成回應
        if user_input.lower() == "generate report":
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            report, fig = analytics_system.generate_report(start_date, end_date)
            
            # 顯示報告
            with st.chat_message("assistant"):
                st.markdown(f"Here's the latest analytics report:\n\n{report}")
                st.pyplot(fig)
            
            # 添加助手回應到歷史
            st.session_state.chat_history.append({"role": "assistant", "content": f"Here's the latest analytics report:\n\n{report}"})
        else:
            response = generate_response(user_input)
            
            # 顯示助手回應
            with st.chat_message("assistant"):
                st.markdown(response)
            
            # 添加助手回應到歷史
            st.session_state.chat_history.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()