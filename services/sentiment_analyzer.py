#!/usr/bin/env python3
"""
Sentiment Analysis Service for Restaurant Reviews
Provides sentiment analysis and keyword extraction for Google Places reviews
"""

import logging;
import re;
from typing import Dict, List, Tuple, Optional, Any;
from collections import Counter;
from datetime import datetime;

try:
    from textblob import TextBlob;
    TEXTBLOB_AVAILABLE = True;
except ImportError:
    print( "TextBlob is not installed. Please install it using 'pip install textblob'." );
    TEXTBLOB_AVAILABLE = False;

try:
    import nltk;
    NLTK_AVAILABLE = True;
except ImportError:
    print( "NLTK is not installed. Please install it using 'pip install nltk'." );
    NLTK_AVAILABLE = False;

logger = logging.getLogger( __name__ );

class SentimentAnalyzer:
    """Service for analyzing restaurant review sentiment and extracting keywords."""
    
    def __init__(self, method: str = 'textblob'):
        """
        Initialize sentiment analyzer.
        
        Args:
            method: Analysis method ('textblob' or 'vader')
        """
        self.method = method;
        self.initialized = False;
        
        if not TEXTBLOB_AVAILABLE:
            raise ImportError( "TextBlob is required. Install with: pip install textblob" );
            
        self._initialize_nltk_data();
        
        # Restaurant-specific keyword categories
        self.food_keywords = {
            'positive': ['delicious', 'tasty', 'amazing', 'excellent', 'perfect', 'fresh', 'flavorful', 'incredible', 'outstanding', 'wonderful'],
            'negative': ['terrible', 'awful', 'disgusting', 'bland', 'stale', 'overcooked', 'undercooked', 'burnt', 'salty', 'dry']
        };
        
        self.service_keywords = {
            'positive': ['friendly', 'attentive', 'helpful', 'professional', 'quick', 'efficient', 'courteous', 'welcoming', 'responsive'],
            'negative': ['rude', 'slow', 'unfriendly', 'unprofessional', 'dismissive', 'ignored', 'waited', 'forever', 'terrible service']
        };
        
        self.atmosphere_keywords = {
            'positive': ['cozy', 'atmosphere', 'ambiance', 'comfortable', 'nice decor', 'clean', 'spacious', 'beautiful', 'relaxing'],
            'negative': ['noisy', 'crowded', 'dirty', 'uncomfortable', 'outdated', 'cramped', 'loud', 'messy']
        };
        
        # Common restaurant aspects
        self.aspect_keywords = {
            'food_quality': ['food', 'dish', 'meal', 'cuisine', 'flavor', 'taste', 'recipe', 'cooking'],
            'service': ['service', 'staff', 'server', 'waiter', 'waitress', 'employee', 'team'],
            'atmosphere': ['atmosphere', 'ambiance', 'decor', 'environment', 'setting', 'vibe'],
            'value': ['price', 'cost', 'expensive', 'cheap', 'value', 'worth', 'money', 'affordable'],
            'location': ['location', 'parking', 'accessible', 'convenient', 'neighborhood'],
            'cleanliness': ['clean', 'sanitary', 'hygienic', 'tidy', 'spotless', 'dirty', 'messy']
        };
        
        self.initialized = True;
        logger.info( f"Sentiment analyzer initialized with method: {method}" );
        
    def _initialize_nltk_data(self):
        """Initialize required NLTK data."""
        if not NLTK_AVAILABLE:
            return;
            
        try:
            # Download required NLTK data if not present
            nltk.data.find( 'tokenizers/punkt' );
        except LookupError:
            logger.info( "Downloading NLTK punkt tokenizer..." );
            nltk.download( 'punkt', quiet=True );
            
        try:
            nltk.data.find( 'corpora/stopwords' );
        except LookupError:
            logger.info( "Downloading NLTK stopwords..." );
            nltk.download( 'stopwords', quiet=True );
            
    def analyze_text(self, text: str) -> Tuple[float, str]:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (sentiment_score, sentiment_label)
            sentiment_score: -1.0 (very negative) to 1.0 (very positive)
            sentiment_label: 'positive', 'negative', or 'neutral'
        """
        if not text or not text.strip():
            return 0.0, 'neutral';
            
        try:
            # Clean text
            cleaned_text = self._clean_text( text );
            
            # Use TextBlob for sentiment analysis
            blob = TextBlob( cleaned_text );
            polarity = blob.sentiment.polarity;  # -1 to 1
            
            # Determine label based on polarity
            if polarity > 0.1:
                label = 'positive';
            elif polarity < -0.1:
                label = 'negative';
            else:
                label = 'neutral';
                
            return round( polarity, 3 ), label;
            
        except Exception as e:
            logger.warning( f"Error analyzing text sentiment: {e}" );
            return 0.0, 'neutral';
            
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for analysis."""
        if not text:
            return "";
            
        # Remove extra whitespace and newlines
        text = re.sub( r'\s+', ' ', text ).strip();
        
        # Remove URLs
        text = re.sub( r'http[s]?://\S+', '', text );
        
        # Remove email addresses  
        text = re.sub( r'\S+@\S+', '', text );
        
        # Remove excessive punctuation
        text = re.sub( r'[!]{2,}', '!', text );
        text = re.sub( r'[?]{2,}', '?', text );
        
        return text;
        
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        Extract important keywords from review text.
        
        Args:
            text: Review text
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of important keywords/phrases
        """
        if not text or not text.strip():
            return [];
            
        try:
            # Clean text
            cleaned_text = self._clean_text( text ).lower();
            
            # Find restaurant aspect mentions
            found_aspects = [];
            
            for aspect, keywords in self.aspect_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in cleaned_text:
                        found_aspects.append( aspect.replace( '_', ' ' ) );
                        break;  # Only add aspect once
            
            # Find specific positive/negative food keywords
            found_descriptors = [];
            
            for sentiment, keywords in self.food_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in cleaned_text:
                        found_descriptors.append( f"{keyword} food" );
                        
            for sentiment, keywords in self.service_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in cleaned_text:
                        found_descriptors.append( f"{keyword} service" );
            
            # Combine and prioritize
            all_keywords = found_aspects + found_descriptors;
            
            # Remove duplicates while preserving order
            unique_keywords = [];
            seen = set();
            for keyword in all_keywords:
                if keyword not in seen:
                    unique_keywords.append( keyword );
                    seen.add( keyword );
            
            return unique_keywords[:max_keywords];
            
        except Exception as e:
            logger.warning( f"Error extracting keywords: {e}" );
            return [];
            
    def analyze_reviews(self, reviews: List[Dict]) -> Dict[str, Any]:
        """
        Analyze multiple reviews and provide comprehensive insights.
        
        Args:
            reviews: List of review dictionaries from Google Places
            
        Returns:
            Dictionary with sentiment analysis results
        """
        if not reviews:
            return {
                'reviews_analyzed': [],
                'sentiment_avg': 0.0,
                'sentiment_distribution': { 'positive': 0, 'neutral': 0, 'negative': 0 },
                'top_keywords': [],
                'analysis_summary': 'No reviews available',
                'last_analyzed': datetime.now().isoformat()
            };
            
        analyzed_reviews = [];
        sentiment_scores = [];
        sentiment_labels = [];
        all_keywords = [];
        
        # Analyze each review
        for i, review in enumerate( reviews[:5] ):  # Max 5 reviews from Google
            text = review.get( 'text', '' );
            rating = review.get( 'rating', 0 );
            author = review.get( 'author_name', f'User {i+1}' );
            time_desc = review.get( 'relative_time_description', 'recently' );
            
            # Perform sentiment analysis
            sentiment_score, sentiment_label = self.analyze_text( text );
            
            # Extract keywords
            keywords = self.extract_keywords( text, max_keywords=3 );
            
            # Store analyzed review
            analyzed_review = {
                'text': text[:200] + ('...' if len( text ) > 200 else ''),  # Truncate for storage
                'rating': rating,
                'sentiment_score': sentiment_score,
                'sentiment_label': sentiment_label,
                'keywords': keywords,
                'author': author[:20],  # Truncate author name
                'time_description': time_desc
            };
            
            analyzed_reviews.append( analyzed_review );
            sentiment_scores.append( sentiment_score );
            sentiment_labels.append( sentiment_label );
            all_keywords.extend( keywords );
            
        # Calculate aggregate metrics
        avg_sentiment = sum( sentiment_scores ) / len( sentiment_scores ) if sentiment_scores else 0.0;
        
        # Count sentiment distribution
        label_counts = Counter( sentiment_labels );
        total_reviews = len( sentiment_labels );
        sentiment_distribution = {
            'positive': round( (label_counts.get( 'positive', 0 ) / total_reviews) * 100 ) if total_reviews > 0 else 0,
            'neutral': round( (label_counts.get( 'neutral', 0 ) / total_reviews) * 100 ) if total_reviews > 0 else 0,
            'negative': round( (label_counts.get( 'negative', 0 ) / total_reviews) * 100 ) if total_reviews > 0 else 0
        };
        
        # Get top keywords
        keyword_counts = Counter( all_keywords );
        top_keywords = [keyword for keyword, count in keyword_counts.most_common( 5 )];
        
        # Generate analysis summary
        analysis_summary = self._generate_summary( sentiment_distribution, top_keywords, avg_sentiment );
        
        return {
            'reviews_analyzed': analyzed_reviews,
            'sentiment_avg': round( avg_sentiment, 3 ),
            'sentiment_distribution': sentiment_distribution,
            'top_keywords': top_keywords,
            'analysis_summary': analysis_summary,
            'reviews_count': len( analyzed_reviews ),
            'last_analyzed': datetime.now().isoformat()
        };
        
    def _generate_summary(self, sentiment_dist: Dict[str, int], keywords: List[str], avg_sentiment: float) -> str:
        """Generate a human-readable summary of the review analysis."""
        if not sentiment_dist or sum( sentiment_dist.values() ) == 0:
            return "No reviews available for analysis";
            
        # Determine overall sentiment
        if avg_sentiment > 0.3:
            overall = "Generally Positive";
        elif avg_sentiment > -0.1:
            overall = "Mixed Reviews";
        else:
            overall = "Generally Negative";
            
        # Highlight dominant sentiment
        dominant_sentiment = max( sentiment_dist.items(), key=lambda x: x[1] );
        
        # Include top keywords
        keyword_text = ", ".join( keywords[:3] ) if keywords else "various aspects";
        
        return f"{overall} ({dominant_sentiment[0]} {dominant_sentiment[1]}%) - Key topics: {keyword_text}";
        
    def get_sentiment_badge_info(self, sentiment_distribution: Dict[str, int]) -> Dict[str, str]:
        """
        Get display information for sentiment badges in emails.
        
        Args:
            sentiment_distribution: Percentage distribution of sentiments
            
        Returns:
            Dictionary with badge text, emoji, and CSS class
        """
        if not sentiment_distribution or sum( sentiment_distribution.values() ) == 0:
            return {
                'text': 'Reviews Pending',
                'emoji': '⏳',
                'css_class': 'sentiment-pending'
            };
            
        positive_pct = sentiment_distribution.get( 'positive', 0 );
        negative_pct = sentiment_distribution.get( 'negative', 0 );
        
        if positive_pct >= 60:
            return {
                'text': f'Positive Reviews ({positive_pct}%)',
                'emoji': '😊',
                'css_class': 'sentiment-positive'
            };
        elif negative_pct >= 40:
            return {
                'text': f'Mixed Reviews ({positive_pct}% pos)',
                'emoji': '😐',
                'css_class': 'sentiment-mixed'
            };
        elif negative_pct >= 60:
            return {
                'text': f'Negative Reviews ({negative_pct}%)',
                'emoji': '😞',
                'css_class': 'sentiment-negative'
            };
        else:
            return {
                'text': f'Mixed Reviews ({positive_pct}% pos)',
                'emoji': '😐', 
                'css_class': 'sentiment-mixed'
            };


# Testing and example usage
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO );
    
    if not TEXTBLOB_AVAILABLE:
        print( "TextBlob not available, skipping tests." );
        exit( 1 );
        
    # Test sentiment analyzer
    analyzer = SentimentAnalyzer();
    
    # Test reviews (simulating Google Places format)
    test_reviews = [
        {
            'text': 'Amazing food and excellent service! The pasta was delicious and the staff was very friendly. Highly recommend!',
            'rating': 5,
            'author_name': 'John Smith',
            'relative_time_description': '2 weeks ago'
        },
        {
            'text': 'Food was okay but the service was really slow. Waited 45 minutes for our meals. Not impressed.',
            'rating': 2,
            'author_name': 'Sarah Johnson', 
            'relative_time_description': '1 month ago'
        },
        {
            'text': 'Great atmosphere and the pizza was fantastic. Clean restaurant with good parking too.',
            'rating': 4,
            'author_name': 'Mike Davis',
            'relative_time_description': '3 weeks ago'
        }
    ];
    
    print( "Testing Sentiment Analysis..." );
    print( "=" * 40 );
    
    # Test individual text analysis
    for review in test_reviews:
        score, label = analyzer.analyze_text( review['text'] );
        keywords = analyzer.extract_keywords( review['text'] );
        print( f"Text: {review['text'][:50]}..." );
        print( f"Rating: {review['rating']} | Sentiment: {label} ({score:.2f})" );
        print( f"Keywords: {keywords}" );
        print();
    
    # Test comprehensive review analysis
    print( "Comprehensive Analysis:" );
    print( "=" * 40 );
    
    analysis = analyzer.analyze_reviews( test_reviews );
    
    print( f"Reviews analyzed: {analysis['reviews_count']}" );
    print( f"Average sentiment: {analysis['sentiment_avg']:.3f}" );
    print( f"Sentiment distribution: {analysis['sentiment_distribution']}" );
    print( f"Top keywords: {analysis['top_keywords']}" );
    print( f"Summary: {analysis['analysis_summary']}" );
    
    # Test badge info
    badge_info = analyzer.get_sentiment_badge_info( analysis['sentiment_distribution'] );
    print( f"Badge: {badge_info['emoji']} {badge_info['text']}" );
