# Space Weather Launch Safety Predictor

## Overview

## Problem Statement

## Objectives

## Dataset

### Dataset Columns

## System Architecture

## Project Structure

## Technology Stack

## Machine Learning Workflow

### Data Cleaning

### Feature Engineering

### Risk Scoring

### Random Forest Model

### Model Evaluation

## Dashboard

## Installation

## Running the Notebook

## Running the Pipeline

## Running the Dashboard

## Testing

## Example Output

## Risk-Level Interpretation

## Limitations

## Educational Disclaimer

## Future Improvements

## Author

## System Flowchart

```mermaid
flowchart TD
    A[space_weather_unified.csv] --> B[Data Validation]
    B --> C[Data Cleaning]
    C --> D[Clean space_df]
    D --> E[Exploratory Data Analysis]
    D --> F[Historical Feature Engineering]
    F --> G[risk_features_df]
    G --> H[Risk Score 0-100]
    H --> I[Risk Level]
    I --> J{Risk Level}
    J -->|LOW| K[GO]
    J -->|MODERATE| L[CAUTION]
    J -->|HIGH| M[DELAY]
    J -->|EXTREME| N[NO-GO]
    G --> O[Time Based Split]
    O --> P[Random Forest Classifier]
    P --> Q[Model Evaluation]
    P --> R[launch_decision_model.pkl]
    G --> S[space_weather_data.pkl]
    R --> T[Prediction Layer]
    S --> T
    T --> U[Dashboard]
    U --> V[Risk Score Chart]
    U --> W[Recommendation Chart]
    U --> X[48h Solar Event Chart]
```
