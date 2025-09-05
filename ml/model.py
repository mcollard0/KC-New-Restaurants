#!/usr/bin/env python3
"""
Restaurant Rating Prediction Model
PyTorch neural network for predicting restaurant ratings based on features
"""

import os;
import logging;
from typing import Dict, List, Optional, Tuple, Any;
import numpy as np;

try:
    import torch;
    import torch.nn as nn;
    import torch.optim as optim;
    from torch.utils.data import Dataset, DataLoader;
    TORCH_AVAILABLE = True;
except ImportError:
    print( "PyTorch is not installed. Please install it using 'pip install torch'." );
    TORCH_AVAILABLE = False;

try:
    import pandas as pd;
    PANDAS_AVAILABLE = True;
except ImportError:
    print( "Pandas is not installed. Please install it using 'pip install pandas'." );
    PANDAS_AVAILABLE = False;

try:
    from sklearn.preprocessing import StandardScaler, LabelEncoder;
    from sklearn.model_selection import train_test_split;
    SKLEARN_AVAILABLE = True;
except ImportError:
    print( "Scikit-learn is not installed. Please install it using 'pip install scikit-learn'." );
    SKLEARN_AVAILABLE = False;

from .grading import normalize_rating_for_training, denormalize_rating_from_training, rating_to_grade;

logger = logging.getLogger( __name__ );

class RestaurantDataset(Dataset):
    """PyTorch Dataset for restaurant data."""
    
    def __init__(self, features: np.ndarray, targets: Optional[np.ndarray] = None):
        """
        Initialize dataset.
        
        Args:
            features: Feature matrix (N x feature_dim)
            targets: Target ratings (N,) - optional for inference
        """
        if not TORCH_AVAILABLE:
            raise ImportError( "PyTorch is required but not installed" );
            
        self.features = torch.FloatTensor( features );
        self.targets = torch.FloatTensor( targets ) if targets is not None else None;
        
    def __len__(self) -> int:
        return len( self.features );
        
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        if self.targets is not None:
            return self.features[idx], self.targets[idx];
        else:
            return self.features[idx], None;


class RestaurantRatingPredictor(nn.Module):
    """
    Neural network for predicting restaurant ratings.
    
    Architecture:
    - Input layer: Variable size based on features
    - Hidden layers: 128 -> 64 -> 32 neurons with ReLU activation
    - Dropout layers for regularization
    - Output: Single value (0-1 range, scaled to 1-5 rating)
    """
    
    def __init__(self, input_dim: int, dropout_rate: float = 0.3):
        """
        Initialize the model.
        
        Args:
            input_dim: Number of input features
            dropout_rate: Dropout rate for regularization
        """
        super( RestaurantRatingPredictor, self ).__init__();
        
        self.input_dim = input_dim;
        self.dropout_rate = dropout_rate;
        
        self.network = nn.Sequential(
            nn.Linear( input_dim, 128 ),
            nn.ReLU(),
            nn.Dropout( dropout_rate ),
            
            nn.Linear( 128, 64 ),
            nn.ReLU(), 
            nn.Dropout( dropout_rate * 0.7 ),  # Reduce dropout in deeper layers
            
            nn.Linear( 64, 32 ),
            nn.ReLU(),
            nn.Dropout( dropout_rate * 0.5 ),
            
            nn.Linear( 32, 16 ),
            nn.ReLU(),
            
            nn.Linear( 16, 1 ),
            nn.Sigmoid()  # Output 0-1, will be scaled to 1-5 rating
        );
        
        # Initialize weights
        self._initialize_weights();
        
    def _initialize_weights(self):
        """Initialize model weights using Xavier initialization."""
        for module in self.modules():
            if isinstance( module, nn.Linear ):
                nn.init.xavier_uniform_( module.weight );
                if module.bias is not None:
                    nn.init.constant_( module.bias, 0 );
                    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the network."""
        return self.network( x );
        
    def predict_rating(self, features: torch.Tensor) -> torch.Tensor:
        """
        Predict rating and convert from 0-1 scale back to 1-5 scale.
        
        Args:
            features: Input features tensor
            
        Returns:
            Predicted ratings on 1-5 scale
        """
        self.eval();
        with torch.no_grad():
            normalized_predictions = self.forward( features );
            # Convert from 0-1 scale back to 1-5 scale
            predictions = normalized_predictions * 4.0 + 1.0;
            return predictions;


class ModelTrainer:
    """Handles training, validation, and model persistence."""
    
    def __init__(self, model: RestaurantRatingPredictor, device: Optional[str] = None):
        """
        Initialize trainer.
        
        Args:
            model: The model to train
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        if not TORCH_AVAILABLE:
            raise ImportError( "PyTorch is required but not installed" );
            
        self.model = model;
        
        # Device selection with fallback
        if device is None:
            self.device = torch.device( 'cuda' if torch.cuda.is_available() else 'cpu' );
        else:
            self.device = torch.device( device );
            
        logger.info( f"Using device: {self.device}" );
        
        # Move model to device
        self.model.to( self.device );
        
        # Training components
        self.criterion = nn.MSELoss();
        self.optimizer = optim.Adam( self.model.parameters(), lr=0.001, weight_decay=1e-5 );
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau( 
            self.optimizer, mode='min', factor=0.5, patience=10, verbose=True 
        );
        
        # Training history
        self.train_losses = [];
        self.val_losses = [];
        self.best_val_loss = float( 'inf' );
        self.best_model_state = None;
        
    def train_epoch(self, train_loader: DataLoader) -> float:
        """Train for one epoch."""
        self.model.train();
        total_loss = 0.0;
        num_batches = 0;
        
        for features, targets in train_loader:
            if targets is None:
                continue;  # Skip batches without targets
                
            features, targets = features.to( self.device ), targets.to( self.device );
            
            # Zero gradients
            self.optimizer.zero_grad();
            
            # Forward pass
            predictions = self.model( features );
            loss = self.criterion( predictions.squeeze(), targets );
            
            # Backward pass
            loss.backward();
            
            # Gradient clipping to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_( self.model.parameters(), max_norm=1.0 );
            
            self.optimizer.step();
            
            total_loss += loss.item();
            num_batches += 1;
            
        return total_loss / max( num_batches, 1 );
        
    def validate_epoch(self, val_loader: DataLoader) -> float:
        """Validate for one epoch."""
        self.model.eval();
        total_loss = 0.0;
        num_batches = 0;
        
        with torch.no_grad():
            for features, targets in val_loader:
                if targets is None:
                    continue;
                    
                features, targets = features.to( self.device ), targets.to( self.device );
                
                predictions = self.model( features );
                loss = self.criterion( predictions.squeeze(), targets );
                
                total_loss += loss.item();
                num_batches += 1;
                
        return total_loss / max( num_batches, 1 );
        
    def train(self, train_loader: DataLoader, val_loader: DataLoader, epochs: int = 100, 
              early_stop_patience: int = 20, save_path: Optional[str] = None) -> Dict[str, List[float]]:
        """
        Train the model.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader  
            epochs: Maximum number of epochs
            early_stop_patience: Early stopping patience
            save_path: Path to save best model
            
        Returns:
            Training history dictionary
        """
        logger.info( f"Starting training for {epochs} epochs on {self.device}" );
        
        patience_counter = 0;
        
        for epoch in range( epochs ):
            # Training phase
            train_loss = self.train_epoch( train_loader );
            val_loss = self.validate_epoch( val_loader );
            
            # Learning rate scheduling
            self.scheduler.step( val_loss );
            
            # Record losses
            self.train_losses.append( train_loss );
            self.val_losses.append( val_loss );
            
            # Check for best model
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss;
                self.best_model_state = self.model.state_dict().copy();
                patience_counter = 0;
                
                # Save best model
                if save_path:
                    self.save_model( save_path );
                    
                logger.info( f"Epoch {epoch+1}/{epochs}: Train Loss: {train_loss:.4f}, "
                           f"Val Loss: {val_loss:.4f} (Best)" );
            else:
                patience_counter += 1;
                logger.info( f"Epoch {epoch+1}/{epochs}: Train Loss: {train_loss:.4f}, "
                           f"Val Loss: {val_loss:.4f}" );
            
            # Early stopping
            if patience_counter >= early_stop_patience:
                logger.info( f"Early stopping after {epoch+1} epochs" );
                break;
                
        # Load best model
        if self.best_model_state is not None:
            self.model.load_state_dict( self.best_model_state );
            
        return {
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss
        };
        
    def save_model(self, file_path: str, include_metadata: bool = True):
        """
        Save model to disk.
        
        Args:
            file_path: Path to save the model
            include_metadata: Include training metadata
        """
        save_dict = {
            'model_state_dict': self.best_model_state or self.model.state_dict(),
            'input_dim': self.model.input_dim,
            'dropout_rate': self.model.dropout_rate,
        };
        
        if include_metadata:
            save_dict.update( {
                'train_losses': self.train_losses,
                'val_losses': self.val_losses,
                'best_val_loss': self.best_val_loss,
                'device': str( self.device )
            } );
        
        torch.save( save_dict, file_path );
        logger.info( f"Model saved to {file_path}" );
        
    @staticmethod
    def load_model(file_path: str, device: Optional[str] = None) -> Tuple[RestaurantRatingPredictor, Dict]:
        """
        Load model from disk.
        
        Args:
            file_path: Path to the saved model
            device: Device to load model on
            
        Returns:
            Tuple of (model, metadata)
        """
        if not TORCH_AVAILABLE:
            raise ImportError( "PyTorch is required but not installed" );
            
        # Auto-detect device if not specified
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu';
            
        checkpoint = torch.load( file_path, map_location=device );
        
        # Create model with saved parameters
        model = RestaurantRatingPredictor(
            input_dim=checkpoint['input_dim'],
            dropout_rate=checkpoint.get( 'dropout_rate', 0.3 )
        );
        
        # Load state dict
        model.load_state_dict( checkpoint['model_state_dict'] );
        model.to( device );
        model.eval();
        
        # Extract metadata
        metadata = {
            'train_losses': checkpoint.get( 'train_losses', [] ),
            'val_losses': checkpoint.get( 'val_losses', [] ),
            'best_val_loss': checkpoint.get( 'best_val_loss', None ),
            'device': device
        };
        
        logger.info( f"Model loaded from {file_path} on {device}" );
        return model, metadata;


def predict_restaurant_rating(model: RestaurantRatingPredictor, features: np.ndarray,
                            confidence_threshold: float = 0.0) -> List[Dict[str, Any]]:
    """
    Predict ratings for restaurants and return structured results.
    
    Args:
        model: Trained model
        features: Feature matrix for prediction
        confidence_threshold: Minimum confidence threshold
        
    Returns:
        List of prediction dictionaries
    """
    if not TORCH_AVAILABLE:
        raise ImportError( "PyTorch is required but not installed" );
        
    model.eval();
    
    with torch.no_grad():
        features_tensor = torch.FloatTensor( features ).to( next( model.parameters() ).device );
        predictions = model.predict_rating( features_tensor );
        
        # Convert to numpy for processing
        predictions_np = predictions.cpu().numpy();
        
        results = [];
        for i, rating in enumerate( predictions_np ):
            rating_float = float( rating );
            grade = rating_to_grade( rating_float );
            
            # Simple confidence estimation (distance from decision boundaries)
            # More sophisticated methods could be implemented later
            confidence = min( 1.0, 1.0 - abs( rating_float - 3.0 ) / 2.0 );
            
            result = {
                'predicted_rating': round( rating_float, 2 ),
                'predicted_grade': grade,
                'confidence': round( confidence, 3 ),
                'meets_threshold': confidence >= confidence_threshold
            };
            
            results.append( result );
            
        return results;


def get_model_info(model: RestaurantRatingPredictor) -> Dict[str, Any]:
    """
    Get information about the model architecture and parameters.
    
    Args:
        model: The model to inspect
        
    Returns:
        Model information dictionary
    """
    total_params = sum( p.numel() for p in model.parameters() );
    trainable_params = sum( p.numel() for p in model.parameters() if p.requires_grad );
    
    return {
        'architecture': 'Feed-forward neural network',
        'input_dim': model.input_dim,
        'layers': ['128', '64', '32', '16', '1'],
        'activation': 'ReLU (with Sigmoid output)',
        'dropout_rate': model.dropout_rate,
        'total_parameters': total_params,
        'trainable_parameters': trainable_params,
        'output_range': '1.0 - 5.0 (star rating)'
    };


# Testing and example usage
if __name__ == "__main__":
    if not TORCH_AVAILABLE:
        print( "PyTorch not available, skipping tests." );
        exit( 1 );
        
    # Test model creation
    print( "Testing RestaurantRatingPredictor model..." );
    
    input_dim = 20;  # Example feature dimension
    model = RestaurantRatingPredictor( input_dim );
    
    print( f"Model created with input dimension: {input_dim}" );
    print( f"Device available: {'CUDA' if torch.cuda.is_available() else 'CPU'}" );
    
    # Test forward pass
    dummy_features = torch.randn( 5, input_dim );  # 5 samples
    predictions = model.predict_rating( dummy_features );
    
    print( f"\nDummy predictions: {predictions.tolist()}" );
    
    # Test grading
    for i, rating in enumerate( predictions ):
        grade = rating_to_grade( rating.item() );
        print( f"Sample {i+1}: {rating.item():.2f} stars → Grade {grade}" );
    
    # Model info
    info = get_model_info( model );
    print( f"\nModel Info:" );
    for key, value in info.items():
        print( f"  {key}: {value}" );
