#!/usr/bin/env python3
"""
Rating to Grade Conversion Utility
Handles conversion between numeric ratings and letter grades for restaurants
"""

from typing import Optional, Dict, Any;

def rating_to_grade(rating: Optional[float]) -> Optional[str]:
    """
    Convert numeric rating to letter grade using school-like grading scale.
    
    Args:
        rating: Numeric rating on 1-5 scale
        
    Returns:
        Letter grade string (A+ through F) or None if rating is None
        
    Grade Scale:
        A+ = 4.6 - 5.0
        A  = 4.4 - 4.59
        A- = 4.2 - 4.39
        B+ = 4.0 - 4.19
        B  = 3.8 - 3.99
        B- = 3.6 - 3.79
        C+ = 3.4 - 3.59
        C  = 3.2 - 3.39
        C- = 3.0 - 3.19
        D  = 2.5 - 2.99
        F  = 0.0 - 2.49
    """
    if rating is None:
        return None;
        
    # Clamp rating to valid range
    rating = max( 0.0, min( 5.0, rating ) );
    
    if rating >= 4.6:
        return "A+";
    elif rating >= 4.4:
        return "A";
    elif rating >= 4.2:
        return "A-";
    elif rating >= 4.0:
        return "B+";
    elif rating >= 3.8:
        return "B";
    elif rating >= 3.6:
        return "B-";
    elif rating >= 3.4:
        return "C+";
    elif rating >= 3.2:
        return "C";
    elif rating >= 3.0:
        return "C-";
    elif rating >= 2.5:
        return "D";
    else:
        return "F";


def grade_to_color(grade: Optional[str]) -> str:
    """
    Get CSS color for grade display in emails.
    
    Args:
        grade: Letter grade (A+ through F)
        
    Returns:
        CSS color string
    """
    if not grade:
        return "#666666";  # Gray for missing grades
        
    grade_colors = {
        "A+": "#00a86b",  # Green
        "A": "#00a86b",
        "A-": "#228b22",
        "B+": "#32cd32",  # Light green
        "B": "#9acd32",   # Yellow-green
        "B-": "#ffff00",  # Yellow
        "C+": "#ffa500",  # Orange
        "C": "#ff8c00",
        "C-": "#ff6347",  # Orange-red
        "D": "#dc143c",   # Red
        "F": "#8b0000"    # Dark red
    };
    
    return grade_colors.get( grade, "#666666" );


def grade_to_gpa(grade: Optional[str]) -> Optional[float]:
    """
    Convert letter grade to GPA-style numeric value.
    
    Args:
        grade: Letter grade
        
    Returns:
        GPA value (0.0 - 4.0) or None
    """
    if not grade:
        return None;
        
    grade_gpa = {
        "A+": 4.0,
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D": 1.0,
        "F": 0.0
    };
    
    return grade_gpa.get( grade );


def get_grade_description(grade: Optional[str]) -> str:
    """
    Get descriptive text for a grade.
    
    Args:
        grade: Letter grade
        
    Returns:
        Descriptive text
    """
    if not grade:
        return "Rating unavailable";
        
    descriptions = {
        "A+": "Exceptional - Outstanding restaurant",
        "A": "Excellent - Highly recommended", 
        "A-": "Very Good - Great choice",
        "B+": "Good - Worth visiting",
        "B": "Above Average - Solid option",
        "B-": "Average - Decent restaurant",
        "C+": "Below Average - Mixed reviews",
        "C": "Poor - Limited appeal", 
        "C-": "Very Poor - Significant issues",
        "D": "Failing - Avoid if possible",
        "F": "Terrible - Major problems"
    };
    
    return descriptions.get( grade, "Unknown rating" );


def normalize_rating_for_training(rating: float) -> float:
    """
    Normalize rating from 1-5 scale to 0-1 scale for ML training.
    
    Args:
        rating: Rating on 1-5 scale
        
    Returns:
        Normalized rating on 0-1 scale
    """
    # Clamp to valid range and normalize
    rating = max( 1.0, min( 5.0, rating ) );
    return ( rating - 1.0 ) / 4.0;


def denormalize_rating_from_training(normalized_rating: float) -> float:
    """
    Convert normalized rating (0-1) back to 1-5 scale.
    
    Args:
        normalized_rating: Rating on 0-1 scale
        
    Returns:
        Rating on 1-5 scale
    """
    # Clamp to valid range and denormalize
    normalized_rating = max( 0.0, min( 1.0, normalized_rating ) );
    return normalized_rating * 4.0 + 1.0;


def get_grading_summary() -> Dict[str, Any]:
    """
    Get summary information about the grading system.
    
    Returns:
        Dictionary with grading system details
    """
    return {
        "scale": "1-5 star rating converted to letter grades",
        "grades": {
            "A+": "4.6 - 5.0 stars",
            "A": "4.4 - 4.59 stars", 
            "A-": "4.2 - 4.39 stars",
            "B+": "4.0 - 4.19 stars",
            "B": "3.8 - 3.99 stars",
            "B-": "3.6 - 3.79 stars",
            "C+": "3.4 - 3.59 stars",
            "C": "3.2 - 3.39 stars",
            "C-": "3.0 - 3.19 stars",
            "D": "2.5 - 2.99 stars",
            "F": "0.0 - 2.49 stars"
        },
        "description": "Grade scale follows academic standards with A+ being exceptional (4.6+ stars) and F being poor (under 2.5 stars)"
    };


# Testing and validation functions
if __name__ == "__main__":
    # Test the grading system
    test_ratings = [5.0, 4.7, 4.5, 4.3, 4.1, 3.9, 3.7, 3.5, 3.3, 3.1, 2.8, 2.0, 1.0];
    
    print( "Rating to Grade Conversion Test:" );
    print( "================================" );
    
    for rating in test_ratings:
        grade = rating_to_grade( rating );
        color = grade_to_color( grade );
        description = get_grade_description( grade );
        
        print( f"{rating:.1f} → {grade} (Color: {color})" );
        print( f"  Description: {description}" );
        print();
    
    # Test normalization
    print( "Normalization Test:" );
    print( "===================" );
    for rating in [1.0, 2.5, 3.0, 4.0, 5.0]:
        normalized = normalize_rating_for_training( rating );
        denormalized = denormalize_rating_from_training( normalized );
        print( f"{rating} → {normalized:.3f} → {denormalized:.3f}" );
    
    # Print grading summary
    print( "\nGrading System Summary:" );
    summary = get_grading_summary();
    for grade, range_str in summary["grades"].items():
        print( f"{grade}: {range_str}" );
