import json
from urllib.request import urlopen
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# API endpoints
HISTORICAL_API_ENDPOINT = "https://api.jsonserve.com/XgAgFJ"
SUBMISSION_API_ENDPOINT = "https://api.jsonserve.com/rJvd7g"
QUIZ_METADATA_API_ENDPOINT = "https://www.jsonkeeper.com/b/LLQT"

def load_api_data(endpoint):
    """Load JSON data from API endpoint."""
    try:
        with urlopen(endpoint) as response:
            data = json.loads(response.read().decode('utf-8'))
        return data
    except Exception as e:
        print(f"Error loading data from {endpoint}: {e}")
        return None

def process_data(data):
    """Process raw data into DataFrames."""
    if isinstance(data, list):
        df = pd.DataFrame.from_records(data)
        quiz_data = [item["quiz"] for item in data]
        quiz_df = pd.DataFrame(quiz_data)
    else:
        df = pd.DataFrame([data])
        quiz_data = [data["quiz"]] if "quiz" in data else []
        quiz_df = pd.DataFrame(quiz_data)
    return df, quiz_df

def filter_dataframes(df, quiz_df):
    """Filter and preprocess DataFrames."""
    # User performance metrics
    filtered_df = df.filter(items=[
        'score', 'trophy_level', 'accuracy', 'speed', 'final_score',
        'negative_score', 'correct_answers', 'incorrect_score', 'duration',
        'better_than', 'total_questions', 'rank_text', 'mistakes_corrected',
        'initial_mistake_count'
    ]).reset_index(drop=True)

    # Data type conversions
    filtered_df['accuracy'] = pd.to_numeric(filtered_df['accuracy'], errors='coerce').fillna(0)
    filtered_df['rank_text'] = pd.to_numeric(
        filtered_df['rank_text'].str.extract(r'(\d+)')[0],
        errors='coerce'
    ).fillna(0).astype(int)

    # Quiz metadata processing
    filtered_quiz_df = quiz_df.filter(items=[
        'difficulty_level', 'topic', 'duration', 'negative_marks',
        'correct_answer_marks', 'max_mistake_count', 'created_at',
        'updated_at'
    ]).reset_index(drop=True)

    # Rename quiz columns to avoid conflicts
    filtered_quiz_df = filtered_quiz_df.rename(columns={
        'duration': 'quiz_duration',
        'negative_marks': 'quiz_negative_marks',
        'correct_answer_marks': 'quiz_correct_marks',
        'max_mistake_count': 'quiz_max_mistakes',
        'created_at': 'quiz_created_at',
        'updated_at': 'quiz_updated_at'
    })

    # DateTime conversions
    filtered_quiz_df['quiz_created_at'] = pd.to_datetime(filtered_quiz_df['quiz_created_at'], errors='coerce')
    filtered_quiz_df['quiz_updated_at'] = pd.to_datetime(filtered_quiz_df['quiz_updated_at'], errors='coerce')
    filtered_quiz_df['timestamp'] = (
        (filtered_quiz_df['quiz_updated_at'] - filtered_quiz_df['quiz_created_at'])
        .dt.total_seconds() / 60.0
    ).fillna(0)

    # Convert duration to seconds
    filtered_quiz_df['quiz_duration'] = pd.to_numeric(filtered_quiz_df['quiz_duration'], errors='coerce') * 60

    return filtered_df, filtered_quiz_df

def visualize_performance_chain(filtered_df):
    """Visualize key performance metrics with enhanced formatting."""
    plt.figure(figsize=(14, 10))
    
    # Create subplot grid
    grid = plt.GridSpec(2, 2, hspace=0.4, wspace=0.3)
    
    # Plot 1: Accuracy Distribution
    ax1 = plt.subplot(grid[0, 0])
    sns.histplot(filtered_df['accuracy'], bins=20, kde=True, ax=ax1)
    ax1.set_title('Accuracy Distribution\n(How precise were the answers?)')
    ax1.set_xlabel('Accuracy Percentage')
    ax1.set_ylabel('Number of Attempts')
    
    # Plot 2: Score vs Correct Answers
    ax2 = plt.subplot(grid[0, 1])
    sns.scatterplot(
        data=filtered_df,
        x='correct_answers',
        y='score',
        hue='rank_text',
        palette='viridis',
        size='initial_mistake_count',
        ax=ax2
    )
    ax2.set_title('Score vs Correct Answers\n(Impact of Mistakes on Final Score)')
    ax2.set_xlabel('Correct Answers')
    ax2.set_ylabel('Total Score')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Plot 3: Topic Performance Comparison
    ax3 = plt.subplot(grid[1, :])
    topic_metrics = filtered_df.groupby('topic').agg({
        'score': 'mean',
        'accuracy': 'mean',
        'correct_answers': 'mean'
    }).reset_index()
    
    # Melt for easier plotting
    melted_metrics = topic_metrics.melt(id_vars='topic', var_name='metric', value_name='value')
    
    sns.barplot(
        data=melted_metrics,
        x='topic',
        y='value',
        hue='metric',
        palette='coolwarm',
        ax=ax3
    )
    ax3.set_title('Topic-wise Performance Comparison\n(Across Multiple Metrics)')
    ax3.set_xlabel('Quiz Topics')
    ax3.set_ylabel('Average Value')
    ax3.tick_params(axis='x', rotation=45)
    ax3.legend(title='Metrics', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.show()

def analyze_topic_performance(merged_df):
    """Analyze and display topic performance with formatted output."""
    print("\n" + "="*60)
    print(" Detailed Topic Performance Analysis ".center(60, '='))
    print("="*60)
    
    # Calculate topic metrics
    topic_metrics = merged_df.groupby('topic').agg({
        'score': ['mean', 'max', 'min'],
        'accuracy': 'mean',
        'correct_answers': 'mean',
        'quiz_negative_marks': 'mean',
        'quiz_correct_marks': 'mean',
        'quiz_duration': 'mean'
    }).reset_index()
    
    # Formatting for display
    topic_metrics.columns = ['_'.join(col).strip() if col[1] else col[0] 
                           for col in topic_metrics.columns.values]
    
    # Print analysis for each topic
    for _, row in topic_metrics.iterrows():
        print(f"\n📚 Topic: {row['topic']}")
        print(f"  ➤ Average Score: {row['score_mean']:.2f} "
              f"(High: {row['score_max']:.2f}, Low: {row['score_min']:.2f})")
        print(f"  ➤ Accuracy: {row['accuracy_mean']:.2f}%")
        print(f"  ➤ Correct Answers: {row['correct_answers_mean']:.2f}")
        print(f"  ➤ Negative Mark Impact: {row['quiz_negative_marks_mean']:.2f}")
        print(f"  ➤ Average Question Value: {row['quiz_correct_marks_mean']:.2f} points")
        print(f"  ➤ Typical Duration: {row['quiz_duration_mean']/60:.2f} minutes")
        print("-"*60)
    
    return topic_metrics

# reocmmendation system logic for recommendation function
"""
use the topic name and score of the submission API point 
to compare with historical trend
create the function to store the topic list
if the score and accuracy is higher than the 60 :: the topic is recommended as strong topic
if the score and accuracy is lower than the 60 :: the topic is recommended as weak topic


use the topic name and score of the submission API point

return the topicrecommendation


"""
def main():
    """Main workflow with enhanced error handling."""
    # Load and process data
    historical_data = load_api_data(HISTORICAL_API_ENDPOINT)
    submission_data = load_api_data(SUBMISSION_API_ENDPOINT)
    
    # Process historical data
    hist_df, hist_quiz_df = process_data(historical_data)
    filtered_hist_df, filtered_hist_quiz_df = filter_dataframes(hist_df, hist_quiz_df)
    
    # Create merged dataset for analysis
    merged_historical = pd.concat([filtered_hist_df, filtered_hist_quiz_df], axis=1)
    
    # Generate visualizations
    visualize_performance_chain(merged_historical)
    
    # Detailed topic analysis
    topic_metrics = analyze_topic_performance(merged_historical)
    
    # Additional performance insights
    print("\n" + "="*60)
    print(" Key Performance Indicators ".center(60, '='))
    print("="*60)
    print(f"🏆 Overall Accuracy: {merged_historical['accuracy'].mean():.2f}%")
    print(f"🚀 Average Speed: {merged_historical['speed'].mean():.2f}")
    print(f"💡 Best Performing Topic: {topic_metrics.loc[topic_metrics['score_mean'].idxmax(), 'topic']}")
    print(f"🔧 Most Challenging Topic: {topic_metrics.loc[topic_metrics['score_mean'].idxmin(), 'topic']}")
    print("="*60)

if __name__ == "__main__":
    main()
