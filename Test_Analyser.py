import json
from urllib.request import urlopen
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai

# Configure the Gemini API
genai.configure(api_key="AIzaSyCRL2KT5KI2m44gW7ruRLyErZD0YmdbBlA")
model = genai.GenerativeModel("gemini-1.5-flash")

# API endpoints
HISTORICAL_API_ENDPOINT = "https://api.jsonserve.com/XgAgFJ"
SUBMISSION_API_ENDPOINT = "https://api.jsonserve.com/rJvd7g"

def load_api_data(endpoint):
    """Load JSON data from an API endpoint."""
    try:
        with urlopen(endpoint) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def process_data(data):
    """Process raw data into structured DataFrames."""
    if isinstance(data, list):
        df = pd.DataFrame(data)
        quiz_df = pd.DataFrame([item["quiz"] for item in data])
    else:
        df = pd.DataFrame([data])
        quiz_df = pd.DataFrame([data["quiz"]]) if "quiz" in data else pd.DataFrame()
    return df, quiz_df

def parse_duration(duration):
    """Convert duration string to total seconds."""
    try:
        if isinstance(duration, str) and ':' in duration:
            parts = list(map(int, duration.split(':')))
            if len(parts) == 2:  # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:  # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return float(duration) * 60  # Assume minutes if numeric
    except ValueError:
        return 0  # Return 0 for invalid formats

def filter_dataframes(df, quiz_df):
    """Clean and transform data with proper type conversions."""
    # User metrics processing
    user_df = df[['score', 'accuracy', 'correct_answers', 'rank_text']].copy()
    user_df['accuracy'] = pd.to_numeric(user_df['accuracy'], errors='coerce').fillna(0)
    user_df['rank'] = user_df['rank_text'].str.extract(r'(\d+)').astype(float).fillna(0).astype(int)
    
    # Quiz metrics processing
    quiz_df = quiz_df[['topic', 'duration']].copy()
    quiz_df['duration_seconds'] = quiz_df['duration'].apply(parse_duration)
    
    return user_df.reset_index(drop=True), quiz_df.reset_index(drop=True)

def analyze_topic_performance(merged_df):
    """Generate a comprehensive topic performance report."""
    analysis = merged_df.groupby('topic').agg(
        attempts=('score', 'count'),
        avg_score=('score', 'mean'),
        avg_accuracy=('accuracy', 'mean'),
        avg_duration=('duration_seconds', 'mean')
    ).reset_index()
    return analysis

def display_topic_performance(performance_report):
    """Display weak and strong topics based on average scores."""
    print("\n📋 Topic Performance Summary:")
    print("______Weak Topics______")
    weak_topics = performance_report[performance_report['avg_score'] < 60]
    for _, row in weak_topics.iterrows():
        print(f"\n📊 Topic: {row['topic']}")
        print(f"   🔢 Attempts: {row['attempts']}")
        print(f"   🎯 Average Score: {row['avg_score']:.2f}")

    print("\n______Strong Topics______")
    strong_topics = performance_report[performance_report['avg_score'] >= 60]
    for _, row in strong_topics.iterrows():
        print(f"\n📊 Topic: {row['topic']}")
        print(f"   🔢 Attempts: {row['attempts']}")
        print(f"   🎯 Average Score: {row['avg_score']:.2f}")
    return weak_topics, strong_topics

def generate_improvement_suggestions(weak_topics, strong_topics, merged_df):
    """Generate improvement suggestions using Gemini API."""
    prompt = f"""
    Role: You are a test assessment analyzer and mentor for NEET students.
    Context: The student's performance report is summarized below.
    
    Weak Topics:
    {weak_topics.to_string(index=False)}
    
    Strong Topics:
    {strong_topics.to_string(index=False)}
    
    Additional Information:
    - Average duration and timestamps of quizzes are available.
    - Provide time management strategies and improvement suggestions.
    """
    try:
        response = model.generate_content(prompt)
        print("\n📋 Actionable Improvement Suggestions:")
        print(response.text)
    except Exception as e:
        print(f"Error generating suggestions: {e}")

def main():
    """Main analysis workflow."""
   
    historical_data = load_api_data(HISTORICAL_API_ENDPOINT)
    user_df, quiz_df = process_data(historical_data)
    
    clean_user, clean_quiz = filter_dataframes(user_df, quiz_df)
    
    merged_data = pd.concat([clean_user, clean_quiz], axis=1)
    
    performance_report = analyze_topic_performance(merged_data)
    
    weak_topics, strong_topics = display_topic_performance(performance_report)
    
    generate_improvement_suggestions(weak_topics, strong_topics, merged_data)
    
    # viewing the insights
    best_topic = performance_report.loc[performance_report['avg_score'].idxmax()]
    print(f"\n🏆 Best Performing Topic: {best_topic['topic']}")
    print(f"   Average Score: {best_topic['avg_score']:.2f}")
    print(f"   Attempts: {best_topic['attempts']}")

if __name__ == "__main__":
    main()





